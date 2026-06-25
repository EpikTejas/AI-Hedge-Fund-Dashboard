from fastapi import FastAPI
import requests
import pandas as pd

app = FastAPI()

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def get_data(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": 100}
    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data)
    df = df.iloc[:, :6]
    df.columns = ["time","open","high","low","close","volume"]
    df["close"] = df["close"].astype(float)
    return df

def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_signal(df):
    df["RSI"] = calculate_rsi(df)
    df["MA50"] = df["close"].rolling(50).mean()
    df["MA100"] = df["close"].rolling(100).mean()

    latest = df.iloc[-1]

    score = 0
    reasons = []

    # RSI logic
    if latest["RSI"] < 30:
        score += 1
        reasons.append("RSI oversold")
    elif latest["RSI"] > 70:
        score -= 1
        reasons.append("RSI overbought")

    # Trend logic
    if latest["MA50"] > latest["MA100"]:
        score += 1
        reasons.append("Uptrend")
    else:
        score -= 1
        reasons.append("Downtrend")

    # Decision
    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = round(min(0.9, abs(score) / 2 + 0.1), 2)  # normalize (0–1)

    return signal, ", ".join(reasons), round(confidence, 2)

@app.get("/signals")
def get_signals():
    result = {}

    for coin in COINS:
        df = get_data(coin)
        signal, reason, confidence = generate_signal(df)

        result[coin] = {
            "price": float(df["close"].iloc[-1]),
            "signal": signal,
            "confidence": confidence,
            "reason": reason
        }

    return result
