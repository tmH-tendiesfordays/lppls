
import matplotlib
matplotlib.use('Agg') # Save plots to files
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
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
TICKERS = ["NFLX"]   # List of tickers to analyze - ["^NDX", "SPY", "^GSPC", "QQQ", "BTC-USD"]
START_DATE = "2007-01-01"
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
            
            # Check if fit succeeded (tc != 0)
            if tc != 0:
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
            else:
                print(f"Global fit failed for {TICKER}, skipping fit plot.")
            


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

            # ==========================================
            # NEW: Cumulative Plot with Table
            # ==========================================
            # ==========================================
            # NEW: Cumulative Plot with Table (Refined)
            # ==========================================
            print(f"Generating cumulative plot for {TICKER}...")
            
            # 1. Get Data & Cluster Signals
            res_df = lppls_model.compute_indicators(res)
            
            # Helper to cluster consecutive dates
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

            table_data = []
            table_data.extend(cluster_signals(res_df, "pos_conf", "Top"))
            table_data.extend(cluster_signals(res_df, "neg_conf", "Bottom"))
            
            # Sort by Start Date Descending (Recent first)
            table_data.sort(key=lambda x: x[0][:10], reverse=True)
            
            # ==========================================
            # 2. Cumulative Plot (Chart Only)
            # ==========================================
            print(f"Generating cumulative chart for {TICKER}...")
            
            # Setup Figure
            fig, ax1 = plt.subplots(figsize=(16, 10))
            
            # Plotting
            ordinals = res_df["time"].astype("int32")
            dates_for_plot = [pd.Timestamp.fromordinal(d) for d in ordinals]
            price_series = np.exp(res_df["price"])
            
            ax1.plot(dates_for_plot, price_series, color='blue', label='Price', linewidth=1.5)
            ax1.set_ylabel('Price ($)', color='blue', fontsize=12)
            ax1.tick_params(axis='y', labelcolor='blue')
            ax1.grid(True, which='major', linestyle='--', alpha=0.7)
            ax1.grid(True, which='minor', linestyle=':', alpha=0.3) 

            # Create Twin Axis for Confidence
            ax2 = ax1.twinx()
            ax2.bar(dates_for_plot, res_df["pos_conf"], color='red', alpha=0.3, width=1.0, label='Confidence (Top)')
            ax2.bar(dates_for_plot, res_df["neg_conf"], color='green', alpha=0.3, width=1.0, label='Confidence (Bottom)')
            
            ax2.set_ylabel('Confidence Indicator', color='black', fontsize=12)
            ax2.set_ylim(0, 1.0)
            
            # Legends
            lines_1, labels_1 = ax1.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', fontsize=10)

            plt.title(f"{TICKER} Price Analysis & Confidence Signals ({START_DATE} to {END_DATE})", fontsize=16)

            # X-Axis formatting
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator()))
            ax1.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=1))
            
            # Save Chart
            cum_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}-{run_timestamp}_cumulative.png')
            plt.savefig(cum_filename, bbox_inches='tight')
            print(f"Saved cumulative chart to {cum_filename}")
            plt.close(fig)

            # ==========================================
            # 3. Data Table (Separate Logic)
            # ==========================================
            table_filename = None
            if table_data:
                print(f"Generating signal table for {TICKER}...")
                
                # Calculate lighter height logic
                # Reduce row height estimate
                num_rows = len(table_data) + 1 # +1 for header
                # Tighter packing: 0.25 inch per row roughly
                row_height_inch = 0.25
                header_height_inch = 0.5
                table_fig_height = header_height_inch + (num_rows * row_height_inch)
                
                # Cap minimum height
                table_fig_height = max(table_fig_height, 2.0)

                fig_table = plt.figure(figsize=(10, table_fig_height))
                ax_table = plt.gca()
                ax_table.axis('off')

                # Headers
                col_labels = ["Date Range", "Max Confidence", "Signal Type"]
                
                # Create the table
                the_table = ax_table.table(cellText=table_data,
                                           colLabels=col_labels,
                                           loc='center',
                                           cellLoc='center')
                
                the_table.auto_set_font_size(False)
                the_table.set_fontsize(10) # Slightly smaller font
                the_table.scale(1, 1.2) # Reduced vertical scale from 1.5 to 1.2
                
                # Style headers
                for (row, col), cell in the_table.get_celld().items():
                    if row == 0:
                        cell.set_text_props(weight='bold')
                        cell.set_facecolor('#f0f0f0')
                
                # Save Table
                table_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}-{run_timestamp}_cumulative_table.png')
                plt.savefig(table_filename, bbox_inches='tight', pad_inches=0.2)
                print(f"Saved signal table to {table_filename}")
                plt.close(fig_table)
            else:
                print(f"No signals found for {TICKER}, skipping table generation.")


            print(f"Projected Critical Time (tc): {tc}")
            tc_str = "N/A"
            try:
                dt_tc = datetime.fromordinal(int(tc))
                tc_str = dt_tc.strftime('%Y-%m-%d')
                print(f"Predicted turning point date: {tc_str}")
            except:
                print("Could not convert tc to date (out of range)")

            # ==========================================
            # 4. Generate Markdown Summary Report
            # ==========================================
            print(f"Generating summary report for {TICKER}...")
            report_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}_{run_timestamp}_report.md')
            
            # Stats & Logic for Analyst Commentary
            num_top = sum(1 for row in table_data if row[2] == "Top")
            num_bot = sum(1 for row in table_data if row[2] == "Bottom")
            
            # --- Dynamic Commentary Generators ---
            
            # 1. Critical Time Context
            tc_commentary = ""
            if tc_str != "N/A":
                try:
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


            summary_text = (
                f"### Executive Summary\n"
                f"The analysis for **{TICKER}** ({START_DATE} to {END_DATE}) has detected a total of **{len(table_data)}** significant LPPLS signals.\n\n"
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

            # Markdown Content
            md_content = f"""# LPPLS Analyst Report: {TICKER}
**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Range:** {START_DATE} to {END_DATE}

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

![Fit Plot]({os.path.basename(fit_filename) if 'fit_filename' in locals() and os.path.exists(fit_filename) else 'Fit plot skipped'})

---

## 2. Confidence Indicators (Multi-Scale)

### What is this?
Calculating $t_c$ on a single window can be noisy. This section performs **nested fits** across varying time windows (e.g., looking back 30 days vs 120 days).
- **Red Spikes**: Fraction of fits predicting a Top.
- **Green Spikes**: Fraction of fits predicting a Bottom.

### Analysis
High values (close to 1.0) indicate a **consensus** across different timeframes that a specific date was a critical point. Frequent clustering of these spikes suggests a high probability of a turning point.

{conf_commentary}

![Confidence Plot]({os.path.basename(conf_filename)})

---

## 3. Cumulative Price & Signal Analysis

### What is this?
This chart overlays the Confidence Signals directly onto the Price History. It is the primary tool for timing.
- **Red Bars**: "Top" confidence. Look for these aligning with new price highs.
- **Green Bars**: "Bottom" confidence. Look for these aligning with price lows (capitulation).

### Analysis
Observe the clusters. A solitary spike might be noise, but a **dense cluster** of bars often precedes a trend reversal.

{recent_commentary}

![Cumulative Chart]({os.path.basename(cum_filename)})

---

## 4. Signal Data Table

### What is this?
A detailed log of the signal clusters shown above, sorted by **Recency**.
- **Date Range**: The duration where the signal persisted.
- **Max Confidence**: The peak intensity (0.0 to 1.0).

![Signal Table]({os.path.basename(table_filename) if table_filename else 'No signals detected'})

---

## 5. Analyst Conclusion
{summary_text}
"""
            with open(report_filename, "w") as f:
                f.write(md_content)
            
            print(f"Saved summary report to {report_filename}")

            # ==========================================
            # 5. Generate PDF Report
            # ==========================================
            print(f"Generating PDF report for {TICKER}...")
            pdf_filename = os.path.join(OUTPUT_DIR, f'{safe_ticker}_{run_timestamp}_report.pdf')
            
            with PdfPages(pdf_filename) as pdf:
                # Page 1: Summary Text
                fig_text = plt.figure(figsize=(10, 8))
                ax_text = fig_text.add_subplot(111)
                ax_text.axis('off')
                
                txt_content = (
                    f"LPPLS Analyst Report: {TICKER}\n"
                    f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Data Range: {START_DATE} to {END_DATE}\n\n"
                    f"Projected Critical Time (tc): {tc_str}\n\n"
                    f"{summary_text.replace('### Executive Summary', 'EXECUTIVE SUMMARY').replace('**', '')}"
                )
                
                # Simple text wrapping for the summary
                import textwrap
                wrapper = textwrap.TextWrapper(width=80) 
                # We won't wrap specific hardcoded lines, just the summary_text part if needed, 
                # but let's just dump it in for now. Matplotlib text doesn't auto-wrap nicely without keys.
                # Let's align top-left.
                
                ax_text.text(0.05, 0.95, txt_content, transform=ax_text.transAxes, ha='left', va='top', fontsize=12, family='monospace')
                pdf.savefig(fig_text)
                plt.close(fig_text)
                
                # Helper to add image page
                def add_image_page(img_path, title):
                    if img_path and os.path.exists(img_path):
                        try:
                            img = mpimg.imread(img_path)
                            # Get image aspect ratio to determine figure size or just fit it
                            h, w, _ = img.shape
                            aspect = w / h
                            
                            # Create figure with reasonable size
                            fig_img = plt.figure(figsize=(11, 11/aspect)) 
                            ax_img = fig_img.add_subplot(111)
                            ax_img.imshow(img)
                            ax_img.axis('off')
                            ax_img.set_title(title)
                            pdf.savefig(fig_img, bbox_inches='tight')
                            plt.close(fig_img)
                        except Exception as e:
                            print(f"Error adding {title} to PDF: {e}")

                # Add Pages
                add_image_page(fit_filename if 'fit_filename' in locals() else None, f"Model Fit: {TICKER}")
                add_image_page(conf_filename, f"Confidence Indicators: {TICKER}")
                add_image_page(cum_filename, f"Cumulative Analysis: {TICKER}")
                add_image_page(table_filename, f"Signal Clusters: {TICKER}")
                
            print(f"Saved PDF report to {pdf_filename}")

        except Exception as e:
            print(f"Failed to process {TICKER}: {e}")
            import traceback
            traceback.print_exc()
