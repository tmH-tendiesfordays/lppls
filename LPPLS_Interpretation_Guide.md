# LPPLS Interpretation & Usage Guide

This guide explains how to run the LPPLS model on your own data and, most importantly, how to interpret the generated graphs using the recent **NVDA (NVIDIA)** analysis as a case study.

---

## 1. How to Run Simulations

You can run the model on any ticker (stock, crypto, index) supported by Yahoo Finance.

1.  **Open the Config Script**:
    Open `custom_run.py` in your editor.

2.  **Edit Configuration**:
    Locate the "USER CONFIGURATION" section at the top:
    ```python
    TICKER = "NVDA"        # Symbol (e.g., "BTC-USD", "SPY", "AAPL")
    START_DATE = "2010-01-01"
    END_DATE = "2026-01-01"
    ```
    *   **TICKER**: The asset symbol.
    *   **Dates**: Ensure the range covers the bubble formation you want to analyze.

3.  **Run the Script**:
    Execute the script from your terminal:
    ```powershell
    python custom_run.py
    ```

4.  **Outputs**:
    The script will generate two images in the same folder:
    *   `{TICKER}_fit.png` (The visual fit)
    *   `{TICKER}_confidence.png` (The bubble probability indicators)

---

## 2. Interpreting the "Fit" Graph
**File:** `{TICKER}_fit.png`

This graph shows the price history overlaid with the model's "Theoretical Bubble" curve.

### The Axes
*   **X-Axis (Time)**: The date range of your data.
*   **Y-Axis (ln(p))**: The **Natural Logarithm** of the price.
    *   *Why Log?* On a normal chart, exponential growth looks like a curve. On a log chart, exponential growth looks like a straight line.
    *   **Super-Exponential**: The LPPLS model looks for lines that curve *upwards* even on a log chart. This acceleration is the signature of a bubble.

### The Lines
*   **<span style="color:blue">Blue Line (Price)</span>**: The actual market price history.
*   **<span style="color:orange">Orange Line (Fit)</span>**: The model's best attempt to mathematically describe the current bubble.

### What to Look For (The "Wobble")
A bubble isn't just a price going up; it's a price that oscillates faster and faster as it rises.
*   **Good Signal**: If the **Blue Price** peaks and dips perfectly in sync with the **Orange Fit** line's wobbles, this is strong confirmation. It means the "Herd Behavior" (greed vs. fear cycles) is following a predictable mathematical pattern.
*   **Crossing/Weaving**: It is healthy for the price to cross above and below the orange line. The orange line acts as the "center of gravity."

### Warning Signs (Divergence)
*   **Price Rips Way Above Fit**: If the Blue line shoots far above the Orange line, the market has gone "hyper-manic." This often precedes a crash.
*   **Price Drops Below Fit**: If the Blue line drops significantly below the Orange line and fails to recover, the positive feedback loop might be broken. The bubble may have "popped" early.

### NVDA Example Analysis
![NVDA Fit](NVDA_fit.png)
*   **2016 - 2019**: Notice how the Blue price hugs the Orange fit line closely, respecting the wobbles. The model captures the trend well.
*   **2022 - 2023**: A large dip where price fell below the trend, but it recovered.
*   **Current Status**: The price is weaving tightly around the fit line, suggesting the bubble regime is currently intact (the 'super-exponential' trend is still valid).

---

## 3. Interpreting the "Confidence" Graph
**File:** `{TICKER}_confidence.png`

This graph tells you how *reliable* the bubble signal is. The model runs hundreds of tests on different time windows (e.g., last 200 days, last 500 days).

### The Axes
*   **Left Y-Axis (Black Line)**: The Price (in Log scale) again, for reference.
*   **Right Y-Axis (Colored Spikes)**: **Confidence Indicator (0.0 to 1.0)**.
    *   **0.0 (0%)**: No agreement. No bubble detected.
    *   **0.5 (50%)**: Half of the tested timeframes agree a bubble is forming.
    *   **1.0 (100%)**: Perfect consensus. A critical signal.

### The Indicators
*   **<span style="color:red">Red Spikes (Pos)</span>**: Probability of a **Bubble Top / Crash**.
    *   Look for clustering of red spikes as the price rises.
    *   A high spike means "We are approaching the Critical Time ($t_c$)."
*   **<span style="color:green">Green Spikes (Neg)</span>**: Probability of a **Bubble Buttom / Rebound**.
    *   These occur during crashes, signaling distinct "fear" patterns that suggest the bottom is near.

### Date Precision
The X-axis shows monthly and yearly ticks. When you see a large Red Spike:
1.  Look at the date on the X-axis.
2.  That date corresponds to when the signal was generated.
3.  If you see high red spikes *now* (at the far right of the chart), it means the model predicts a crash is imminent.

### NVDA Example Analysis
![NVDA Confidence](NVDA_confidence.png)
*   **Top Chart (Red/Pos)**:
    *   Notice the clusters of red spikes during the rapid ascents.
    *   The recent data (far right) shows the indicator rising to nearly **0.6 (60%)**, suggesting growing consensus among the models that the current trend is becoming unstable.
*   **Bottom Chart (Green/Neg)**:
    *   Notice the massive green spike around **late 2018 / early 2019**.
    *   This perfectly marked the bottom of that correction, signaling a buying opportunity before the next rally.

---

## Summary
1.  **Run** `custom_run.py`.
2.  **Check Fit**: Does the Blue Price wiggle in sync with the Orange Fit?
3.  **Check Confidence**: are there Red Spikes (Crash Risk) or Green Spikes (Rebound Opportunity) appearing right now?
