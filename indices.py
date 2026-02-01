
import matplotlib
matplotlib.use('Agg') # Save plots to files
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import glob
import re

try:
    from lppls.lppls import lppls
except ImportError:
    from lppls import lppls

# ==========================================
# CONFIGURATION
# ==========================================
TICKERS = ["^NDX", "SPY", "^GSPC", "QQQ", "BTC-USD"]
START_DATE = "2019-01-01"
OUTPUT_DIR = "daily_plots"
KEEP_HISTORY_DAYS = 3
# ==========================================

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_unique_dates_from_files(directory):
    files = glob.glob(os.path.join(directory, "*.png"))
    dates = set()
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    
    for f in files:
        basename = os.path.basename(f)
        match = date_pattern.search(basename)
        if match:
            dates.add(match.group(0))
    return sorted(list(dates))

def cleanup_old_files(directory, keep_count):
    print(f"Cleaning up old files in {directory}...")
    unique_dates = get_unique_dates_from_files(directory)
    
    if len(unique_dates) <= keep_count:
        print("No files to delete.")
        return

    # Dates to delete (all except last 'keep_count')
    dates_to_delete = unique_dates[:-keep_count]
    print(f"Deleting files from dates: {dates_to_delete}")
    
    files = glob.glob(os.path.join(directory, "*.png"))
    for f in files:
        for d in dates_to_delete:
            if d in f:
                try:
                    os.remove(f)
                    print(f"Deleted {f}")
                except OSError as e:
                    print(f"Error deleting {f}: {e}")

def run_analysis():
    ensure_dir(OUTPUT_DIR)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    # Use tomorrow as end_date to ensure we get today's data from yfinance
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    for ticker in TICKERS:
        print(f"--- Processing {ticker} ---")
        try:
            # Fetch Data
            data = yf.download(ticker, start=START_DATE, end=end_date)
            if len(data) == 0:
                print(f"Error: No data found for {ticker}")
                continue
            
            # Flatten columns if multi-index
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Preprocess
            time = [pd.Timestamp.toordinal(pd.Timestamp(t1)) for t1 in data.index]
            price = np.log(data['Close'].values)
            observations = np.array([time, price])
            
            # Initialize & Fit
            lppls_model = lppls.LPPLS(observations=observations)
            # Reduced searches for speed in daily runs, but keeping it robust enough
            MAX_SEARCHES = 25 
            tc, m, w, a, b, c, c1, c2, O, D = lppls_model.fit(MAX_SEARCHES)
            
            # Plot Fit
            plt.close('all') # Clear previous figures
            lppls_model.plot_fit()
            plt.title(f"LPPLS Fit: {ticker} ({today_str})")
            safe_ticker = ticker.replace('^', '') # Remove caret for filename
            fit_filename = os.path.join(OUTPUT_DIR, f"{safe_ticker}_{today_str}_fit.png")
            plt.savefig(fit_filename)
            print(f"Saved {fit_filename}")
            
            # Confidence Indicators
            # Using parameters balanced for daily run speed vs accuracy
            res = lppls_model.mp_compute_nested_fits(
                workers=4,
                window_size=120, 
                smallest_window_size=30, 
                outer_increment=1, 
                inner_increment=5, 
                max_searches=25,
            )
            
            plt.close('all')
            lppls_model.plot_confidence_indicators(res)
            plt.title(f"Confidence: {ticker} ({today_str})")
            conf_filename = os.path.join(OUTPUT_DIR, f"{safe_ticker}_{today_str}_confidence.png")
            plt.savefig(conf_filename)
            print(f"Saved {conf_filename}")
            
        except Exception as e:
            print(f"Failed to process {ticker}: {e}")
            import traceback
            traceback.print_exc()

    # Cleanup old runs
    cleanup_old_files(OUTPUT_DIR, KEEP_HISTORY_DAYS)

if __name__ == '__main__':
    run_analysis()
