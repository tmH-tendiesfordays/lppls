# LPPLS Analyzer

This project runs the **Log-Periodic Power Law Singularity (LPPLS)** model on financial data to detect bubble regimes and predict critical turning points (crashes or rebounds).

---

## 1. Setup & Installation

Before running any scripts, ensure your Python virtual environment is active.

**PowerShell:**
```powershell
.\lppls\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.\lppls\venv\Scripts\activate.bat
```

---

## 2. How to Run Simulations

You can run the model on any ticker (stock, crypto, index) supported by Yahoo Finance.

### Option A: Custom Analysis (`custom_run.py`)
Use this for ad-hoc analysis of specific assets.

1.  **Edit Configuration**:
    Open `custom_run.py` and modify the top section:
    ```python
    TICKERS = ["NVDA", "BTC-USD"]  # List of symbols
    START_DATE = "2020-01-01"      # Start of analysis window
    # END_DATE is set to today automatically
    ```
2.  **Run**:
    ```powershell
    python custom_run.py
    ```
3.  **Outputs**:
    Results are saved in the `manual_plots/` directory.

### Option B: Daily Automation (`indices.py`)
Use this for automated daily tracking of major indices.

1.  **Configuration**:
    The script has pre-configured tickers (e.g., ^NDX, SPY, BTC-USD).
2.  **Run**:
    ```powershell
    python indices.py
    ```
3.  **Outputs**:
    Results are saved in the `daily_plots/` directory.
    *   **Auto-Cleanup**: This script automatically deletes files older than 3 days to keep the folder clean.

---

## 3. Output Files & Features

For each analyzed ticker, the system generates three files:

1.  **`{TICKER}_{DATE}_fit.png`**:
    *   Visualizes the price history vs. the theoretical bubble curve.
2.  **`{TICKER}_{DATE}_confidence.png`**:
    *   Shows "Confidence Spikes" indicating the probability of a crash or rebound.
3.  **`{TICKER}_{DATE}_confidence.csv`** (New Feature):
    *   Contains the raw data for the confidence signals.
    *   **Columns**:
        *   `Date`: The date of the signal.
        *   `Value`: The strength of the signal (0.0 - 1.0).
        *   `Type`:
            *   **"Top"**: Indicates a potential market top (Crash risk).
            *   **"Bottom"**: Indicates a potential market bottom (Rebound opportunity).

---

## 4. Interpretation Guide

### The "Fit" Graph
**File:** `*_fit.png`

This graph shows the price history overlaid with the model's "Theoretical Bubble" curve.

*   **Blue Line (Price)**: Actual market price (Log scale).
*   **Orange Line (Fit)**: The mathematical model of the bubble.
*   **What to Look For**: Matches where the blue price line "wobbles" in sync with the orange fit line suggest a strong bubble regime.

### The "Confidence" Graph
**File:** `*_confidence.png`

This graph indicates how reliable the bubble signal is.

*   **Red Spikes (Pos)**: Probability of a **Bubble Top / Crash**.
*   **Green Spikes (Neg)**: Probability of a **Bubble Bottom / Rebound**.

**Interpreting Values**:
*   **0.0**: No signal.
*   **> 0.3**: Be alert.
*   **> 0.6**: Strong consensus among models; critical signal.

### Using the CSV Data
**File:** `*_confidence.csv`

Since the graphs can sometimes look crowded, use the CSV file to pinpoint exact dates.

*   **Example**:
    ```csv
    Date,Value,Type
    2024-03-20,0.4532,Top
    2022-10-15,0.6120,Bottom
    ```
*   Filter for `"Top"` to see crash warnings.
*   Filter for `"Bottom"` to see buying opportunities.

---
