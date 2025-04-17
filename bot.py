import requests
import pandas as pd
import time
import telegram
import ta

# === Config ===
API_KEY = "WURVR7KA6AES8K9B"
SYMBOLS = {"XAUUSD": "XAU/USD", "EURUSD": "EUR/USD"}
INTERVAL = "15min"
TELEGRAM_TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
BUDGET = 5000
RISK_PERCENT = 0.02

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def fetch_data(symbol):
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={INTERVAL}&apikey={API_KEY}&outputsize=compact"
    r = requests.get(url)
    data = r.json()
    try:
        df = pd.DataFrame(data[f"Time Series FX ({INTERVAL})"]).T.astype(float)
        df = df.rename(columns={
            "1. open": "Open", "2. high": "High",
            "3. low": "Low", "4. close": "Close"
        })
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Errore nel parsing dati per {symbol}: {e}")
        return None

def analyze(df):
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
    df["macd"] = ta.trend.MACD(df["Close"]).macd_diff()
    df["ema_fast"] = ta.trend.EMAIndicator(df["Close"], window=9).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["Close"], window=21).ema_indicator()
    df["atr"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()
    df["bb_bbm"] = ta.volatility.BollingerBands(df["Close"]).bollinger_mavg()
    df["cloud_base"] = ta.trend.IchimokuIndicator(df["High"], df["Low"]).ichimoku_base_line()

    latest = df.iloc[-1]
    signal_strength = 0

    # Condizioni principali
    if latest["rsi"] < 30:
        signal_strength += 1
    elif latest["rsi"] > 70:
        signal_strength -= 1

    if latest["macd"] > 0:
        signal_strength += 1
    elif latest["macd"] < 0:
        signal_strength -= 1

    if latest["ema_fast"] > latest["ema_slow"]:
        signal_strength += 1
    elif latest["ema_fast"] < latest["ema_slow"]:
        signal_strength -= 1

    # Bollinger e Ichimoku come conferme
    conferme = 0
    if latest["Close"] > latest["bb_bbm"]:
        conferme += 1
    if latest["Close"] > latest["cloud_base"]:
        conferme += 1
    if latest["Close"] < latest["bb_bbm"]:
        conferme -= 1
    if latest["Close"] < latest["cloud_base"]:
        conferme -= 1

    # Solo se forte segnale e almeno 1 conferma
    if signal_strength == 3 and conferme >= 1:
        return "FORTE BUY", latest["Close"], latest["atr"]
    elif signal_strength == -3 and conferme <= -1:
        return "FORTE SELL", latest["Close"], latest["atr"]
    else:
        return None, None, None

def calculate_tp_sl(price, atr, direction):
    if direction == "BUY":
        tp = price + atr * 3
        sl = price - atr * 1.5
    else:
        tp = price - atr * 3
        sl = price + atr * 1.5
    return round(tp, 4), round(sl, 4)

def calculate_lot_size(sl_pips, symbol):
    pip_value = 10 if symbol in ["XAUUSD"] else 1
    risk_amount = BUDGET * RISK_PERCENT
    lots = risk_amount / (sl_pips * pip_value)
    return round(lots, 2)

def main():
    while True:
        for symbol in SYMBOLS:
            print(f"Controllo {symbol}...")
            df = fetch_data(symbol)
            if df is not None:
                signal, price, atr = analyze(df)
                if signal:
                    direction = "BUY" if "BUY" in signal else "SELL"
                    tp, sl = calculate_tp_sl(price, atr, direction)
                    sl_pips = abs(price - sl)
                    lot_size = calculate_lot_size(sl_pips, symbol)
                    msg = f"{signal} su {SYMBOLS[symbol]}\nPrezzo: {price:.4f}\nTP: {tp}\nSL: {sl}\nLotti consigliati: {lot_size}"
                    send_signal(msg)
        time.sleep(360)  # 6 minuti

if __name__ == "__main__":
    main()
