import yfinance as yf

def get_price():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1m")
    if data.empty:
        return None
    return round(data['Close'].iloc[-1], 2)
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Messaggio di test
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=✅+Bot+collegato+correttamente!")
