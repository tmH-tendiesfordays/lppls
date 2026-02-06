
import matplotlib
matplotlib.use('Agg') # Save plots to files
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
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

def cleanup_ticker_dir(ticker_dir, keep_count):
    images_dir = os.path.join(ticker_dir, "images")
    reports_dir = os.path.join(ticker_dir, "reports")
    
    if not os.path.exists(images_dir):
        return

    print(f"Cleaning up old files in {ticker_dir}...")
    
    # Get unique dates from images
    files = glob.glob(os.path.join(images_dir, "*.png"))
    dates = set()
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    
    for f in files:
        basename = os.path.basename(f)
        match = date_pattern.search(basename)
        if match:
            dates.add(match.group(0))
            
    unique_dates = sorted(list(dates))
    
    if len(unique_dates) <= keep_count:
        print("No files to delete.")
        return

    # Dates to delete (all except last 'keep_count')
    dates_to_delete = unique_dates[:-keep_count]
    print(f"Deleting files from dates: {dates_to_delete}")
    
    # Delete from images and reports
    dirs_to_clean = [images_dir, reports_dir]
    types = ('*.png', '*.csv', '*.md', '*.pdf')
    
    for d_path in dirs_to_clean:
        if not os.path.exists(d_path):
            continue
            
        files_grabbed = []
        for t in types:
            files_grabbed.extend(glob.glob(os.path.join(d_path, t)))
            
        for f in files_grabbed:
            for d in dates_to_delete:
                if d in f:
                    try:
                        os.remove(f)
                        print(f"Deleted {f}")
                    except OSError as e:
                        print(f"Error deleting {f}: {e}")

def cluster_signals(df, col_name, signal_type):
    clusters = []
    # Filter for signals
    sig_df = df[df[col_name] > 0].copy()
    if sig_df.empty:
        return []
    
    sig_df = sig_df.sort_values("time")
    sig_df['date'] = sig_df['time'].apply(lambda t: pd.Timestamp.fromordinal(int(t)))
    
    # Group consecutive dates (gap > 1 day means new group)
    sig_df['grp'] = (sig_df['date'].diff().dt.days > 1).cumsum()
    
    for _, group in sig_df.groupby('grp'):
        start_date = group['date'].iloc[0].strftime('%Y-%m-%d')
        end_date = group['date'].iloc[-1].strftime('%Y-%m-%d')
        max_conf = group[col_name].max()
        
        date_range = start_date if start_date == end_date else f"{start_date} to {end_date}"
        clusters.append([date_range, f"{max_conf:.4f}", signal_type])
    return clusters

