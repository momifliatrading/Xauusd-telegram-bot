import requests
import pandas as pd
import ta
import time
import telegram

# Telegram
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
bot = telegram.Bot(token=TOKEN)

# Alpha Vantage
API_KEY = "WURVR7KA6AES8K9B"
BASE_URL = "https://www.alphavantage.co/query"

# Lista strumenti da analizzare
symbols = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "BTCUSD": "BTC/USD"
}

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_data(symbol):
    try:
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": symbol[:3],
            "to_symbol": symbol[3:],
            "interval": "15min",
            "apikey": API_KEY,
            "outputsize": "compact"
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        key = f"Time Series FX (15min)"
        if key not in data:
            print(f"Errore dati per {symbol}: {data}")
            return None

        df = pd.DataFrame.from_dict(data[key], orient='index')
        df.columns = ["Open", "High", "Low", "Close"]
        df = df.astype(float)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Errore download {symbol}: {e}")
        return None

def analyze(df):
    df = df.copy()
    df.dropna(inplace=True)

    df['rsi'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    df['macd'] = ta.trend.MACD(close=df['Close']).macd_diff()
    df['ema_fast'] = ta.trend.EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['atr'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

    latest = df.iloc[-1]
    signal_strength = 0

    if latest['rsi'] < 30:
        signal_strength += 1
    elif latest['rsi'] > 70:
        signal_strength -= 1

    if latest['macd'] > 0:
        signal_strength += 1
    elif latest['macd'] < 0:
        signal_strength -= 1

    if latest['ema_fast'] > latest['ema_slow']:
        signal_strength += 1
    elif latest['ema_fast'] < latest['ema_slow']:
        signal_strength -= 1

    if signal_strength == 3:
        return "FORTE BUY", latest['Close'], latest['atr']
    elif signal_strength == -3:
        return "FORTE SELL", latest['Close'], latest['atr']
    else:
        return None, None, None

def calculate_tp_sl(price, atr, direction):
    if direction == "BUY":
        tp = price + atr * 3
        sl = price - atr * 1.5
    else:
        tp = price - atr * 3
        sl = price + atr * 1.5
    return round(tp, 2), round(sl, 2)

def calculate_lot_size(account_balance, risk_percent, sl_pips, pip_value=10):
    risk_amount = account_balance * (risk_percent / 100)
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(lot_size, 2)

def main():
    while True:
        for symbol, name in symbols.items():
            df = get_data(symbol)
            if df is not None:
                signal, price, atr = analyze(df)
                if signal:
                    direction = "BUY" if "BUY" in signal else "SELL"
                    tp, sl = calculate_tp_sl(price, atr, direction)
                    sl_pips = abs(price - sl)
                    lot = calculate_lot_size(5000, 2, sl_pips)
                    message = (
                        f"{signal} su {name}\n"
                        f"Prezzo: {price:.2f}\nTP: {tp}\nSL: {sl}\n"
                        f"Lottaggio consigliato: {lot} lotti (su 5.000$ con rischio 2%)"
                    )
                    send_signal(message)
        time.sleep(900)  # 15 minuti

if __name__ == "__main__":
    main()
