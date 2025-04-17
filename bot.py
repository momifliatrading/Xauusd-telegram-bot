import yfinance as yf
import time

def get_xauusd_data():
    try:
        ticker = yf.Ticker("GC=F")  # Future sull'oro, più stabile
        data = ticker.history(period="1d", interval="1m")

        if not data.empty:
            last_price = data["Close"].iloc[-1]
            print(f"Prezzo attuale XAU/USD: {last_price}")
        else:
            print("Nessun dato ricevuto.")

    except Exception as e:
        print(f"Errore durante il recupero dei dati: {e}")

while True:
    get_xauusd_data()
    time.sleep(60)
