import yfinance as yf
import requests

def get_price():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1m")
    if data.empty:
        return None
    return round(data['Close'].iloc[-1], 2)

def send_telegram_message(message):
    bot_token = 'YOUR_BOT_TOKEN'
    chat_id = 'YOUR_CHAT_ID'
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=payload)
    return response.json()

# Test
price = get_price()
if price:
    send_telegram_message(f"Prezzo attuale XAU/USD: {price}")
else:
    send_telegram_message("Errore nel recupero del prezzo.")
