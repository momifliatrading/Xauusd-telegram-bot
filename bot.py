import requests
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import telegram
import time

# === CONFIG ===
TELEGRAM_TOKEN = '8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8'
CHAT_ID = '585847488'
API_KEYS = ['4G8M6XH4J90KZ71K', 'HSQEM45D73VB2136']
SYMBOLS = ['XAU/USD', 'EUR/USD']
CAPITAL = 5000
RISK_PERCENTAGE = 0.02

bot = telegram.Bot(token=TELEGRAM_TOKEN)
api_index = 0
no_signal_counter = {symbol: 0 for symbol in SYMBOLS}

# === FUNZIONI ===

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": f"[ALERT] {message}"}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Errore invio alert Telegram: {response.text}")
    except Exception as e:
        print(f"Errore nella funzione send_telegram_alert: {e}")

def get_alpha_vantage_data(symbol, interval='30min', api_key=''):
    function = "FX_INTRADAY"
    from_symbol, to_symbol = symbol.split('/')
    url = (
        f'https://www.alphavantage.co/query?function={function}&from_symbol={from_symbol}'
        f'&to_symbol={to_symbol}&interval={interval}&outputsize=compact&apikey={api_key}'
    )
    try:
        print(f"[INFO] Richiesta dati per {symbol} - URL: {url}")
        r = requests.get(url)
        data = r.json()
        key_data = f'Time Series FX ({interval})'
        if key_data not in data:
            send_telegram_alert(f"Errore: Dati non disponibili da Alpha Vantage per {symbol}")
            print(f"[ERRORE] Dati non trovati per {symbol}: {data}")
            return None
        df = pd.DataFrame(data[key_data]).T.astype(float)
        df.columns = ['open', 'high', 'low', 'close']
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        send_telegram_alert(f"Errore durante la richiesta dati per {symbol}: {e}")
        print(f"[EXCEPTION] Errore richiesta dati per {symbol}: {e}")
        return None

def analyze(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['ema'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    ichi = ta.trend.IchimokuIndicator(df['high'], df['low'])
    df['tenkan'] = ichi.ichimoku_conversion_line()
    df['kijun'] = ichi.ichimoku_base_line()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    signals = []

    if latest['rsi'] < 30 and latest['macd'] > latest['macd_signal'] and latest['close'] > latest['ema']:
        signals.append('FORTE BUY')
    elif latest['rsi'] > 70 and latest['macd'] < latest['macd_signal'] and latest['close'] < latest['ema']:
        signals.append('FORTE SELL')
    elif latest['rsi'] < 40 and latest['macd'] > latest['macd_signal']:
        signals.append('DEBOLE BUY')
    elif latest['rsi'] > 60 and latest['macd'] < latest['macd_signal']:
        signals.append('DEBOLE SELL')

    bb_confirm = latest['close'] < latest['bb_low'] or latest['close'] > latest['bb_high']
    ichi_confirm = latest['tenkan'] > latest['kijun'] if signals and 'BUY' in signals[0] else latest['tenkan'] < latest['kijun']

    if signals:
        confermato = bb_confirm or ichi_confirm
        return signals[0], latest['atr'], confermato
    return None, None, False

def calcola_lotto(atr, sl_pips):
    rischio = CAPITAL * RISK_PERCENTAGE
    valore_pip = rischio / sl_pips
    lotto = round(valore_pip / 10, 2)
    return max(lotto, 0.01)

def invia_messaggio(symbol, segnale, atr, confermato):
    sl = round(atr * 1.5, 3)
    tp = round(atr * (2.5 if 'FORTE' in segnale else 1.5), 3)
    lotto = calcola_lotto(atr, sl)

    stato = "CONFERMATO" if confermato else "DA CONFERMARE"
    msg = (
        f"**Segnale {segnale} su {symbol}**\n"
        f"Stato: {stato}\n"
        f"TP: {tp} | SL: {sl}\n"
        f"Lotto consigliato: {lotto}\n"
        f"Orario: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)

def job():
    global api_index
    for symbol in SYMBOLS:
        key = API_KEYS[api_index % len(API_KEYS)]
        api_index += 1

        df = get_alpha_vantage_data(symbol, api_key=key)
        if df is None:
            continue

        df = analyze(df)
        segnale, atr, confermato = generate_signal(df)

        if segnale:
            print(f"[INFO] Segnale per {symbol}: {segnale} (Confermato: {confermato})")
            invia_messaggio(symbol, segnale, atr, confermato)
            no_signal_counter[symbol] = 0
        else:
            no_signal_counter[symbol] += 1
            print(f"[INFO] Nessun segnale per {symbol}. Contatore: {no_signal_counter[symbol]}")
            if no_signal_counter[symbol] >= 6:
                send_telegram_alert(f"Nessun segnale su {symbol} da oltre 3 ore. Verifica funzionamento bot.")
                no_signal_counter[symbol] = 0

if __name__ == '__main__':
    scheduler = BackgroundScheduler(timezone=utc)
    trigger = IntervalTrigger(minutes=30, timezone=utc)
    scheduler.add_job(job, trigger)
    scheduler.start()
    print("Bot avviato. Premere CTRL+C per fermarlo.")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Bot arrestato.")
