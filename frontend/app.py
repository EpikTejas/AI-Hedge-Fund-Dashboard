import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 🔹 Page config
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

# 🔹 Auto refresh every 100 sec
st_autorefresh(interval=100000)

# 🔹 Dark theme
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 AI Trading Dashboard")

# -----------------------------
# 🔹 Fetch Binance Data
# -----------------------------
def get_crypto_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=100"
    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df

# -----------------------------
# 🔹 RSI Calculation
# -----------------------------
def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# -----------------------------
# 🔹 Moving Average
# -----------------------------
def calculate_ma(df):
    return df["close"].rolling(20).mean()

# -----------------------------
# 🔹 AI Signal Logic (FIXED)
# -----------------------------
def generate_signal(df):
    rsi = calculate_rsi(df)
    ma = calculate_ma(df)

    last_price = df["close"].iloc[-1]
    last_ma = ma.iloc[-1]

    # 🔹 Volume
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    last_volume = df["volume"].iloc[-1]
    volume_spike = last_volume > avg_volume * 1.5

    # 🔹 Volatility
    volatility = df["close"].pct_change().std()
    low_volatility = volatility < 0.002

    score = 0
    reasons = []

    # RSI
    if rsi < 30:
        score += 1
        reasons.append("RSI oversold")
    elif rsi > 70:
        score -= 1
        reasons.append("RSI overbought")

    # Trend
    if last_price > last_ma:
        score += 1
        reasons.append("Uptrend")
    else:
        score -= 1
        reasons.append("Downtrend")

    # Volume boost
    if volume_spike:
        if score > 0:
            score += 1
        elif score < 0:
            score -= 1
        reasons.append("Volume spike")

    # Volatility filter
    if low_volatility:
        reasons.append("Low volatility")

    # Signal decision
    if score >= 2:
        signal = "BUY"
    elif score == 1:
        signal = "buy(weak)"
    elif score <= -2:
        signal = "SELL"
    elif score == -1:
        signal = "sell(weak)"
    else:
        signal = "HOLD"

    # 🔹 Confidence (fixed scaling)
    confidence = round(min(95, abs(score) * 30))

    reason = ", ".join(reasons)

    return signal, confidence, reason, ma

# -----------------------------
# 🔹 Chart
# -----------------------------
def plot_chart(df, ma):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Candles"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=ma,
        line=dict(width=2),
        name="MA (20)"
    ))

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=10, r=10, t=30, b=10)
    )

    return fig

# -----------------------------
# 🔹 Main Dashboard
# -----------------------------
coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
cols = st.columns(len(coins))

for i, coin in enumerate(coins):
    df = get_crypto_data(coin)

    signal, confidence, reason, ma = generate_signal(df)
    price = df["close"].iloc[-1]

    with cols[i]:
        st.subheader(coin)

        st.write(f"Price: ${round(price,2)}")
        st.write(f"Signal: {signal}")

        # 🔥 Confidence UI
        st.progress(confidence / 100)

        if confidence > 70:
            st.success(f"Confidence: {confidence}%")
        elif confidence > 40:
            st.warning(f"Confidence: {confidence}%")
        else:
            st.error(f"Confidence: {confidence}%")

        st.write(f"Reason: {reason}")

        fig = plot_chart(df, ma)
        st.plotly_chart(fig, use_container_width=True)
