
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

# ==========================================
# USER CONFIGURATION
# ==========================================
TICKER = "NDX"   # Try Bitcoin, SPY, QQQ, NVDA, etc.
START_DATE = "1995-01-01"
END_DATE = "2026-01-31" # Near the 2021 peak of Bitcoin
# ==========================================

# ==========================================

if __name__ == '__main__':
    print(f"Fetching data for {TICKER} from {START_DATE} to {END_DATE}...")
    data = yf.download(TICKER, start=START_DATE, end=END_DATE)

    if len(data) == 0:
        print("Error: No data found. Please check ticker and dates.")
        exit()

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
    lppls_model.plot_fit()
    plt.title(f"LPPLS Fit: {TICKER}")
    plt.savefig(f'{TICKER}_fit.png')
    print(f"Saved plot to {TICKER}_fit.png")

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

    lppls_model.plot_confidence_indicators(res)
    plt.savefig(f'{TICKER}_confidence.png')
    print(f"Saved confidence plot to {TICKER}_confidence.png")

    print(f"Projected Critical Time (tc): {tc}")
    dt_tc = datetime.fromordinal(int(tc))
    print(f"Predicted turning point date: {dt_tc.strftime('%Y-%m-%d')}")

