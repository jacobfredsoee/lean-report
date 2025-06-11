import streamlit as st
import os
import logging
from s3_utils import (
    find_backtest_files_s3,
    list_s3_directories,
    parse_log_file_s3,
    parse_s3_path,
    read_s3_file,
    read_s3_json,
)
from plot_utils import (
    data_file_status_box,
    extract_ohlc_from_json,
    plot_candlestick,
    generate_multi_series_chart_plot,
    summary_stats_box,
    algo_basic_info_box,
    plot_profit_loss_bar,
)
from utils import find_backtest_files, parse_log_file
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Utility functions (move these to the top to avoid linter errors)
def is_s3_path(path: str) -> bool:
    return path.startswith("s3://")


def get_files(path: str) -> dict:
    if is_s3_path(path):
        try:
            files = find_backtest_files_s3(path)
            return files
        except Exception as e:
            st.sidebar.error(f"Error finding S3 files: {str(e)}")
            return {}
    else:
        return find_backtest_files(path)


def read_json_file(file_path: str) -> dict:
    if is_s3_path(file_path):
        try:
            return read_s3_json(file_path)
        except Exception as e:
            st.error(f"Error reading JSON from S3: {str(e)}")
            return {}
    else:
        with open(file_path, "r") as f:
            return json.load(f)


def read_log_file(file_path: str, n_lines: int) -> list:
    if is_s3_path(file_path):
        try:
            return parse_log_file_s3(file_path, n_lines)
        except Exception as e:
            st.error(f"Error reading log from S3: {str(e)}")
            return []
    else:
        return parse_log_file(file_path, n_lines)


def count_log_lines(file_path: str) -> int:
    if is_s3_path(file_path):
        try:
            content = read_s3_file(file_path)
            return len(content.splitlines())
        except Exception as e:
            st.error(f"Error counting log lines from S3: {str(e)}")
            return 0
    else:
        with open(file_path, "r") as f:
            return sum(1 for _ in f)


def get_subdirectories(path: str) -> list:
    if is_s3_path(path):
        try:
            return list_s3_directories(path)
        except Exception as e:
            st.sidebar.error(f"Error listing S3 directories: {str(e)}")
            return []
    else:
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]


# Set page config
st.set_page_config(page_title="Backtest Viewer", layout="wide")

# Initialize session state for browsing and reporting
if "browse_path" not in st.session_state:
    st.session_state["browse_path"] = ""
if "report_path" not in st.session_state:
    st.session_state["report_path"] = ""

# Sidebar for folder selection
st.sidebar.title("Backtest Selection")
# default_path = "s3://algo-trading/output/optimizations"  # S3 bucket path
default_path = "/Users/jacobfredsoe/Downloads/optimizations"  # local path
browse_path = st.sidebar.text_input(
    "Enter backtest output folder path:",
    value=st.session_state["browse_path"] or default_path,
    help="Enter the full path to your backtest output folder (local path or s3://bucket/path)",
)
st.session_state["browse_path"] = browse_path

# List all immediate subfolders of browse_path
if browse_path and (is_s3_path(browse_path) or os.path.exists(browse_path)):
    subdirs = sorted(get_subdirectories(browse_path))
    if subdirs:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Folders in this path")
        for subdir in subdirs:
            if is_s3_path(browse_path):
                bucket, prefix = parse_s3_path(browse_path)
                if prefix:
                    new_s3_path = f"s3://{bucket}/{prefix}/{subdir}"
                else:
                    new_s3_path = f"s3://{bucket}/{subdir}"
                full_path = new_s3_path
            else:
                full_path = os.path.abspath(os.path.join(browse_path, subdir))
            if st.sidebar.button(
                subdir, key=f"navbtn_{subdir}", use_container_width=True
            ):
                st.session_state["report_path"] = full_path
                st.rerun()
    else:
        st.sidebar.info("No subdirectories found in the selected folder.")
else:
    st.sidebar.warning(
        "Please enter a valid folder path. You can use ~/ to start from your home directory or s3://bucket/path for S3."
    )

