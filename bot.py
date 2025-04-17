import requests
import pandas as pd
import time
import telegram
import ta

# Telegram
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
bot = telegram.Bot(token=TOKEN)

# Alpha Vantage
API_KEY = "WURVR7KA6AES8K9B"
symbols = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD"
}

CAPITALE = 5000
RISCHIO_PCT = 0.02

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
        signal = "FORTE BUY"
    elif signal_strength == -3:
        signal = "FORTE SELL"
    elif signal_strength == 2:
        signal = "BUY (debole)"
    elif signal_strength == -2:
        signal = "SELL (debole)"

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

def calculate_lot_size(sl_pips, symbol):
    if sl_pips == 0:
        return 0.01
    risk_usd = CAPITALE * RISCHIO_PCT
    pip_value = 10  # Per 1 lotto standard su coppie in USD
    lots = risk_usd / (sl_pips * pip_value)
    return round(min(max(lots, 0.01), 5), 2)

def main():
    while True:
        for name, symbol in symbols.items():
            df = get_data(symbol)
            if df is not None:
                signal, price, atr, strength = analyze(df)
                if signal:
                    tp, sl = calculate_tp_sl(price, atr, strength)
                    sl_pips = abs(price - sl) * 100  # Per calcolo lottaggio
                    lot = calculate_lot_size(sl_pips, symbol)
                    message = (
                        f"Strumento: {name}\n"
                        f"Segnale: {signal}\n"
                        f"Prezzo: {price:.5f}\n"
                        f"TP: {tp}\nSL: {sl}\n"
                        f"Lotto consigliato: {lot} (2% su $5000)"
                    )
                    send_signal(message)
        time.sleep(360)  # 6 minuti

if __name__ == "__main__":
    main()
