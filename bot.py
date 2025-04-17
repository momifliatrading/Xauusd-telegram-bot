import yfinance as yf
import time

def get_xauusd_data():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1d", interval="1m")
    if data.empty:
        print("Nessun dato ricevuto da Yahoo Finance.")
    else:
        latest = data.iloc[-1]
        print(f"Ultimo prezzo XAU/USD: {latest['Close']}")

while True:
    get_xauusd_data()
    time.sleep(60)