# Determine which path to show the report for
report_path = st.session_state.get("report_path") or browse_path
subdirs = get_subdirectories(report_path)
if (
    report_path
    and (is_s3_path(report_path) or os.path.exists(report_path))
    and len(subdirs) == 0
):
    files = get_files(report_path)
    has_json = bool(files["main"] or files.get("summary"))
    if has_json:
        st.title("Backtest result")
        main = files["main"]
        summary = files.get("summary", [])
        json_data = None
        summary_data = None
        if main:
            json_data = read_json_file(main[0])
        if summary:
            summary_data = read_json_file(summary[0])

        if json_data:
            # Algorithm basic information
            algo_basic_info_box(summary_data)

            data_file_status_box(files)

            # OHLC Candlestick
            ohlc_daily = extract_ohlc_from_json(json_data)
            st.plotly_chart(plot_candlestick(ohlc_daily), use_container_width=True)
            # Profit/Loss Bar Plot
            profit_loss_fig = plot_profit_loss_bar(json_data)
            if profit_loss_fig:
                st.plotly_chart(profit_loss_fig, use_container_width=True)
            # Summary box
            summary_stats_box(summary_data)

            # All requested plots (unified as multi-series, even if only one series)
            plot_specs = [
                (
                    "Drawdown",
                    [("Equity Drawdown", "Drawdown", "dodgerblue")],
                    "Drawdown",
                ),
                (
                    "KAUF",
                    [("PRICE", "Kaufman Adaptive Moving Average (KAMA)", "purple")],
                    "Kaufman Adaptive Moving Average (KAMA)",
                ),
                (
                    "Portfolio Turnover",
                    [("Portfolio Turnover", "Portfolio Turnover", "brown")],
                    "Portfolio Turnover",
                ),
                (
                    "Capacity",
                    [("Strategy Capacity", "Strategy Capacity", "teal")],
                    "Strategy Capacity",
                ),
                (
                    "ATR",
                    [("ATR", "Average True Range (ATR)", "red")],
                    "Average True Range (ATR)",
                ),
                (
                    "STR",
                    [
                        ("TrailingLower", "Strategy Trailing Lower", "dodgerblue"),
                        ("Current", "Strategy Current", "orange"),
                    ],
                    "Strategy Trailing Lower & Current",
                ),
                ("Benchmark", [("Benchmark", "Benchmark", "green")], "Benchmark"),
                (
                    "Exposure",
                    [
                        ("Equity - Long Ratio", "Equity - Long Ratio", "blue"),
                        ("Equity - Short Ratio", "Equity - Short Ratio", "orange"),
                    ],
                    "Equity - Long Ratio & Short Ratio",
                ),
            ]

            # Display in two columns
            cols = st.columns(2)
            for idx, (chart, series_specs, title) in enumerate(plot_specs):
                fig = generate_multi_series_chart_plot(
                    json_data, chart, series_specs, title
                )
                if fig:
                    with cols[idx % 2]:
                        st.plotly_chart(fig, use_container_width=True)

            # Log file viewer
            log_files = files.get("log", [])
            if log_files:
                log_file = log_files[0]
                if "log_lines_shown" not in st.session_state:
                    st.session_state["log_lines_shown"] = 200
                st.markdown("---")
                st.subheader("Log File Preview")
                log_entries = read_log_file(
                    log_file, st.session_state["log_lines_shown"]
                )
                import pandas as pd

                df = pd.DataFrame(log_entries)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Count total lines for button logic
                total_lines = count_log_lines(log_file)
                shown = st.session_state["log_lines_shown"]
                if shown < total_lines:
                    if st.button("Load 200 more log lines"):
                        st.session_state["log_lines_shown"] += 200
                else:
                    st.info("End of log file reached.")
            else:
                st.info("No log file found in this backtest folder.")
    else:
        st.warning("No backtest report (JSON) found in this folder.")
