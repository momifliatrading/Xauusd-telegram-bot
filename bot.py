import time
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot
import logging

# === CONFIG ===
TELEGRAM_TOKEN = '8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8'
CHAT_ID = '585847488'
ALPHA_VANTAGE_KEY = 'INSERISCI_LA_TUA_API_KEY'  # sostituisci con la tua API key
SYMBOLS = ['XAU/USD', 'EUR/USD']
CHECK_INTERVAL = 360  # 6 minuti
STATUS_INTERVAL = 1800  # 30 minuti
RISK_PER_TRADE = 0.02
CAPITAL = 5000

# === SETUP BOT ===
bot = Bot(token=TELEGRAM_TOKEN)

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        print(f"[Telegram] Sent: {text}")
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

def get_data(symbol):
    symbol_map = {
        'XAU/USD': 'XAUUSD',
        'EUR/USD': 'EURUSD'
    }
    fx_symbol = symbol_map[symbol]
    url = f'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={fx_symbol[:3]}&to_symbol={fx_symbol[3:]}&interval=5min&apikey={ALPHA_VANTAGE_KEY}&outputsize=compact'
    r = requests.get(url)
    data = r.json()

    try:
        df = pd.DataFrame(data['Time Series FX (5min)']).T.astype(float)
        df = df.rename(columns={
            '1. open': 'Open',
            '2. high': 'High',
            '3. low': 'Low',
            '4. close': 'Close'
        })
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        logging.error(f"Data error for {symbol}: {e}")
        return None

def calculate_indicators(df):
    df['EMA'] = df['Close'].ewm(span=21).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    df['MACD'], df['MACD_Signal'] = compute_macd(df['Close'])
    df['ATR'] = compute_atr(df)
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(series, short=12, long=26, signal=9):
    ema_short = series.ewm(span=short).mean()
    ema_long = series.ewm(span=long).mean()
    macd = ema_short - ema_long
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line

def compute_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def generate_signal(df):
    latest = df.iloc[-1]
    signals = {'RSI': None, 'MACD': None, 'EMA': None}

    # RSI
    if latest['RSI'] < 30:
        signals['RSI'] = 'BUY'
    elif latest['RSI'] > 70:
        signals['RSI'] = 'SELL'

    # MACD
    if latest['MACD'] > latest['MACD_Signal']:
        signals['MACD'] = 'BUY'
    elif latest['MACD'] < latest['MACD_Signal']:
        signals['MACD'] = 'SELL'

    # EMA
    if latest['Close'] > latest['EMA']:
        signals['EMA'] = 'BUY'
    elif latest['Close'] < latest['EMA']:
        signals['EMA'] = 'SELL'

    values = list(signals.values())
    if values.count('BUY') == 3:
        return 'FORTE BUY', latest['ATR']
    elif values.count('SELL') == 3:
        return 'FORTE SELL', latest['ATR']
    else:
        return 'NESSUN SEGNALE', latest['ATR']

def calculate_tp_sl(price, atr, direction):
    factor = 1.5
    if direction == 'BUY':
        return round(price + factor * atr, 2), round(price - factor * atr, 2)
    elif direction == 'SELL':
        return round(price - factor * atr, 2), round(price + factor * atr, 2)

def calculate_lot_size(atr, price):
    risk_amount = CAPITAL * RISK_PER_TRADE
    sl_pips = atr
    pip_value = 10  # USD per pip per lot
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(lot_size, 2)

# === MAIN LOOP ===
last_status_time = time.time()

while True:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    any_signal = False

    for symbol in SYMBOLS:
        df = get_data(symbol)
        if df is None:
            continue

        df = calculate_indicators(df)
        signal, atr = generate_signal(df)
        price = df['Close'].iloc[-1]

        if signal != 'NESSUN SEGNALE':
            tp, sl = calculate_tp_sl(price, atr, signal.split()[1])
            lot = calculate_lot_size(atr, price)
            msg = f"[{now}] {symbol}\nSegnale: {signal}\nPrezzo: {price}\nTP: {tp}\nSL: {sl}\nLot consigliato: {lot}"
            send_telegram_message(msg)
            any_signal = True
        else:
            print(f"[{now}] {symbol} - Nessun segnale forte.")

    # Invio aggiornamento ogni 30 minuti
    if time.time() - last_status_time > STATUS_INTERVAL:
        send_telegram_message(f"[{now}] ✅ Il bot è attivo. Nessun segnale forte rilevato negli ultimi 30 minuti.")
        last_status_time = time.time()

    time.sleep(CHECK_INTERVAL)
