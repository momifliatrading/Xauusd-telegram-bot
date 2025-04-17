import requests
import pandas as pd
import time
import datetime
import logging
from telegram import Bot
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

# === CONFIGURAZIONE ===
ALPHA_VANTAGE_API_KEY = "LA_TUA_API_KEY"
TELEGRAM_TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
SYMBOLS = {"XAU/USD": "XAUUSD", "EUR/USD": "EURUSD"}
INTERVAL = "5min"
RISK_PERCENTAGE = 0.02
ACCOUNT_BALANCE = 5000

# === SETUP TELEGRAM ===
bot = Bot(token=TELEGRAM_TOKEN)

# === FUNZIONE PER OTTENERE I DATI ===
def get_data(symbol):
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={INTERVAL}&apikey={ALPHA_VANTAGE_API_KEY}&outputsize=compact"
    r = requests.get(url)
    data = r.json()
    key = f"Time Series FX ({INTERVAL})"
    if key not in data:
        print(f"Errore: chiave '{key}' non trovata nei dati")
        return None
    df = pd.DataFrame(data[key]).T.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

# === FUNZIONE PER GENERARE I SEGNALI ===
def generate_signals(df):
    ema = EMAIndicator(close=df['4. close'], window=20).ema_indicator()
    rsi = RSIIndicator(close=df['4. close'], window=14).rsi()
    macd = MACD(close=df['4. close']).macd_diff()
    atr = AverageTrueRange(high=df['2. high'], low=df['3. low'], close=df['4. close']).average_true_range()
    df = df.copy()
    df['EMA'] = ema
    df['RSI'] = rsi
    df['MACD_diff'] = macd
    df['ATR'] = atr

    last = df.iloc[-1]
    signal = None
    strength = 0

    # Condizioni
    if last['4. close'] > last['EMA']:
        strength += 1
    if last['RSI'] > 50:
        strength += 1
    if last['MACD_diff'] > 0:
        strength += 1
    if strength == 3:
        signal = "FORTE BUY"
    elif strength == 2:
        signal = "BUY"
    elif strength == 1:
        signal = "DEBOLE BUY"

    # SELL
    strength = 0
    if last['4. close'] < last['EMA']:
        strength += 1
    if last['RSI'] < 50:
        strength += 1
    if last['MACD_diff'] < 0:
        strength += 1
    if strength == 3:
        signal = "FORTE SELL"
    elif strength == 2:
        signal = "SELL"
    elif strength == 1:
        signal = "DEBOLE SELL"

    # TP / SL / LOTTAGGIO
    tp = round(last['4. close'] + 2 * last['ATR'], 3) if "BUY" in signal else round(last['4. close'] - 2 * last['ATR'], 3)
    sl = round(last['4. close'] - last['ATR'], 3) if "BUY" in signal else round(last['4. close'] + last['ATR'], 3)
    risk = last['ATR']
    lot_size = round((ACCOUNT_BALANCE * RISK_PERCENTAGE) / risk, 2)

    return signal, tp, sl, lot_size

# === FUNZIONE PRINCIPALE ===
def run_bot():
    last_update = None
    while True:
        now = datetime.datetime.now()
        update_needed = last_update is None or (now - last_update).seconds >= 1800

        for name, code in SYMBOLS.items():
            df = get_data(code)
            if df is not None:
                signal, tp, sl, lot = generate_signals(df)
                message = f"{name} - Segnale: {signal}\nPrezzo: {df['4. close'].iloc[-1]:.3f}\nTP: {tp} | SL: {sl}\nLottaggio: {lot}"
                if "FORTE" in signal or update_needed:
                    bot.send_message(chat_id=CHAT_ID, text=message)

        if update_needed:
            last_update = now

        time.sleep(360)  # 6 minuti

# === AVVIO ===
if __name__ == "__main__":
    run_bot()