else:
    summary_files = []
    for dir in subdirs:
        if is_s3_path(report_path):
            bucket, prefix = parse_s3_path(report_path)
            if prefix:
                s3_path = f"s3://{bucket}/{prefix}/{dir}"
            else:
                s3_path = f"s3://{bucket}/{dir}"
            try:
                files = find_backtest_files_s3(s3_path)
                if files.get("summary"):
                    summary_files.extend(files["summary"])
            except Exception as e:
                st.error(f"Error finding summary files in S3: {str(e)}")
        else:
            dir_path = os.path.join(report_path, dir)
            for file in os.listdir(dir_path):
                if file.endswith("-summary.json"):
                    summary_files.append(os.path.join(dir_path, file))

    st.header("Optimization results")

    # Sort summary files by name
    summary_files = sorted(summary_files)

    # Extract info for table
    table_rows = []
    all_equity_curves = []

    for summary_file in summary_files:
        try:
            data = read_json_file(summary_file)
            folder = os.path.basename(os.path.dirname(summary_file))
            # Portfolio statistics (corrected path)
            stats = data.get("totalPerformance", {}).get("portfolioStatistics", {})
            end_equity = stats.get("endEquity", None)
            total_net_profit = stats.get("totalNetProfit", None)
            drawdown = stats.get("drawdown", None)
            sharpe_ratio = stats.get("sharpeRatio", None)
            # Parameters
            params = data.get("algorithmConfiguration", {}).get("parameters", {})
            filtered_params = {k: v for k, v in params.items() if v != ""}
            # Add row
            table_rows.append(
                {
                    "backtestId": folder,
                    "endEquity": end_equity,
                    "totalNetProfit": total_net_profit,
                    "drawdown": drawdown,
                    "sharpeRatio": sharpe_ratio,
                    "parameters": json.dumps(filtered_params, indent=2),
                }
            )
            # Equity curve for plotting
            if data and "charts" in data and "Strategy Equity" in data["charts"]:
                equity_data = data["charts"]["Strategy Equity"]["series"]["Equity"][
                    "values"
                ]
                df = pd.DataFrame(
                    np.array(equity_data),
                    columns=pd.Index(["timestamp", "open", "high", "low", "close"]),
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                all_equity_curves.append(df)
        except Exception as e:
            st.error(f"Error reading file {summary_file}: {str(e)}")

    # Plot equity curves (as before)
    if all_equity_curves:
        fig = go.Figure()
        for df in all_equity_curves:
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["close"],
                    mode="lines",
                    line=dict(color="grey", width=1),
                    opacity=0.1,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        all_timestamps = sorted(
            set([ts for df in all_equity_curves for ts in df["timestamp"]])
        )
        mean_values = []
        for ts in all_timestamps:
            values = [
                df[df["timestamp"] == ts]["close"].values[0]
                for df in all_equity_curves
                if ts in df["timestamp"].values
            ]
            if values:
                mean_values.append(sum(values) / len(values))
        fig.add_trace(
            go.Scatter(
                x=all_timestamps,
                y=mean_values,
                mode="lines",
                line=dict(color="black", width=2),
                name="Mean Equity",
                hoverinfo="x+y+name",
            )
        )
        fig.update_layout(
            title="All Optimization Equity Curves",
            xaxis_title="Date",
            yaxis_title="Equity",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No equity curves found in the summary files.")

    # Show table
    if table_rows:
        df_table = pd.DataFrame(table_rows)
        # Convert to percent and format
        df_table["totalNetProfit"] = pd.to_numeric(
            df_table["totalNetProfit"], errors="coerce"
        )
        df_table["drawdown"] = pd.to_numeric(df_table["drawdown"], errors="coerce")
        df_table["totalNetProfit"] = df_table["totalNetProfit"].apply(
            lambda x: f"{x*100:.2f}%" if pd.notnull(x) else ""
        )
        df_table["drawdown"] = df_table["drawdown"].apply(
            lambda x: f"{x*100:.2f}%" if pd.notnull(x) else ""
        )

        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "backtestId",
                "endEquity",
                "totalNetProfit",
                "drawdown",
                "sharpeRatio",
                "parameters",
            ],
            column_config={
                "parameters": st.column_config.TextColumn("parameters", width="large"),
            },
        )
    else:
        st.warning("No summary files found for table.")
