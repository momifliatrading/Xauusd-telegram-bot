import requests
import pandas as pd
import time
import telegram
import ta

# === CONFIGURAZIONE ===
TOKEN = "8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8"
CHAT_ID = "585847488"
CAPITALE = 5000
RISCHIO_PCT = 0.02
symbols = {"XAU/USD": "XAUUSD", "EUR/USD": "EURUSD"}
API_KEYS = ["WURVR7KA6AES8K9B", "HSQEM45D73VB2136"]

bot = telegram.Bot(token=TOKEN)

def send_signal(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def get_data(symbol):
    for api_key in API_KEYS:
        url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[4:]}&interval=1min&apikey={api_key}&outputsize=compact"
        try:
            response = requests.get(url)
            data = response.json()
            if "Time Series FX (1min)" in data:
                df = pd.DataFrame(data['Time Series FX (1min)']).T.astype(float)
                df.columns = ['Open', 'High', 'Low', 'Close']
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                return df
        except:
            continue
    return None

def is_breakout(df):
    recent = df[-20:]
    max_high = recent['High'][:-1].max()
    min_low = recent['Low'][:-1].min()
    last_close = recent['Close'].iloc[-1]

    if last_close > max_high:
        return "BREAKOUT BUY"
    elif last_close < min_low:
        return "BREAKOUT SELL"
    return None

def confirm_candlestick(df):
    last = df.iloc[-2]
    current = df.iloc[-1]
    if current['Close'] > current['Open'] and last['Close'] < last['Open']:
        return "bullish_engulfing"
    elif current['Close'] < current['Open'] and last['Close'] > last['Open']:
        return "bearish_engulfing"
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

def calculate_lot_size(sl_pips):
    if sl_pips == 0: return 0.01
    risk_usd = CAPITALE * RISCHIO_PCT
    pip_value = 10
    lots = risk_usd / (sl_pips * pip_value)
    return round(min(max(lots, 0.01), 5), 2)

def main():
    while True:
        for name, symbol in symbols.items():
            df = get_data(symbol)
            if df is None:
                send_signal(f"Aggiornamento strategia:\nErrore nel recupero dati per {name}")
                continue

            signal, price, atr, strength = analyze(df)
            breakout = is_breakout(df)
            candle = confirm_candlestick(df)

            messaggio = f"Aggiornamento strategia ({name}):\n"
            messaggio += f"Prezzo attuale: {price:.5f}\n"

            if signal:
                tp, sl = calculate_tp_sl(price, atr, strength)
                sl_pips = abs(price - sl) * 100
                lot = calculate_lot_size(sl_pips)
                messaggio += f"Segnale tecnico: {signal}\nTP: {tp}, SL: {sl}\nLotto: {lot}\n"
            if breakout:
                messaggio += f"Breakout rilevato: {breakout}\n"
            if candle:
                messaggio += f"Conferma candlestick: {candle.replace('_', ' ').capitalize()}\n"

            if not signal and not breakout:
                messaggio += "Nessun segnale forte al momento.\n"

            send_signal(messaggio)
        time.sleep(1800)  # ogni 30 minuti

if __name__ == "__main__":
    main()
