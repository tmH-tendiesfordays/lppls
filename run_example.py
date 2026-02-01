
import matplotlib
matplotlib.use('Agg') # Set backend to non-interactive to save files instead of showing windows
import matplotlib.pyplot as plt
try:
    from lppls.lppls import lppls, data_loader
except ImportError:
    from lppls import lppls, data_loader
import numpy as np
import pandas as pd
from datetime import datetime as dt

print("Starting LPPLS example run...")

# read example dataset into df 
data = data_loader.nasdaq_dotcom()
print(f"Loaded data: {len(data)} rows")

# convert time to ordinal
time = [pd.Timestamp.toordinal(dt.strptime(t1, '%Y-%m-%d')) for t1 in data['Date']]

# create list of observation data
price = np.log(data['Adj Close'].values)

# create observations array (expected format for LPPLS observations)
observations = np.array([time, price])

# Use a smaller subset for the quick demo
print("Slicing data to first 200 points for speed...")
observations = observations[:, :200]

# Use a smaller subset for the quick demo
observations = observations[:, :200]
print(f"Using subset of data: {observations.shape[1]} points")

# set the max number for searches to perform before giving-up
# the literature suggests 25
MAX_SEARCHES = 25

# instantiate a new LPPLS model with the Nasdaq Dot-com bubble dataset
lppls_model = lppls.LPPLS(observations=observations)

# fit the model to the data and get back the params
print("Fitting model...")
tc, m, w, a, b, c, c1, c2, O, D = lppls_model.fit(MAX_SEARCHES)
print("Model fitted.")

# visualize the fit
print("Plotting fit...")
lppls_model.plot_fit()
plt.savefig('example_fit.png')
print("Fit plot saved to example_fit.png")

# compute the confidence indicator
print("Computing confidence indicators (this might take a moment)...")
res = lppls_model.mp_compute_nested_fits(
    workers=4, # Reduced workers for safety in environment
    window_size=120, 
    smallest_window_size=30, 
    outer_increment=1, 
    inner_increment=5, 
    max_searches=25,
    # filter_conditions_config={} # not implemented in 0.6.x
)

print("Plotting confidence indicators...")
lppls_model.plot_confidence_indicators(res)
plt.savefig('example_confidence.png')
print("Confidence indicators plot saved to example_confidence.png")

print("Example run completed successfully.")
