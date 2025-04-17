import requests
import yfinance as yf
import time
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def get_xauusd_signal():
    df = yf.download("XAUUSD=X", interval="60m", period="2d")
    close = df["Close"]
    ema20 = close.ewm(span=20).mean()
    ema50 = close.ewm(span=50).mean()

    if ema20.iloc[-1] > ema50.iloc[-1] and ema20.iloc[-2] <= ema50.iloc[-2]:
        return "BUY"
    elif ema20.iloc[-1] < ema50.iloc[-1] and ema20.iloc[-2] >= ema50.iloc[-2]:
        return "SELL"
    return None

while True:
    signal = get_xauusd_signal()
    if signal:
        send_telegram_message(f"Segnale forte {signal} su XAU/USD")
    time.sleep(60)
