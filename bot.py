import requests
import pandas as pd
import time
import telegram
import ta
import numpy as np

# === CONFIG ===
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
API_KEY = "WURVR7KA6AES8K9B"
CAPITALE = 5000
RISCHIO_PCT = 0.02
symbols = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD"
}
bot = telegram.Bot(token=TOKEN)

# === FUNZIONI ===
def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_data(symbol):
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[4:]}&interval=1min&apikey={API_KEY}&outputsize=compact"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['Time Series FX (1min)']).T.astype(float)
        df.columns = ['Open', 'High', 'Low', 'Close']
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Errore nel download di {symbol}: {e}")
        return None

def detect_candlestick(df):
    last = df.iloc[-2]  # Penultima candela
    curr = df.iloc[-1]  # Ultima candela

    body = curr['Close'] - curr['Open']
    range_ = curr['High'] - curr['Low']
    upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
    lower_wick = min(curr['Open'], curr['Close']) - curr['Low']

    # Engulfing
    prev_body = last['Close'] - last['Open']
    if body > 0 and prev_body < 0 and curr['Open'] < last['Close'] and curr['Close'] > last['Open']:
        return "bullish_engulfing"
    elif body < 0 and prev_body > 0 and curr['Open'] > last['Close'] and curr['Close'] < last['Open']:
        return "bearish_engulfing"

    # Hammer / Shooting Star
    if body > 0 and lower_wick > body * 2 and upper_wick < body:
        return "hammer"
    elif body < 0 and upper_wick > abs(body) * 2 and lower_wick < abs(body):
        return "shooting_star"

    return None

def analyze(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['macd'] = macd.macd_diff()
    df['ema_fast'] = ta.trend.EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['atr'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()
    df.dropna(inplace=True)

    latest = df.iloc[-1]
    signal_strength = 0
    signal = None

    if latest['rsi'] < 30: signal_strength += 1
    elif latest['rsi'] > 70: signal_strength -= 1

    if latest['macd'] > 0: signal_strength += 1
    elif latest['macd'] < 0: signal_strength -= 1

    if latest['ema_fast'] > latest['ema_slow']: signal_strength += 1
    elif latest['ema_fast'] < latest['ema_slow']: signal_strength -= 1

    if signal_strength == 3: signal = "FORTE BUY"
    elif signal_strength == -3: signal = "FORTE SELL"
    elif signal_strength == 2: signal = "BUY (debole)"
    elif signal_strength == -2: signal = "SELL (debole)"

    pattern = detect_candlestick(df)

    # Filtro candlestick
    if signal in ["FORTE BUY", "BUY (debole)"] and pattern not in ["bullish_engulfing", "hammer"]:
        return None, None, None, None
    if signal in ["FORTE SELL", "SELL (debole)"] and pattern not in ["bearish_engulfing", "shooting_star"]:
        return None, None, None, None

    return signal, latest['Close'], latest['atr'], signal_strength

def calculate_tp_sl(price, atr, strength):
    if abs(strength) == 3:
        tp = price + atr * 3 if strength > 0 else price - atr * 3
        sl = price - atr * 1.5 if strength > 0 else price + atr * 1.5
    elif abs(strength) == 2:
        tp = price + atr * 2 if strength > 0 else price - atr * 2
        sl = price - atr if strength > 0 else price + atr
    else:
        return None, None
    return round(tp, 5), round(sl, 5)

def calculate_lot_size(sl_pips):
    if sl_pips == 0:
        return 0.01
    risk_usd = CAPITALE * RISCHIO_PCT
    pip_value = 10
    lots = risk_usd / (sl_pips * pip_value)
    return round(min(max(lots, 0.01), 5), 2)

def main():
    while True:
        report = f"Aggiornamento strategia ({pd.Timestamp.now().strftime('%H:%M:%S')}):\n\n"
        for name, symbol in symbols.items():
            df = get_data(symbol)
            if df is not None:
                signal, price, atr, strength = analyze(df)
                if signal:
                    tp, sl = calculate_tp_sl(price, atr, strength)
                    sl_pips = abs(price - sl) * 100
                    lot = calculate_lot_size(sl_pips)
                    report += (
                        f"Strumento: {name}\n"
                        f"Segnale: {signal}\n"
                        f"Prezzo: {price:.5f}\n"
                        f"TP: {tp} / SL: {sl}\n"
                        f"Lotto consigliato: {lot}\n\n"
                    )
                else:
                    report += f"Strumento: {name} - Nessun segnale valido (candlestick non conferma)\n\n"
            else:
                report += f"Errore nel recupero dati per {name}\n\n"

        send_signal(report.strip())
        time.sleep(1800)  # ogni 30 minuti

# === START ===
if __name__ == "__main__":
    main()
