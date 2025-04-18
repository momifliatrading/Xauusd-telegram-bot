import requests
import pandas as pd
from datetime import datetime
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
import ta

# === CONFIG ===
API_KEYS = [
    "G1DLU6EXR0XKXKWE",
    "HSQEM45D73VB2136"
]

TELEGRAM_TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
CAPITAL = 5000
RISK = 0.02

symbols = {
    "XAU/USD": ("XAU", "USD"),
    "EUR/USD": ("EUR", "USD")
}

bot = Bot(token=TELEGRAM_TOKEN)

# === FUNZIONI ===

def get_data(from_symbol, to_symbol):
    for api_key in API_KEYS:
        url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval=5min&apikey={api_key}&outputsize=compact"
        print(f"[{datetime.now()}] Chiamata API: {url}")
        try:
            response = requests.get(url)
            data = response.json()

            if "Time Series FX (5min)" in data:
                df = pd.DataFrame(data['Time Series FX (5min)']).T.astype(float)
                df.columns = ['Open', 'High', 'Low', 'Close']
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                return df
            else:
                print(f"[{datetime.now()}] Risposta senza dati validi per {from_symbol}/{to_symbol}: {data}")
        except Exception as e:
            print(f"[{datetime.now()}] Errore nella richiesta per {from_symbol}/{to_symbol} con {api_key}: {e}")
    return None

def analyze(df):
    df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.macd_diff(df['Close'])

    last_rsi = df['RSI'].iloc[-1]
    last_macd = macd.iloc[-1]
    last_price = df['Close'].iloc[-1]
    last_ema = df['EMA20'].iloc[-1]

    buy = last_rsi < 30 and last_macd > 0 and last_price > last_ema
    sell = last_rsi > 70 and last_macd < 0 and last_price < last_ema

    if buy or sell:
        direction = "BUY" if buy else "SELL"
        strength = "FORTE"
        return direction, strength, last_price
    return None, None, None

def calculate_tp_sl(price, direction):
    atr = 0.003  # Fisso per ora
    if direction == "BUY":
        tp = price + 2 * atr
        sl = price - atr
    else:
        tp = price - 2 * atr
        sl = price + atr
    return round(tp, 4), round(sl, 4)

def calculate_lot_size(price, sl, capital, risk):
    risk_amount = capital * risk
    stop_loss_pips = abs(price - sl)
    if stop_loss_pips == 0:
        return 0.01
    lot_size = risk_amount / (stop_loss_pips * 100000)
    return round(min(max(lot_size, 0.01), 5), 2)

def invia_messaggio(msg):
    try:
        bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        print(f"[{datetime.now()}] Errore nell’invio Telegram: {e}")

def main():
    for name, (from_symbol, to_symbol) in symbols.items():
        df = get_data(from_symbol, to_symbol)
        if df is None:
            print(f"[{datetime.now()}] Errore nel recupero dati per {name}")
            continue

        direction, strength, price = analyze(df)
        if direction:
            tp, sl = calculate_tp_sl(price, direction)
            lot = calculate_lot_size(price, sl, CAPITAL, RISK)
            msg = (
                f"Segnale {strength} {direction} su {name}\n"
                f"Prezzo: {price}\nTP: {tp} | SL: {sl}\n"
                f"Lotto consigliato: {lot}"
            )
            invia_messaggio(msg)
        else:
            print(f"[{datetime.now()}] Nessun segnale forte per {name}")

# === SCHEDULAZIONE OGNI 6 MINUTI ===
scheduler = BlockingScheduler()
scheduler.add_job(main, 'interval', minutes=6)
scheduler.start()
