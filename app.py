import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta
import os
import matplotlib.pyplot as plt
import mplfinance as mpf
from pattern_detector import PatternDetector

st.set_page_config(page_title="Deep Learning Pattern Scanner", layout="wide")

@st.cache_resource
def load_detector():
    return PatternDetector()

@st.cache_data(ttl=60) # Cache data for 60 seconds (optimized for speed)
def get_data(ticker, interval):
    data = yf.download(ticker, period="7d", interval=interval, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    
    # Add Bonus RSI Filter
    data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
    return data

def generate_temp_image(df):
    """Generate temporary image for inference"""
    mc = mpf.make_marketcolors(up='w', down='b', edge='black', wick='black')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='', y_on_right=False)
    fig, ax = plt.subplots(figsize=(3, 3), dpi=64)
    mpf.plot(df, type='candle', style=s, ax=ax, axisoff=True)
    
    tmp_path = "temp_predict.png"
    plt.savefig(tmp_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return tmp_path

# --- UI ---
st.title("📈 Deep Learning Stock Pattern Scanner")
st.markdown("Uses Convolutional Neural Networks (CNN) to detect classical chart patterns.")

# Sidebar
st.sidebar.header("Scanner Settings")
tickers = st.sidebar.text_input("Stocks (Comma separated)", "RELIANCE.NS, TCS.NS, INFY.NS").split(",")
interval = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])
window_size = st.sidebar.slider("Pattern Lookback Window", 30, 100, 50)

detector = load_detector()

for ticker in tickers:
    ticker = ticker.strip()
    st.subheader(f"Analysis for {ticker} ({interval})")
    
    df = get_data(ticker, interval)
    
    if df.empty:
        st.error(f"No data for {ticker}")
        continue
        
    # Get last N candles for pattern detection
    latest_window = df.tail(window_size).copy()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Plot Interactive Chart using Plotly
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'],
                        name='Candles')])
        
        # Highlight the analyzed window
        fig.add_vrect(x0=latest_window.index[0], x1=latest_window.index[-1], 
                      fillcolor="LightSalmon", opacity=0.2, layer="below", line_width=0,
                      annotation_text="CNN Scan Window", annotation_position="top left")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.write("### AI Analysis")
        # Generate image and predict
        tmp_img = generate_temp_image(latest_window)
        pattern, confidence = detector.predict(tmp_img)
        
        if pattern == "Model not loaded":
            st.warning("⚠️ Model not trained yet. Run `train.py`.")
        else:
            if pattern == "none":
                st.info("No defined pattern detected.")
            else:
                st.success(f"**Pattern Detected:** {pattern.replace('_', ' ').title()}")
                st.progress(confidence / 100.0)
                st.caption(f"Confidence: {confidence:.2f}%")
        
        st.metric("Latest RSI (14)", f"{latest_window['RSI'].iloc[-1]:.2f}")
        if latest_window['RSI'].iloc[-1] > 70:
            st.error("RSI indicates Overbought")
        elif latest_window['RSI'].iloc[-1] < 30:
            st.success("RSI indicates Oversold")

        if os.path.exists(tmp_img):
            os.remove(tmp_img)