def run_analysis():
    ensure_dir(OUTPUT_DIR)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    # Use tomorrow as end_date to ensure we get today's data from yfinance
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    for ticker in TICKERS:
        print(f"--- Processing {ticker} ---")
        
        safe_ticker = ticker.replace('^', '') # Remove caret for filename
        
        # Create subfolders for this ticker
        ticker_dir = os.path.join(OUTPUT_DIR, safe_ticker)
        images_dir = os.path.join(ticker_dir, "images")
        reports_dir = os.path.join(ticker_dir, "reports")

        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

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
            # safe_ticker defined earlier
            fit_filename = os.path.join(images_dir, f"{safe_ticker}_{today_str}_fit.png")
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
            # IMPROVEMENT: Add Title using suptitle for shared title across subplots
            plt.suptitle(f"Confidence Indicators: {ticker} ({START_DATE} to {today_str})")
            # plt.title(f"Confidence: {ticker} ({today_str})") # Removed simple title in favor of suptitle
            conf_filename = os.path.join(images_dir, f"{safe_ticker}_{today_str}_confidence.png")
            plt.savefig(conf_filename)
            print(f"Saved {conf_filename}")

            csv_filename = os.path.join(reports_dir, f"{safe_ticker}_{today_str}_confidence.csv")
            lppls_model.save_confidence_csv(res, csv_filename)
            
            # ==========================================
            # 3. Cumulative Plot & Reports
            # ==========================================
            print(f"Generating reports for {ticker}...")
            
            # Process Data for Table
            res_df = lppls_model.compute_indicators(res)
            table_data = []
            table_data.extend(cluster_signals(res_df, "pos_conf", "Top"))
            table_data.extend(cluster_signals(res_df, "neg_conf", "Bottom"))
            # Sort Descending (Recent First)
            table_data.sort(key=lambda x: x[0][:10], reverse=True)
            
            # --- Cumulative Chart ---
            fig, ax1 = plt.subplots(figsize=(16, 10))
            
            ordinals = res_df["time"].astype("int32")
            dates_for_plot = [pd.Timestamp.fromordinal(d) for d in ordinals]
            price_series = np.exp(res_df["price"])
            
            ax1.plot(dates_for_plot, price_series, color='blue', label='Price', linewidth=1.5)
            ax1.set_ylabel('Price ($)', color='blue', fontsize=12)
            ax1.tick_params(axis='y', labelcolor='blue')
            ax1.grid(True, which='major', linestyle='--', alpha=0.7)
            ax1.grid(True, which='minor', linestyle=':', alpha=0.3) 

            # Twin Axis for Confidence
            ax2 = ax1.twinx()
            ax2.bar(dates_for_plot, res_df["pos_conf"], color='red', alpha=0.3, width=1.0, label='Confidence (Top)')
            ax2.bar(dates_for_plot, res_df["neg_conf"], color='green', alpha=0.3, width=1.0, label='Confidence (Bottom)')
            ax2.set_ylabel('Confidence Indicator', color='black', fontsize=12)
            ax2.set_ylim(0, 1.0)
            
            lines_1, labels_1 = ax1.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', fontsize=10)

            plt.title(f"{ticker} Analysis ({START_DATE} to {today_str})", fontsize=16)
            
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator()))
            ax1.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=1))
            
            cum_filename = os.path.join(images_dir, f'{safe_ticker}_{today_str}_cumulative.png')
            plt.savefig(cum_filename, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved {cum_filename}")

            # --- Signal Table ---
            table_filename = None
            if table_data:
                # Calculate lighter height logic
                num_rows = len(table_data) + 1 
                row_height_inch = 0.25
                header_height_inch = 0.5
                table_fig_height = header_height_inch + (num_rows * row_height_inch)
                table_fig_height = max(table_fig_height, 2.0)

                fig_table = plt.figure(figsize=(10, table_fig_height))
                ax_table = plt.gca()
                ax_table.axis('off')

                col_labels = ["Date Range", "Max Confidence", "Signal Type"]
                the_table = ax_table.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='center')
                the_table.auto_set_font_size(False)
                the_table.set_fontsize(10)
                the_table.scale(1, 1.2)
                
                for (row, col), cell in the_table.get_celld().items():
                    if row == 0:
                        cell.set_text_props(weight='bold')
                        cell.set_facecolor('#f0f0f0')
                
                table_filename = os.path.join(images_dir, f'{safe_ticker}_{today_str}_cumulative_table.png')
                plt.savefig(table_filename, bbox_inches='tight', pad_inches=0.2)
                plt.close(fig_table)
                print(f"Saved {table_filename}")

            # --- Summary Stats & Analyst Logic ---
            tc_str = "N/A"
            # 1. Critical Time Context
            tc_commentary = ""
            if tc != 0:
                try:
                    dt_tc = datetime.fromordinal(int(tc))
                    tc_str = dt_tc.strftime('%Y-%m-%d')
                    
                    dt_tc_obj = datetime.fromordinal(int(tc))
                    if dt_tc_obj < datetime.now():
                        tc_commentary = f"**Observation:** The projected Critical Time ({tc_str}) has passed. Since the crash/correction didn't strictly coincide with this date, the market may have entered a new regime or diffused the bubble pressure sideways."
                    else:
                        days_to_tc = (dt_tc_obj - datetime.now()).days
                        tc_commentary = f"**Observation:** We are currently **{days_to_tc} days** away from the projected critical point. Historical patterns suggest that price oscillations typically accelerate as we close this gap."
                except:
                    pass
            else:
                 tc_commentary = "**Observation:** No valid critical time ($t_c$) could be converged upon, possibly due to lack of distinct super-exponential behavior in the current window."

            # 2. Confidence Context
            conf_commentary = ""
            high_conf_signals = [row for row in table_data if float(row[1]) > 0.3]
            if high_conf_signals:
                conf_commentary = f"**Observation:** We see {len(high_conf_signals)} signal clusters with confidence > 30%. This 'agreement' across time scales reinforces the validity of the trend identification."
            else:
                conf_commentary = f"**Observation:** Most signals have low confidence (< 30%). This implies the model is detecting some super-exponential traces, but they are not yet uniform across all time scales (potentially just noise)."

            # 3. Recent Trend Context
            recent_commentary = ""
            if table_data:
                # Look at last 3 signals
                recent = table_data[:3]
                types = [r[2] for r in recent]
                if all(t == "Top" for t in types):
                    recent_commentary = "**Observation:** The last 3 detected signal clusters were all 'Top' signals. The market is persistently testing upper limits."
                elif all(t == "Bottom" for t in types):
                    recent_commentary = "**Observation:** The last 3 detected clusters were 'Bottom' signals, suggesting repeated capitulation or support testing."
                else:
                    recent_commentary = "**Observation:** Recent signals are mixed (both Top and Bottom), indicating high uncertainty or a transition phase."
            else:
                recent_commentary = "**Observation:** The absence of recent signals suggests the price is following a more linear or exponential walk without the accerelating oscillations characteristic of a bubble."

            num_top = sum(1 for row in table_data if row[2] == "Top")
            num_bot = sum(1 for row in table_data if row[2] == "Bottom")
            
            summary_text = (
                f"### Executive Summary\n"
                f"The analysis for **{ticker}** ({START_DATE} to {today_str}) has detected a total of **{len(table_data)}** significant LPPLS signals.\n\n"
                f"**Signal Breakdown:**\n"
                f"- **{num_top}** Top Signals (Red): Indication of bubble-like behavior and potential local maxima.\n"
                f"- **{num_bot}** Bottom Signals (Green): Indication of negative bubbles and potential buying opportunities.\n\n"
            )
            
            if table_data:
                last_sig = table_data[0]
                summary_text += (
                    f"**Recent Activity:**\n"
                    f"The most recent alert was a **{last_sig[2]}** signal observed during **{last_sig[0]}**, "
                    f"peaking at a confidence level of **{last_sig[1]}**. "
                    f"Traders should watch for price reaction around these levels."
                )
            else:
                summary_text += "No significant super-exponential signals were detected in this timeframe, suggesting price action is currently within visible bounds without extreme acceleration."
            
            
            
            # --- Markdown Report ---
            report_filename = os.path.join(reports_dir, f'{safe_ticker}_{today_str}_report.md')
            md_content = f"""# LPPLS Analyst Report: {ticker}
**Date:** {today_str}

---

## 1. Model Fit & Critical Time ($t_c$)

### What is this?
The **LPPLS (Log-Periodic Power Law Singularity)** model fits a super-exponential growth function to the price history to identify unsustainable trajectories. The **Critical Time ($t_c$)** represents the mathematical limit where the bubble component becomes finite—often coinciding with a change in regime (crash or major correction).

### Analysis
**Projected Critical Time:** {tc_str}

{tc_commentary}

**Visual Interpretation:**
- **Fit Line (Orange)**: Represents the theoretical super-exponential path.
- **Price (Blue)**: Actual market data.
- **Divergence**: If the Price is currently far below the Fit Line, the bubble may have already popped or valid parameters were not found. If Price is hugging the Orange line tightly parabolic, the trend is robust.

- **Divergence**: If the Price is currently far below the Fit Line, the bubble may have already popped or valid parameters were not found. If Price is hugging the Orange line tightly parabolic, the trend is robust.

![Fit](../images/{os.path.basename(fit_filename)})

---

## 2. Confidence Indicators (Multi-Scale)

### What is this?
Calculating $t_c$ on a single window can be noisy. This section performs **nested fits** across varying time windows (e.g., looking back 30 days vs 120 days).
- **Red Spikes**: Fraction of fits predicting a Top.
- **Green Spikes**: Fraction of fits predicting a Bottom.

### Analysis
High values (close to 1.0) indicate a **consensus** across different timeframes that a specific date was a critical point. Frequent clustering of these spikes suggests a high probability of a turning point.

{conf_commentary}

{conf_commentary}

![Confidence](../images/{os.path.basename(conf_filename)})

---

## 3. Cumulative Price & Signal Analysis

### What is this?
This chart overlays the Confidence Signals directly onto the Price History. It is the primary tool for timing.
- **Red Bars**: "Top" confidence. Look for these aligning with new price highs.
- **Green Bars**: "Bottom" confidence. Look for these aligning with price lows (capitulation).

### Analysis
Observe the clusters. A solitary spike might be noise, but a **dense cluster** of bars often precedes a trend reversal.

{recent_commentary}

{recent_commentary}

![Cumulative](../images/{os.path.basename(cum_filename)})

---

## 4. Signal Data Table

### What is this?
A detailed log of the signal clusters shown above, sorted by **Recency**.
- **Date Range**: The duration where the signal persisted.
- **Max Confidence**: The peak intensity (0.0 to 1.0).

- **Max Confidence**: The peak intensity (0.0 to 1.0).

![Table](../images/{os.path.basename(table_filename) if table_filename else 'No Signals'})

---

## 5. Analyst Conclusion
{summary_text}
"""
            with open(report_filename, "w") as f:
                f.write(md_content)
            print(f"Saved {report_filename}")
            
            # --- PDF Report ---
            pdf_filename = os.path.join(reports_dir, f'{safe_ticker}_{today_str}_report.pdf')
            with PdfPages(pdf_filename) as pdf:
                # Page 1: Text
                fig_text = plt.figure(figsize=(11.69, 8.27)) # A4 Landscape
                ax_text = fig_text.add_subplot(111); ax_text.axis('off')
                
                import textwrap
                wrapper = textwrap.TextWrapper(width=90, replace_whitespace=False)
                
                def wrap_paragraph(text):
                    lines = text.split('\n')
                    wrapped_lines = []
                    for line in lines:
                        if line.strip():
                            wrapped_lines.extend(wrapper.wrap(line))
                        else:
                            wrapped_lines.append("")
                    return "\n".join(wrapped_lines)

                clean_exec = summary_text.replace('### Executive Summary', 'EXECUTIVE SUMMARY').replace('**', '')

                raw_text = (
                    f"LPPLS Analyst Report: {ticker}\nDate: {today_str}\n\n"
                    f"Projected Critical Time (tc): {tc_str}\n\n"
                    f"{clean_exec}" 
                )
                
                final_text = wrap_paragraph(raw_text)
                
                ax_text.text(0.05, 0.95, final_text, transform=ax_text.transAxes, ha='left', va='top', fontsize=10, family='monospace')
                pdf.savefig(fig_text); plt.close(fig_text)
                
                # Pages 2-5: Images
                def add_page(path, title):
                    if path and os.path.exists(path):
                        try:
                            img = mpimg.imread(path)
                            h, w, _ = img.shape
                            fig_img = plt.figure(figsize=(11, 11 * (h/w))) 
                            ax_img = fig_img.add_subplot(111)
                            ax_img.imshow(img); ax_img.axis('off'); ax_img.set_title(title)
                            pdf.savefig(fig_img, bbox_inches='tight'); plt.close(fig_img)
                        except: pass
                
                add_page(fit_filename, "Fit")
                add_page(conf_filename, "Confidence")
                add_page(cum_filename, "Cumulative")
                add_page(table_filename, "Signal Table")
            
            print(f"Saved {pdf_filename}")
            
        except Exception as e:
            print(f"Failed to process {ticker}: {e}")
            import traceback
            traceback.print_exc()

        # Cleanup old runs for this ticker
        cleanup_ticker_dir(ticker_dir, KEEP_HISTORY_DAYS)

if __name__ == '__main__':
    run_analysis()
