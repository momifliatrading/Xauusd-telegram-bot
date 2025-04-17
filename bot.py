import requests

# Inserisci il tuo token e chat ID
bot_token = '8062957086:AAFCPvaa9AJ04ZYD3Sm3yaE-Od4ExsO2HW8'
chat_id = '585847488'
message = 'Ciao! Questo è un messaggio di test dal bot XAU/USD.'

# URL dell'API Telegram
url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

# Parametri del messaggio
payload = {
    'chat_id': chat_id,
    'text': message
}

# Invia la richiesta
response = requests.post(url, data=payload)

# Mostra il risultato
if response.status_code == 200:
    print("Messaggio inviato con successo!")
else:
    print("Errore nell'invio del messaggio:", response.text)
