# ==============================
# 📊 STOCK PATTERN SCANNER (ALL-IN-ONE)
# ==============================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from datetime import datetime

st.set_page_config(layout="wide")

# ==============================
# 🔹 USER INPUT
# ==============================

st.title("📈 AI Stock Pattern Scanner (1-Min Data + CNN Ready)")

ticker = st.text_input("Enter Stock", "RELIANCE.NS")
interval = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h"])
period = st.selectbox("Period", ["1d", "5d", "1mo"])

# ==============================
# 🔹 DATA FETCH
# ==============================

@st.cache_data
def load_data(ticker, interval, period):
    data = yf.download(ticker, interval=interval, period=period)

    # FIX Multi-index issue
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data.dropna(inplace=True)
    return data

# ==============================
# 🔹 PATTERN DETECTION LOGIC
# ==============================

def detect_patterns(data):

    # Breakout
    data['Resistance'] = data['High'].rolling(20).max()
    data['Breakout'] = data['Close'] > data['Resistance']

    # Breakdown
    data['Support'] = data['Low'].rolling(20).min()
    data['Breakdown'] = data['Close'] < data['Support']

    # Double Top (simple logic)
    data['Peak'] = (data['High'] > data['High'].shift(1)) & (data['High'] > data['High'].shift(-1))
    peaks = data[data['Peak']]

    double_top_idx = []
    for i in range(1, len(peaks)):
        if abs(peaks['High'].iloc[i] - peaks['High'].iloc[i-1]) < 2:
            double_top_idx.append(peaks.index[i])

    data['DoubleTop'] = data.index.isin(double_top_idx)

    return data

# ==============================
# 🔹 IMAGE GENERATION (CNN READY)
# ==============================

def save_chart_image(data, ticker):
    folder = "dataset"
    os.makedirs(folder, exist_ok=True)

    filename = f"{folder}/{ticker}_{datetime.now().strftime('%H%M%S')}.png"

    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close']
    )])

    fig.update_layout(xaxis_rangeslider_visible=False)

    fig.write_image(filename)
    return filename

# ==============================
# 🔹 MOCK CNN MODEL (REPLACE LATER)
# ==============================

def cnn_predict(image_path):
    # 🔥 Replace with real CNN later
    patterns = ["Double Top", "Breakout", "No Pattern"]
    probs = np.random.rand(len(patterns))
    probs = probs / probs.sum()

    idx = np.argmax(probs)
    return patterns[idx], round(probs[idx]*100, 2)

# ==============================
# 🔹 MAIN APP
# ==============================

if st.button("Run Scanner"):

    data = load_data(ticker, interval, period)

    if len(data) < 50:
        st.error("Not enough data")
        st.stop()

    data = detect_patterns(data)

    # ==============================
    # 📊 CHART
    # ==============================

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close']
    ))

    # Markers
    breakout = data[data['Breakout']]
    fig.add_trace(go.Scatter(
        x=breakout.index,
        y=breakout['Close'],
        mode='markers',
        name='Breakout',
        marker=dict(size=10, symbol='triangle-up')
    ))

    dt = data[data['DoubleTop']]
    fig.add_trace(go.Scatter(
        x=dt.index,
        y=dt['High'],
        mode='markers',
        name='Double Top',
        marker=dict(size=12, symbol='x')
    ))

    fig.update_layout(height=700, xaxis_rangeslider_visible=False)

    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # 🧠 CNN PART
    # ==============================

    st.subheader("🤖 AI Pattern Detection")

    image_path = save_chart_image(data.tail(50), ticker)

    pattern, confidence = cnn_predict(image_path)

    st.success(f"Detected Pattern: {pattern}")
    st.info(f"Confidence: {confidence}%")

    # ==============================
    # 📊 SUMMARY
    # ==============================

    st.subheader("📊 Signals Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Breakouts", int(data['Breakout'].sum()))
    col2.metric("Breakdowns", int(data['Breakdown'].sum()))
    col3.metric("Double Tops", int(data['DoubleTop'].sum()))
