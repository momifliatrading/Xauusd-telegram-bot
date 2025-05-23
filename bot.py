import requests
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import telegram
import matplotlib.pyplot as plt
import time

# === CONFIG ===
TELEGRAM_TOKEN = '8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8'
CHAT_ID = '585847488'
API_KEY = '8K05187USSNGO28Q'
SYMBOLS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF']
CAPITAL = 5000
RISK_PERCENTAGE = 0.02

bot = telegram.Bot(token=TELEGRAM_TOKEN)
segnali_generati = 0

def get_alpha_vantage_data(symbol, interval='1min', api_key=''):
    function = "FX_INTRADAY"
    from_symbol, to_symbol = symbol.split('/')
    url = (
        f'https://www.alphavantage.co/query?function={function}&from_symbol={from_symbol}'
        f'&to_symbol={to_symbol}&interval={interval}&outputsize=compact&apikey={api_key}'
    )
    r = requests.get(url)
    try:
        data = r.json()
    except Exception as e:
        return None

    key_fx = f'Time Series FX ({interval})'
    if key_fx not in data:
        return None

    df = pd.DataFrame(data[key_fx]).T.astype(float)
    df.columns = ['open', 'high', 'low', 'close']
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df

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

def plot_chart(df, symbol, signal):
    fig, ax = plt.subplots(figsize=(10, 5))
    for i in range(len(df)):
        color = 'green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
        ax.plot([df.index[i], df.index[i]], [df['low'].iloc[i], df['high'].iloc[i]], color=color)
        ax.plot([df.index[i], df.index[i]], [df['open'].iloc[i], df['close'].iloc[i]], color=color, linewidth=4)

    ax.plot(df.index, df['ema'], label='EMA 50', linestyle='--', linewidth=1.2)
    ax.set_title(f"{symbol} - Segnale: {signal}")
    ax.legend()
    ax.grid(True)
    file_path = f"{symbol.replace('/', '_')}_chart.png"
    plt.tight_layout()
    plt.savefig(file_path)
    plt.close()
    return file_path

def invia_messaggio(symbol, segnale, atr, confermato, df):
    global segnali_generati
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

    # Invio immagine
    image_path = plot_chart(df.tail(50), symbol, segnale)
    with open(image_path, 'rb') as f:
        bot.send_photo(chat_id=CHAT_ID, photo=f)

    segnali_generati += 1

def job():
    for symbol in SYMBOLS:
        df = get_alpha_vantage_data(symbol, interval='1min', api_key=API_KEY)
        if df is None:
            continue
        df = analyze(df)
        segnale, atr, confermato = generate_signal(df)
        if segnale:
            invia_messaggio(symbol, segnale, atr, confermato, df)

def report_status():
    global segnali_generati
    msg = (
        f"[STATUS] Il bot è attivo.\n"
        f"Ultimo controllo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Segnali rilevati nelle ultime 3 ore: {segnali_generati}"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg)
    segnali_generati = 0

def alive_message():
    bot.send_message(chat_id=CHAT_ID, text="Bot ancora attivo.")

if __name__ == '__main__':
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.add_job(job, IntervalTrigger(minutes=3, timezone=utc))
    scheduler.add_job(report_status, IntervalTrigger(hours=3, timezone=utc))
    scheduler.add_job(alive_message, IntervalTrigger(hours=1, timezone=utc))
    scheduler.start()
    print("Bot avviato.")
    bot.send_message(chat_id=CHAT_ID, text="Bot avviato e funzionante!")

    try:
        while True:
            time.sleep(1)
    except Exception as e:
        bot.send_message(chat_id=CHAT_ID, text=f"BOT FERMATO! Errore: {str(e)}")
        scheduler.shutdown()
    except (KeyboardInterrupt, SystemExit):
        bot.send_message(chat_id=CHAT_ID, text="Bot arrestato manualmente.")
        scheduler.shutdown()
        def invia_messaggio(symbol, segnale, atr, confermato, df):
    global segnali_generati

    # Filtro sicurezza: blocca segnali con ATR troppo basso
    if atr < 0.0005:  # Puoi regolare questa soglia per ogni simbolo!
        print(f"Segnale scartato su {symbol}: ATR troppo basso ({atr})")
        return  # Non invia il messaggio e non calcola niente

    sl = round(atr * 1.5, 3)
    tp = round(atr * (2.5 if 'FORTE' in segnale else 1.5), 3)
    
    # Ulteriore sicurezza: se SL o TP sono comunque troppo bassi
    if sl < 0.0005 or tp < 0.0005:
        print(f"Segnale scartato su {symbol}: SL o TP troppo bassi (SL: {sl}, TP: {tp})")
        return

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

    image_path = plot_chart(df.tail(50), symbol, segnale)
    with open(image_path, 'rb') as f:
        bot.send_photo(chat_id=CHAT_ID, photo=f)

    segnali_generati += 1
