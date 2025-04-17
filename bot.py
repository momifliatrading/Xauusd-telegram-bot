import yfinance as yf
import time

def get_xauusd_data():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1d", interval="1m")
    if not data.empty:
        last_price = data["Close"].iloc[-1]
        print(f"Prezzo attuale XAU/USD: {last_price}")
    else:
        print("Nessun dato ricevuto.")

# Loop ogni 60 secondi
while True:
    get_xauusd_data()
    time.sleep(60)
