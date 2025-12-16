import requests
import os
import time
import yfinance as yf
from datetime import datetime

# --- INICIO DE DEPURACIÓN DE CLAVES ---
print("🔍 DEPURACIÓN: Comprobando claves...")
api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

if api_key:
    print(f"✅ Clave ALPHA_VANTAGE_API_KEY encontrada.")
else:
    print("❌ ERROR: La clave ALPHA_VANTAGE_API_KEY NO fue encontrada o está vacía.")

if webhook_url:
    print(f"✅ Clave DISCORD_WEBHOOK_URL encontrada.")
else:
    print("❌ ERROR: La clave DISCORD_WEBHOOK_URL NO fue encontrada o está vacía.")
# --- FIN DE LA DEPURACIÓN ---

# --- CONFIGURACIÓN ---
ALPHA_VANTAGE_API_KEY = os.getenv('NY2BKAZONTRVMUEK')
DISCORD_WEBHOOK_URL = os.getenv('https://discordapp.com/api/webhooks/1449729466933841921/ayyGZXy9o1Fuo4YGBWMwpBRjNnQ9NtgY63nxkapJXUDRLVlbdb_bugXQl5dt3Mi8j7Un')

# --- CONFIGURACIÓN DE TODAS LAS ESTRATEGIAS ---
# 1. Para Detección de Ballenas y Rompes
UMBRAL_VOLUMEN = 500000  # 500 mil acciones
PERIODO_RESISTENCIA = 90 # Días para calcular la resistencia

# 2. Para Análisis de Patrón (Barbacoa/Incendio)
FACTOR_MEDIA_ALCISTA = 1.05 # Precio 5% por encima de su media
FACTOR_MEDIA_BAJISTA = 0.95 # Precio 5% por debajo de su media

# 3. Para Detección Anticipatoria (Compresión/Acumulación)
FACTOR_COMPRESION = 0.75 # El rango de 10d debe ser menor al 75% del rango de 50d
FACTOR_VOLUMEN_ACUMULADO = 1.5 # El volumen de 3d debe ser 1.5x mayor que el de los 20d previos

# --- ¡NUEVO! TU LISTA DE EXPLORACIÓN ---
# Añade aquí acciones de otros sectores, mid-caps, o cualquier ticker que te interese.
# El bot analizará estas además de las más populares del día.
MI_LISTA_ADICIONAL = [
    "PLTR", # Ejemplo: Tecnología / Defensa
    "GME",  # Ejemplo: Retail / Meme stock
    "COIN", # Ejemplo: Cripto
    "RIVN", # Ejemplo: Vehículos eléctricos
    "AFRM", # Ejemplo: Fintech
    "SOFI", # Ejemplo: Banca digital
    # Añade todas las que quieras aquí...
]

# --- CONFIGURACIÓN DE HORARIO (AHORA EN HORA UTC DEL SERVIDOR) ---
# ¡IMPORTANTE! Estas horas son en UTC (hora de Londres), no en hora de España.
# 7:00 AM UTC = 8:00 AM en España (Apertura Europa)
# 21:00 PM UTC = 4:00 PM en Nueva York (Cierre EE.UU.)
HORA_INICIO = 7    # <-- ¡CAMBIO! Ahora empieza a las 7:00 AM UTC
MINUTO_INICIO = 0  # <-- ¡CAMBIO!
HORA_FIN = 21      # <-- ¡CAMBIO! Ahora termina a las 21:00 PM UTC
MINUTO_FIN = 1     # <-- ¡CAMBIO!

# --- MEMORIA DEL RASTREADOR ---
alerted_today = set()
last_run_day = None

# --- FUNCIONES ---

def enviar_alerta_discord(ticker, precio_actual, cambio_precio, porcentaje_cambio, volumen_actual, volumen_promedio, ratio, resistencia, media_movil_20d, rango_10d, rango_50d, vol_3d, vol_20d_previos, señales_encontradas):
    """Envía una súper-alerta con toda la información de las 5 estrategias."""
    print(f"🚀 ¡SÚPER ALERTA DEFINITIVA! Enviando análisis completo para {ticker}...")
    
    titulo = f"🤖 **ANÁLISIS COMPLETO: {ticker}** 🤖"
    if len(señales_encontradas) > 1:
        titulo = f"🚀🔥🧨 **SEÑAL MÚLTIPLE EN {ticker}** 🚀🔥🧨"
    
    contenido = f"{titulo}\n\n" \
                f"💹 **Precio:** {precio_actual:.2f} {cambio_precio} ({porcentaje_cambio})\n\n" \
                f"--- **ANÁLISIS TÉCNICO** ---\n" \
                f"📊 **Volumen:** {volumen_actual:,} (Promedio: {volumen_promedio:,.0f})\n" \
                f"🔥 **Ratio Volumen:** {ratio:.2f}x\n" \
                f"🧱 **Resistencia:** {resistencia:.2f}\n" \
                f"📈 **Media 20d:** {media_movil_20d:.2f}\n\n" \
                f"--- **ANÁLISIS ANTICIPATORIO** ---\n" \
                f"📉 **Rango 10d:** {rango_10d:.2f} (vs Rango 50d: {rango_50d:.2f})\n" \
                f"📊 **Volumen 3d:** {vol_3d:,.0f} (vs Vol. previo: {vol_20d_previos:,.0f})\n\n" \
                f"--- **SEÑALES DETECTADAS** ---\n" \
                f"➡️ {', '.join(señales_encontradas)}"

    datos = {
        "username": "Market Monitor", # Puedes cambiar este nombre para más discreción
        "content": contenido
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=datos)
        response.raise_for_status()
        print(f"✅ Súper-alerta definitiva enviada para {ticker}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar alerta a Discord: {e}")

