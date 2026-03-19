import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import mplfinance as mpf
from scipy.signal import find_peaks
import logging

logging.basicConfig(level=logging.INFO)

DATASET_DIR = "dataset"
CATEGORIES = ['double_top', 'double_bottom', 'head_shoulders', 'inverse_head_shoulders', 'none']

for cat in CATEGORIES:
    os.makedirs(os.path.join(DATASET_DIR, cat), exist_ok=True)

def heuristic_labeler(close_prices):
    """
    Basic algorithmic heuristic to synthetically label historical data for CNN training.
    Returns the category string.
    """
    # Find local peaks and troughs
    peaks, _ = find_peaks(close_prices, distance=10, prominence=np.std(close_prices)*0.5)
    troughs, _ = find_peaks(-close_prices, distance=10, prominence=np.std(close_prices)*0.5)
    
    # Double Top Logic (2 peaks, roughly same height, separated by trough)
    if len(peaks) >= 2:
        p1, p2 = close_prices[peaks[-2]], close_prices[peaks[-1]]
        if abs(p1 - p2) / p1 < 0.01: # Within 1% height
            return 'double_top'
            
    # Double Bottom Logic (2 troughs, roughly same depth)
    if len(troughs) >= 2:
        t1, t2 = close_prices[troughs[-2]], close_prices[troughs[-1]]
        if abs(t1 - t2) / t1 < 0.01:
            return 'double_bottom'
            
    # Head and Shoulders (3 peaks: lower, higher, lower)
    if len(peaks) >= 3:
        p1, p2, p3 = close_prices[peaks[-3]], close_prices[peaks[-2]], close_prices[peaks[-1]]
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.02:
            return 'head_shoulders'

    # Inverse Head and Shoulders (3 troughs: higher, lower, higher)
    if len(troughs) >= 3:
        t1, t2, t3 = close_prices[troughs[-3]], close_prices[troughs[-2]], close_prices[troughs[-1]]
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.02:
            return 'inverse_head_shoulders'
            
    return 'none'

def generate_images(df, window_size=50, image_size=(3, 3)):
    """Generates pure candlestick images over a sliding window."""
    if df is None or len(df) < window_size:
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Custom style: black and white candles, no axes, no grids
    mc = mpf.make_marketcolors(up='w', down='b', edge='black', wick='black')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='', y_on_right=False)

    count = 0
    for i in range(0, len(df) - window_size, 5): # Slide window by 5 to avoid too much overlap
        window_df = df.iloc[i:i+window_size]
        
        # Determine label
        label = heuristic_labeler(window_df['Close'].values)
        
        # Save path
        filename = f"{label}_{df.index[i+window_size-1].strftime('%Y%m%d%H%M')}.png"
        filepath = os.path.join(DATASET_DIR, label, filename)
        
        # Generate clean chart
        fig, ax = plt.subplots(figsize=image_size, dpi=64)
        mpf.plot(window_df, type='candle', style=s, ax=ax, axisoff=True)
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        count += 1
        
    logging.info(f"Generated {count} images.")

if __name__ == "__main__":
    from data_fetch import fetch_and_update_data
    df = fetch_and_update_data("RELIANCE.NS")
    generate_images(df)
