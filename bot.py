import requests
import pandas as pd
import time
import telegram
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

# Dati Telegram
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
bot = telegram.Bot(token=TOKEN)

# API Key Alpha Vantage
API_KEY = "WURVR7KA6AES8K9B"

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_xauusd_data():
    url = (
        f"https://www.alphavantage.co/query?function=FX_INTRADAY"
        f"&from_symbol=XAU&to_symbol=USD&interval=1min&outputsize=full&apikey={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    
    try:
        raw_data = data["Time Series FX (1min)"]
        df = pd.DataFrame.from_dict(raw_data, orient="index")
        df = df.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close"
        })
        df = df.astype(float)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Errore nel parsing dei dati: {e}")
        return None

def analyze(data):
    df = data.copy()
    df.dropna(inplace=True)

    # Indicatori
    df['rsi'] = RSIIndicator(close=df['Close'], window=14).rsi()
    df['macd'] = MACD(close=df['Close']).macd_diff()
    df['ema_fast'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['ema_slow'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['atr'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

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

    # EMA
    if latest['ema_fast'] > latest['ema_slow']:
        signal_strength += 1
    elif latest['ema_fast'] < latest['ema_slow']:
        signal_strength -= 1

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
            if data is not None:
                signal, price, atr, strength = analyze(data)
                if signal in ["FORTE BUY", "FORTE SELL"]:
                    tp, sl = calculate_tp_sl(price, atr, strength)
                    message = f"{signal}\nPrezzo: {price:.2f}\nTP: {tp}\nSL: {sl}"
                    send_signal(message)
            time.sleep(300)  # ogni 5 minuti
        except Exception as e:
            print(f"Errore: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
