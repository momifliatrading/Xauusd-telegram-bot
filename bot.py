import yfinance as yf
import pandas as pd
import numpy as np
import time
import datetime
import telegram
import ta

# TOKEN e CHAT_ID del bot
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
bot = telegram.Bot(token=TOKEN)

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_xauusd_data():
    try:
        df = yf.download("XAUUSD=X", interval="5m", period="1d")
        if df is None or df.empty:
            print("Dati non disponibili o vuoti.")
            return None
        return df
    except Exception as e:
        print(f"Errore durante il download dei dati: {e}")
        return None

def calculate_indicators(df):
    df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.macd_diff(df['Close'])
    df['MACD_Hist'] = macd
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    return df

def check_signal(df):
    if df is None or df.empty:
        return

    latest = df.iloc[-1]

    ema_signal = None
    rsi_signal = None
    macd_signal = None

    # EMA
    if latest['Close'] > latest['EMA20']:
        ema_signal = 'buy'
    elif latest['Close'] < latest['EMA20']:
        ema_signal = 'sell'

    # RSI
    if latest['RSI'] < 30:
        rsi_signal = 'buy'
    elif latest['RSI'] > 70:
        rsi_signal = 'sell'

    # MACD Histogram
    if latest['MACD_Hist'] > 0:
        macd_signal = 'buy'
    elif latest['MACD_Hist'] < 0:
        macd_signal = 'sell'

    signals = [ema_signal, rsi_signal, macd_signal]
    signal_type = None

    if signals.count('buy') >= 2:
        signal_type = 'FORTE BUY'
    elif signals.count('sell') >= 2:
        signal_type = 'FORTE SELL'

    # Calcolo TP/SL dinamici
    if signal_type:
        atr = latest['ATR']
        entry = latest['Close']
        if signal_type == 'FORTE BUY':
            tp = entry + (2.5 * atr if signals.count('buy') == 3 else 1.5 * atr)
            sl = entry - (1.5 * atr)
        else:
            tp = entry - (2.5 * atr if signals.count('sell') == 3 else 1.5 * atr)
            sl = entry + (1.5 * atr)

        message = (
            f"{signal_type} su XAU/USD\n\n"
            f"Prezzo: {entry:.2f}\n"
            f"Take Profit: {tp:.2f}\n"
            f"Stop Loss: {sl:.2f}\n\n"
            f"RSI: {latest['RSI']:.2f}\n"
            f"MACD Histogram: {latest['MACD_Hist']:.4f}\n"
            f"EMA20: {latest['EMA20']:.2f}"
        )
        send_signal(message)

# Loop principale ogni 5 minuti
while True:
    print(f"[{datetime.datetime.now()}] Controllo segnali...")
    df = get_xauusd_data()
    if df is not None:
        df = calculate_indicators(df)
        check_signal(df)
    time.sleep(300)  # 5 minuti
