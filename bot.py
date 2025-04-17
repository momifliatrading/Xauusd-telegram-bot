import yfinance as yf
import time

def get_xauusd_data():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1d", interval="1m")
    
    if not data.empty:
        latest = data.iloc[-1]
        print(f"Prezzo attuale XAU/USD: {latest['Close']}")
    else:
        print("Nessun dato disponibile")

while True:
    get_xauusd_data()
    time.sleep(60)
