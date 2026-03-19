import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import logging
import matplotlib.pyplot as plt
import mplfinance as mpf
from scipy.signal import find_peaks
import tensorflow as tf
from tensorflow.keras import layers, models
import plotly.graph_objects as go
import ta
from PIL import Image

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Deep Learning Pattern Scanner", layout="wide")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

DATA_DIR = "data"
DATASET_DIR = "dataset"
MODEL_DIR = "models"
CATEGORIES = ['double_top', 'double_bottom', 'head_shoulders', 'inverse_head_shoulders', 'none']
MODEL_PATH = os.path.join(MODEL_DIR, "pattern_cnn.keras")
CLASSES_PATH = os.path.join(MODEL_DIR, "classes.txt")

for d in [DATA_DIR, MODEL_DIR] + [os.path.join(DATASET_DIR, cat) for cat in CATEGORIES]:
    os.makedirs(d, exist_ok=True)

# ==========================================
# 2. DATA FETCHING LOGIC
# ==========================================
def fetch_data(ticker="RELIANCE.NS", interval="1m", period="7d"):
    """Fetches stock data and handles multi-index issues."""
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            return None
        
        # Flatten Multi-Index columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        data.reset_index(inplace=True)
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        # Add RSI
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# ==========================================
# 3. IMAGE GENERATION & AUTO-LABELING
# ==========================================
def heuristic_labeler(close_prices):
    """Basic algorithmic heuristic to synthetically label historical data."""
    peaks, _ = find_peaks(close_prices, distance=10, prominence=np.std(close_prices)*0.5)
    troughs, _ = find_peaks(-close_prices, distance=10, prominence=np.std(close_prices)*0.5)
    
    if len(peaks) >= 2:
        p1, p2 = close_prices[peaks[-2]], close_prices[peaks[-1]]
        if abs(p1 - p2) / p1 < 0.01: return 'double_top'
            
    if len(troughs) >= 2:
        t1, t2 = close_prices[troughs[-2]], close_prices[troughs[-1]]
        if abs(t1 - t2) / t1 < 0.01: return 'double_bottom'
            
    if len(peaks) >= 3:
        p1, p2, p3 = close_prices[peaks[-3]], close_prices[peaks[-2]], close_prices[peaks[-1]]
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.02: return 'head_shoulders'

    if len(troughs) >= 3:
        t1, t2, t3 = close_prices[troughs[-3]], close_prices[troughs[-2]], close_prices[troughs[-1]]
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.02: return 'inverse_head_shoulders'
            
    return 'none'

