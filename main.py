import requests
import os
import time
import yfinance as yf
from datetime import datetime
import pandas as pd # <-- ¡NUEVA IMPORTANCIA! Para manejar la lista de acciones

# --- CONFIGURACIÓN ---
ALPHA_VANTAGE_API_KEY = os.getenv('NY2BKAZONTRVMUEK')
DISCORD_WEBHOOK_URL = os.getenv('https://discordapp.com/api/webhooks/1449729466933841921/ayyGZXy9o1Fuo4YGBWMwpBRjNnQ9NtgY63nxkapJXUDRLVlbdb_bugXQl5dt3Mi8j7Un')

# --- CONFIGURACIÓN DE LAS 5 ESTRATEGIAS ---
UMBRAL_VOLUMEN = 500000
PERIODO_RESISTENCIA = 90
FACTOR_MEDIA_ALCISTA = 1.05
FACTOR_MEDIA_BAJISTA = 0.95
FACTOR_COMPRESION = 0.75
FACTOR_VOLUMEN_ACUMULADO = 1.5

# --- CONFIGURACIÓN DE HORARIO (HORA UTC) ---
# 7:00 AM UTC = 8:00 AM en España (Apertura Europa)
# 21:00 PM UTC = 4:00 PM en Nueva York (Cierre EE.UU.)
HORA_INICIO = 7
MINUTO_INICIO = 0
HORA_FIN = 21
MINUTO_FIN = 1

# --- MEMORIA DEL RASTREADOR ---
alerted_today = set()
last_run_day = None

# --- FUNCIONES ---

def enviar_alerta_discord(ticker, precio_actual, cambio_precio, porcentaje_cambio, volumen_actual, volumen_promedio, ratio, resistencia, media_movil_20d, rango_10d, rango_50d, vol_3d, vol_20d_previos, señales_encontradas):
    """Envía una súper-alerta con toda la información de las 5 estrategias."""
    print(f"🚀 ¡SÚPER ALERTA! Enviando análisis para {ticker}...")
    
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
                f"--- **SEÑALES DETECTADAS** ---\n" \
                f"➡️ {', '.join(señales_encontradas)}"

    datos = {
        "username": "Market Monitor",
        "content": contenido
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=datos)
        response.raise_for_status()
        print(f"✅ Alerta enviada para {ticker}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar alerta a Discord: {e}")

def obtener_lista_completa_de_acciones():
    """Carga una lista completa de tickers del mercado estadounidense."""
    print("📚 Cargando lista completa de acciones del mercado NASDAQ...")
    try:
        # Usamos pandas_datareader para obtener la lista de tickers de NASDAQ
        from pandas_datareader.nasdaq_trader import get_nasdaq_symbols
        tickers = get_nasdaq_symbols()
        print(f"✅ Se cargaron {len(tickers)} tickers de NASDAQ.")
        return tickers
    except Exception as e:
        print(f"❌ No se pudo cargar la lista de NASDAQ. Error: {e}")
        print("🔄 Intentando con una lista estática como respaldo...")
        # Respaldo: una lista de acciones conocidas si lo anterior falla
        tickers_respaldo = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V']
        return tickers_respaldo

def analizar_ticker(ticker):
    """Realiza un análisis completo con las 5 estrategias."""
    global alerted_today
    if ticker in alerted_today:
        return

    try:
        print(f"🔍 Analizando {ticker}...")
        
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
            enviar_alerta_discord(ticker, precio_actual, cambio_precio_str, porcentaje_cambio_str, volumen_actual, volumen_promedio, ratio_volumen, resistencia, media_movil_20d, rango_10d, rango_50d, vol_3d, vol_20d_previos, señales_encontradas)
            alerted_today.add(ticker)

    except Exception as e:
        print(f"   - ❌ Error al procesar {ticker}: {e}")

# --- BUCLE PRINCIPAL ---
if __name__ == "__main__":
    print("🚀 Iniciando Explorador de Mercado Definitivo...")
    
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

    if not ALPHA_VANTAGE_API_KEY or not DISCORD_WEBHOOK_URL:
        print("ERROR: No has configurado tus claves en los Secrets de Replit.")
    else:
        while True:
            ahora = datetime.now()
            current_day = ahora.day
            if last_run_day != current_day:
                print(f"\n--- Nuevo día detectado ({ahora.strftime('%Y-%m-%d')}). Borrando memoria de alertas. ---")
                alerted_today.clear()
                last_run_day = current_day
            if (ahora.hour >= HORA_INICIO and ahora.minute >= MINUTO_INICIO) and \
               (ahora.hour < HORA_FIN or (ahora.hour == HORA_FIN and ahora.minute <= MINUTO_FIN)):
                print(f"\n{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC - Mercado abierto. Explorando el mercado...")
                lista_completa = obtener_lista_completa_de_acciones()
                if not lista_completa:
                    print("No se pudieron obtener acciones. Reintentando en 10 minutos.")
                    time.sleep(600)
                else:
                    print(f"Analizando {len(lista_completa)} acciones. Esto puede tardar un tiempo...")
                    for ticker in lista_completa:
                        analizar_ticker(ticker)
                        time.sleep(12) # Pausa para no superar el límite de la API
                    print("\n🏁 Análisis completo del mercado finalizado.")
            else:
                print(f"\n{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC - Mercado cerrado. Durmiendo...")
                time.sleep(600)
