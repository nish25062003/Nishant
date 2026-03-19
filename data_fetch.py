import yfinance as yf
import pandas as pd
import os
import logging
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_and_update_data(ticker="RELIANCE.NS", interval="1m", period="7d"):
    """Fetches stock data and appends to local CSV to bypass 7-day 1m limit."""
    file_path = os.path.join(DATA_DIR, f"{ticker}_{interval}.csv")
    
    logging.info(f"Fetching {period} data for {ticker} at {interval} interval...")
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            logging.warning(f"No data returned for {ticker}.")
            return None
        
        # Flatten Multi-Index columns if present (yfinance latest versions)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        data.reset_index(inplace=True)
        # Standardize datetime column name
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        if os.path.exists(file_path):
            existing_data = pd.read_csv(file_path)
            # Combine and drop duplicates based on Date
            combined = pd.concat([existing_data, data])
            combined['Date'] = pd.to_datetime(combined['Date'], utc=True)
            combined.drop_duplicates(subset=['Date'], keep='last', inplace=True)
            combined.sort_values('Date', inplace=True)
            combined.to_csv(file_path, index=False)
            logging.info(f"Updated {file_path}. Total rows: {len(combined)}")
            return combined
        else:
            data.to_csv(file_path, index=False)
            logging.info(f"Created {file_path}. Total rows: {len(data)}")
            return data
            
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None

if __name__ == "__main__":
    # Test fetch
    fetch_and_update_data("RELIANCE.NS", "1m", "7d")
