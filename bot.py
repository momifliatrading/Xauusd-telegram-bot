import yfinance as yf
import ta
import pandas as pd
import time
import telegram
import logging

# Configura il logging
logging.basicConfig(level=logging.INFO)

# Dati Telegram
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
bot = telegram.Bot(token=TOKEN)

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_xauusd_data():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="7d", interval="1m")
    return data

def analyze(data):
    df = data.copy()
    df.dropna(inplace=True)

    # Indicatori tecnici
    df['rsi'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    df['macd'] = ta.trend.MACD(close=df['Close']).macd_diff()
    df['ema_fast'] = ta.trend.EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['atr'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

    latest = df.iloc[-1]

    signal_strength = 0
    signal = None

    # RSI
    if latest['rsi'] < 30:
        signal_strength += 1
    elif latest['rsi'] > 70:
        signal_strength -= 1

    # MACD
    if latest['macd'] > 0:
        signal_strength += 1
    elif latest['macd'] < 0:
        signal_strength -= 1

    # EMA crossover
    if latest['ema_fast'] > latest['ema_slow']:
        signal_strength += 1
    elif latest['ema_fast'] < latest['ema_slow']:
        signal_strength -= 1

    # Segnale finale
    if signal_strength == 3:
        signal = "FORTE BUY"
    elif signal_strength == -3:
        signal = "FORTE SELL"
    elif signal_strength == 2:
        signal = "BUY"
    elif signal_strength == -2:
        signal = "SELL"

    return signal, latest['Close'], latest['atr'], signal_strength

def calculate_tp_sl(price, atr, signal_strength):
    if abs(signal_strength) == 3:
        tp = price + atr * 3 if signal_strength > 0 else price - atr * 3
        sl = price - atr * 1.5 if signal_strength > 0 else price + atr * 1.5
    elif abs(signal_strength) == 2:
        tp = price + atr * 2 if signal_strength > 0 else price - atr * 2
        sl = price - atr if signal_strength > 0 else price + atr
    else:
        return None, None
    return round(tp, 2), round(sl, 2)

def main():
    while True:
        try:
            data = get_xauusd_data()
            signal, price, atr, strength = analyze(data)
            if signal in ["FORTE BUY", "FORTE SELL"]:
                tp, sl = calculate_tp_sl(price, atr, strength)
                message = f"{signal}\nPrezzo: {price:.2f}\nTP: {tp}\nSL: {sl}"
                send_signal(message)
                logging.info(f"Segnale inviato: {message}")
            else:
                logging.info(f"Nessun segnale forte ({signal})")
            time.sleep(60)
        except Exception as e:
            logging.error(f"Errore: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
