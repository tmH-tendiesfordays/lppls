
import matplotlib
matplotlib.use('Agg') # Save plots to files
import matplotlib.pyplot as plt
try:
    from lppls.lppls import lppls
except ImportError:
    from lppls import lppls
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# ==========================================
# USER CONFIGURATION
# ==========================================
TICKERS = ["SLV", "GLD"]   # List of tickers to analyze - ["^NDX", "SPY", "^GSPC", "QQQ", "BTC-USD"]
START_DATE = "2020-01-01"
# Use current date as End Date
END_DATE = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR = "manual_plots" # Sub-folder for results
# ==========================================

# ==========================================

if __name__ == '__main__':
    print(f"Running analysis from {START_DATE} to {END_DATE}")
    
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    # Generate a timestamp for this run (shared by all plots this session)
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for TICKER in TICKERS:
        print(f"\n{'='*40}")
        print(f"Processing: {TICKER}")
        print(f"{'='*40}")

        try:
            print(f"Fetching data for {TICKER} from {START_DATE} to {END_DATE}...")
            data = yf.download(TICKER, start=START_DATE, end=END_DATE)

            if len(data) == 0:
                print(f"Error: No data found for {TICKER}. Please check ticker and dates.")
                continue
            
            print(f"Downloaded Data Range: {data.index[0]} to {data.index[-1]}")

            # Flatten columns if multi-index (common in newer yfinance)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Prepare data for LPPLS
            # We need 'Date' as ordinal and 'Adj Close' (or 'Close')
            time = [pd.Timestamp.toordinal(pd.Timestamp(t1)) for t1 in data.index]
            price = np.log(data['Close'].values) # Use Log price for LPPLS

            # Create observations array [time, price]
            observations = np.array([time, price])

            print(f"Data points: {len(observations[0])}")

            # Initialize Model
            lppls_model = lppls.LPPLS(observations=observations)

            # Fit Model
            MAX_SEARCHES = 25
            print("Fitting LPPLS model...")
            tc, m, w, a, b, c, c1, c2, O, D = lppls_model.fit(MAX_SEARCHES)

            # Visualize Fit
            print(f"Plotting fit for {TICKER}...")
            # Clean filename (remove special chars like ^)
            safe_ticker = TICKER.replace('^', '')
            
            plt.close('all') # Ensure clean canvas
            lppls_model.plot_fit()
            plt.title(f"LPPLS Fit: {TICKER}")
            
            # IMPROVEMENT: Better Date Axis
            import matplotlib.dates as mdates
            ax = plt.gca()
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            plt.xticks(rotation=45)

            # Construct filename with subfolder and timestamp
            fit_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}_{run_timestamp}_fit.png')
            
            plt.savefig(fit_filename)
            print(f"Saved plot to {fit_filename}")

            # Calculate Confidence Indicators
            # NOTE: This takes time. We reduce window sizes for the demo but keep it robust enough to see.
            print("Calculating confidence indicators...")
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
            
            # IMPROVEMENT: Add Title
            plt.suptitle(f"Confidence Indicators: {TICKER} ({START_DATE} to {END_DATE})")

            # IMPROVEMENT: Better Date Axis for Confidence Plot (Subplots)
            fig = plt.gcf()
            for ax in fig.axes:
                 # Skip if axis is off (e.g. tables)
                if not ax.axison:
                    continue
                
                 # Only modify x-axis for bottom plots or all sharex
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
                # Rotate labels for visibility
                for label in ax.get_xticklabels():
                    label.set_rotation(45)

            conf_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}_{run_timestamp}_confidence.png')
            
            plt.savefig(conf_filename)
            print(f"Saved confidence plot to {conf_filename}")

            csv_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}_{run_timestamp}_confidence.csv')
            lppls_model.save_confidence_csv(res, csv_filename)

            print(f"Projected Critical Time (tc): {tc}")
            try:
                dt_tc = datetime.fromordinal(int(tc))
                print(f"Predicted turning point date: {dt_tc.strftime('%Y-%m-%d')}")
            except:
                print("Could not convert tc to date (out of range)")

        except Exception as e:
            print(f"Failed to process {TICKER}: {e}")
            import traceback
            traceback.print_exc()