def generate_images(df, window_size=50):
    """Generates pure candlestick images over a sliding window."""
    if df is None or len(df) < window_size:
        return 0

    df_plot = df.copy()
    df_plot['Date'] = pd.to_datetime(df_plot['Date'])
    df_plot.set_index('Date', inplace=True)
    
    mc = mpf.make_marketcolors(up='w', down='b', edge='black', wick='black')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='', y_on_right=False)

    count = 0
    for i in range(0, len(df_plot) - window_size, 5):
        window_df = df_plot.iloc[i:i+window_size]
        label = heuristic_labeler(window_df['Close'].values)
        
        filename = f"{label}_{df_plot.index[i+window_size-1].strftime('%Y%m%d%H%M')}.png"
        filepath = os.path.join(DATASET_DIR, label, filename)
        
        if not os.path.exists(filepath):
            fig, ax = plt.subplots(figsize=(3, 3), dpi=64)
            mpf.plot(window_df, type='candle', style=s, ax=ax, axisoff=True)
            plt.savefig(filepath, bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            count += 1
    return count

# ==========================================
# 4. CNN MODEL TRAINING
# ==========================================
def build_and_train_model(epochs=5):
    IMG_HEIGHT, IMG_WIDTH, BATCH_SIZE = 128, 128, 32
    
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR, validation_split=0.2, subset="training",
        seed=123, image_size=(IMG_HEIGHT, IMG_WIDTH), batch_size=BATCH_SIZE)

    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR, validation_split=0.2, subset="validation",
        seed=123, image_size=(IMG_HEIGHT, IMG_WIDTH), batch_size=BATCH_SIZE)

    class_names = train_ds.class_names

    model = models.Sequential([
        layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
        layers.Rescaling(1./255),
        layers.Conv2D(32, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(len(class_names), activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    history = model.fit(train_ds, validation_data=val_ds, epochs=epochs)
    
    model.save(MODEL_PATH)
    with open(CLASSES_PATH, "w") as f:
        f.write(",".join(class_names))
        
    return history.history['accuracy'][-1], class_names

# ==========================================
# 5. INFERENCE LOGIC
# ==========================================
@st.cache_resource
def load_detector():
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASSES_PATH):
        model = tf.keras.models.load_model(MODEL_PATH)
        with open(CLASSES_PATH, "r") as f:
            classes = f.read().split(",")
        return model, classes
    return None, None

def predict_pattern(model, class_names, df_window):
    """Generates a temp image of the current window and predicts."""
    df_plot = df_window.copy()
    df_plot['Date'] = pd.to_datetime(df_plot['Date'])
    df_plot.set_index('Date', inplace=True)
    
    mc = mpf.make_marketcolors(up='w', down='b', edge='black', wick='black')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='', y_on_right=False)
    
    tmp_path = "temp_predict.png"
    fig, ax = plt.subplots(figsize=(3, 3), dpi=64)
    mpf.plot(df_plot, type='candle', style=s, ax=ax, axisoff=True)
    plt.savefig(tmp_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    
    img = tf.keras.utils.load_img(tmp_path, target_size=(128, 128))
    img_array = tf.expand_dims(tf.keras.utils.img_to_array(img), 0)
    
    predictions = model.predict(img_array, verbose=0)
    score = tf.nn.softmax(predictions[0])
    
    os.remove(tmp_path)
    return class_names[np.argmax(score)], 100 * np.max(score)

# ==========================================
# 6. STREAMLIT UI DASHBOARD
# ==========================================
st.title("📈 Deep Learning Stock Pattern Scanner")

tab1, tab2 = st.tabs(["📊 Live Scanner Dashboard", "⚙️ Setup & Model Training"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.sidebar.header("Scanner Settings")
    tickers = st.sidebar.text_input("Stocks (Comma separated)", "RELIANCE.NS, TCS.NS").split(",")
    interval = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])
    window_size = st.sidebar.slider("Pattern Lookback Window", 30, 100, 50)
    
    model, class_names = load_detector()
    
    if st.button("Scan Now"):
        for ticker in tickers:
            ticker = ticker.strip()
            st.markdown(f"### Analysis for {ticker} ({interval})")
            
            df = fetch_data(ticker, interval)
            if df is None or len(df) < window_size:
                st.error(f"Not enough data for {ticker}")
                continue
                
            latest_window = df.tail(window_size)
            col1, col2 = st.columns([3, 1])
            
            with col1:
                fig = go.Figure(data=[go.Candlestick(
                    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candles'
                )])
                # Highlight scan area
                fig.add_vrect(
                    x0=latest_window['Date'].iloc[0], x1=latest_window['Date'].iloc[-1], 
                    fillcolor="LightSalmon", opacity=0.2, line_width=0, annotation_text="Scan Window"
                )
                fig.update_layout(xaxis_rangeslider_visible=False, height=400, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.write("#### AI Prediction")
                if model is None:
                    st.warning("⚠️ Model not trained. Go to Setup tab.")
                else:
                    pattern, confidence = predict_pattern(model, class_names, latest_window)
                    if pattern == "none":
                        st.info("No distinct pattern detected.")
                    else:
                        st.success(f"**Pattern:** {pattern.replace('_', ' ').title()}")
                        st.progress(confidence / 100.0)
                        st.caption(f"Confidence: {confidence:.2f}%")
                
                rsi_val = latest_window['RSI'].iloc[-1]
                st.metric("Latest RSI (14)", f"{rsi_val:.2f}")
                if rsi_val > 70: st.error("Status: Overbought")
                elif rsi_val < 30: st.success("Status: Oversold")
                else: st.info("Status: Neutral")
            st.divider()

# --- TAB 2: SETUP & TRAINING ---
with tab2:
    st.header("System Setup & CNN Training")
    st.markdown("Use this section to build your dataset and train the CNN. **Run these steps sequentially if this is your first time.**")
    
    colA, colB, colC = st.columns(3)
    
    with colA:
        st.subheader("1. Download Data")
        setup_ticker = st.text_input("Ticker for dataset", "RELIANCE.NS")
        if st.button("Download 7d Data"):
            with st.spinner("Fetching..."):
                df = fetch_data(setup_ticker, "1m", "7d")
                if df is not None:
                    df.to_csv(os.path.join(DATA_DIR, f"{setup_ticker}_raw.csv"), index=False)
                    st.success(f"Downloaded {len(df)} rows.")
    
    with colB:
        st.subheader("2. Generate Images")
        if st.button("Create Image Dataset"):
            with st.spinner("Converting charts to images..."):
                file_path = os.path.join(DATA_DIR, f"{setup_ticker}_raw.csv")
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    count = generate_images(df)
                    st.success(f"Generated {count} new images.")
                else:
                    st.error("No raw data found. Do Step 1 first.")
                    
    with colC:
        st.subheader("3. Train CNN Model")
        epochs = st.number_input("Epochs", min_value=1, max_value=50, value=5)
        if st.button("Start Training"):
            with st.spinner(f"Training CNN for {epochs} epochs... (This may take a moment)"):
                try:
                    final_acc, classes = build_and_train_model(epochs)
                    st.success(f"Training Complete! Final Accuracy: {final_acc:.2f}")
                    st.write(f"Classes modeled: {classes}")
                    st.info("Model saved! You can now use the Live Scanner Dashboard.")
                    # Clear cache so the scanner loads the new model
                    load_detector.clear() 
                except Exception as e:
                    st.error(f"Error during training: Make sure you have enough generated images in the dataset folders. Details: {e}")
