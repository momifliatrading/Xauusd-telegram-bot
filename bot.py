import yfinance as yf

def get_price():
    ticker = yf.Ticker("XAUUSD=X")
    data = ticker.history(period="1m")
    if data.empty:
        return None
    return round(data['Close'].iloc[-1], 2)