def obtener_candidatos_variados():
    """Obtiene candidatos de dos fuentes: la lista de Alpha Vantage y tu lista personal."""
    print("📡 Obteniendo lista variada de candidatos...")
    candidatos_unicos = set()
    
    # Fuente 1: Lista de Alpha Vantage
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={ALPHA_VANTAGE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        for categoria in ['most_actively_traded', 'top_gainers', 'top_losers']:
            if categoria in data:
                for item in data[categoria]:
                    candidatos_unicos.add(item['ticker'])
    except Exception as e:
        print(f"❌ No se pudo obtener la lista de Alpha Vantage: {e}")

    # Fuente 2: Tu lista personal
    for ticker in MI_LISTA_ADICIONAL:
        candidatos_unicos.add(ticker)

    lista_final = list(candidatos_unicos)
    print(f"✅ Se encontraron {len(lista_final)} candidatos únicos para analizar.")
    return lista_final

def analizar_ticker(ticker):
    """Realiza un análisis completo con las 5 estrategias."""
    global alerted_today
    if ticker in alerted_today:
        return

    try:
        print(f"🔍 Análisis Definitivo 5 en 1 para {ticker}...")
        
        stock_data = yf.Ticker(ticker)
        hist = stock_data.history(period="65d", interval="1d")
        if hist.empty or len(hist) < 60: return

        quote_url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
        quote_response = requests.get(quote_url)
        data = quote_response.json()
        
        precio_actual = float(data.get('Global Quote', {}).get('05. price', '0.0'))
        cambio_precio_str = data.get('Global Quote', {}).get('09. change', '0.00')
        porcentaje_cambio_str = data.get('Global Quote', {}).get('10. change percent', '0.0%')
        volumen_actual = int(data.get('Global Quote', {}).get('06. volume', '0'))

        volumen_promedio = hist['Volume'].tail(20).mean()
        ratio_volumen = volumen_actual / volumen_promedio if volumen_promedio > 0 else 0
        media_movil_20d = hist['Close'].tail(20).mean()
        resistencia = hist['High'].tail(PERIODO_RESISTENCIA).max()
        
        rango_10d = (hist['High'].tail(10) - hist['Low'].tail(10)).mean()
        rango_50d = (hist['High'].tail(50) - hist['Low'].tail(50)).mean()
        vol_3d = hist['Volume'].tail(3).mean()
        vol_20d_previos = hist['Volume'].tail(23).head(20).mean()

        señales_encontradas = []
        if precio_actual > resistencia:
            señales_encontradas.append("🚀 Rompe Alcista Confirmado")
        if volumen_actual > UMBRAL_VOLUMEN:
            señales_encontradas.append("🔥 Pico de Volumen Anormal")
        
        # --- Texto resaltado con Markdown ---
        if precio_actual > media_movil_20d * FACTOR_MEDIA_ALCISTA:
            señales_encontradas.append("🍖 Patrón de '**Barbacoa**' (Cierre de Ganancias)")
        elif precio_actual < media_movil_20d * FACTOR_MEDIA_BAJISTA:
            señales_encontradas.append("🚨 Patrón de '**Incendio**' (Pump and Dump)")
            
        esta_comprimido = rango_10d < (rango_50d * FACTOR_COMPRESION)
        hay_acumulacion = vol_3d > (vol_20d_previos * FACTOR_VOLUMEN_ACUMULADO)
        if esta_comprimido and hay_acumulacion:
            señales_encontradas.append("🧨 Posible Explosión Inminente (**Resorte** Comprimido)")

        if señales_encontradas:
            print(f"   - 🎯 ¡SEÑAL(ES) ENCONTRADA(S) en {ticker}!")
            print(f"      -> {', '.join(señales_encontradas)}")
            print("-" * 40)
            enviar_alerta_discord(ticker, precio_actual, cambio_precio_str, porcentaje_cambio_str, volumen_actual, volumen_promedio, ratio_volumen, resistencia, media_movil_20d, rango_10d, rango_50d, vol_3d, vol_20d_previos, señales_encontradas)
            alerted_today.add(ticker)

    except Exception as e:
        print(f"   - ❌ Error al procesar {ticker}: {e}")

# --- BUCLE PRINCIPAL ---
if __name__ == "__main__":
    print("🚀 Iniciando Analista Definitivo 5 en 1 (Versión Final)...")
    if not ALPHA_VANTAGE_API_KEY or not DISCORD_WEBHOOK_URL:
        print("ERROR: No has configurado tus claves en los Secrets de Replit.")
    else:
        while True:
            # Usamos datetime.now() que nos dará la hora del servidor (UTC)
            ahora = datetime.now()
            current_day = ahora.day
            if last_run_day != current_day:
                print(f"\n--- Nuevo día detectado ({ahora.strftime('%Y-%m-%d')}). Borrando memoria de alertas. ---")
                alerted_today.clear()
                last_run_day = current_day
            if (ahora.hour >= HORA_INICIO and ahora.minute >= MINUTO_INICIO) and \
               (ahora.hour < HORA_FIN or (ahora.hour == HORA_FIN and ahora.minute <= MINUTO_FIN)):
                print(f"\n{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC - Mercado abierto. Ejecutando análisis completo...")
                candidatos = obtener_candidatos_variados()
                if not candidatos:
                    time.sleep(300)
                else:
                    for ticker in candidatos:
                        analizar_ticker(ticker)
                        time.sleep(12) 
            else:
                print(f"\n{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC - Mercado cerrado. Durmiendo...")
                time.sleep(600)
