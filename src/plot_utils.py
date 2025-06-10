import pandas as pd
import plotly.graph_objs as go
import numpy as np
import streamlit as st
import os


def extract_ohlc_from_json(json_data):
    # Extract OHLC data from the main JSON
    values = json_data["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    if not values or not isinstance(values[0], (list, tuple)):
        values = np.array(values).reshape(-1, 5)
    ohlc = pd.DataFrame(
        np.array(values),
        columns=pd.Index(["Timestamp", "Open", "High", "Low", "Close"]),
    )
    ohlc["Open"] = pd.to_numeric(ohlc["Open"])
    ohlc["High"] = pd.to_numeric(ohlc["High"])
    ohlc["Low"] = pd.to_numeric(ohlc["Low"])
    ohlc["Close"] = pd.to_numeric(ohlc["Close"])
    ohlc["Datetime"] = pd.to_datetime(ohlc["Timestamp"], unit="s", utc=True)
    return ohlc


def plot_candlestick(ohlc_daily):
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=ohlc_daily["Datetime"],
                open=ohlc_daily["Open"],
                high=ohlc_daily["High"],
                low=ohlc_daily["Low"],
                close=ohlc_daily["Close"],
                increasing_line_color="blue",
                decreasing_line_color="orange",
            )
        ]
    )
    fig.update_layout(
        title="Strategy Equity Candlestick",
        xaxis_title="Datetime",
        yaxis_title="Equity",
        xaxis_rangeslider_visible=False,
        height=600,
    )
    return fig


def generate_multi_series_chart_plot(json_data, chart_name, series_specs, title):
    """
    Plot multiple series from the same chart on one plot.
    series_specs: list of (series_name, metric_name, color)
    """
    fig = go.Figure()
    unit = ""
    for series_name, metric_name, color in series_specs:
        try:
            values = json_data["charts"][chart_name]["series"][series_name]["values"]
            unit = json_data["charts"][chart_name]["series"][series_name].get(
                "unit", ""
            )
        except KeyError:
            continue
        if not values or not isinstance(values[0], (list, tuple)):
            values = np.array(values).reshape(-1, 2)
        df = pd.DataFrame(np.array(values), columns=pd.Index(["Timestamp", "Y"]))
        df["Y"] = pd.to_numeric(df["Y"])
        df["Datetime"] = pd.to_datetime(df["Timestamp"], unit="s", utc=True)
        fig.add_trace(
            go.Scatter(
                x=df["Datetime"],
                y=df["Y"],
                mode="lines+markers",
                name=metric_name,
                line=dict(color=color),
            )
        )

        fig.update_layout(title=title, xaxis_title="Datetime", yaxis_title=unit)
        return fig


def summary_stats_box(json_data):
    def format_value(val):
        if val is None:
            return "-", None
        sval = str(val).strip()
        color = None
        # Handle percentages
        if sval.endswith("%"):
            try:
                num = float(sval.replace("%", "").replace(",", ""))
                color = "black"
                return f"{num:,.1f}%", color
            except Exception:
                return sval, None
        # Handle dollar values
        if sval.startswith("$") or sval.startswith("-\\$"):
            try:
                num = float(sval.replace("$", "").replace(",", ""))
                sign = "-" if num < 0 else ""
                color = "black"
                return f"{sign}${abs(num):,.1f}", color
            except Exception:
                return sval, None
        # Handle plain numbers
        try:
            num = float(sval.replace(",", ""))
            color = "black"
            if "." in sval or isinstance(val, float):
                return f"{num:,.1f}", color
            else:
                return f"{int(num):,}", color
        except Exception:
            return sval, None

    stats = json_data.get("statistics", {})
    key_stats = {
        "Start Equity": stats.get("Start Equity"),
        "End Equity": stats.get("End Equity"),
        "Net Profit": stats.get("Net Profit"),
        "Compounding Annual Return": stats.get("Compounding Annual Return"),
        "Drawdown": stats.get("Drawdown"),
        "Sharpe Ratio": stats.get("Sharpe Ratio"),
        "Win Rate": stats.get("Win Rate"),
        "Loss Rate": stats.get("Loss Rate"),
        "Profit-Loss Ratio": stats.get("Profit-Loss Ratio"),
        "Total Orders": stats.get("Total Orders"),
        "Portfolio Turnover": stats.get("Portfolio Turnover"),
        "Total Fees": stats.get("Total Fees"),
    }
    with st.container():
        st.markdown("#### Summary Statistics")
        cols = st.columns(4)
        for idx, (k, v) in enumerate(key_stats.items()):
            if v is not None:
                formatted, color = format_value(v)
                if color:
                    cols[idx % 4].markdown(
                        f"<div style='font-size: 1.5em; color: {color}; font-weight: bold'>{formatted}</div><div style='font-size: 1em; color: black'>{k}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    cols[idx % 4].metric(k, formatted)


def algo_basic_info_box(summary_json):
    # Start and end date from summary json
    config = summary_json.get("algorithmConfiguration", {})
    algo_name = config.get("name", "-")
    start_date = config.get("startDate", "-")
    end_date = config.get("endDate", "-")
    parameters = config.get("parameters", {})

    with st.container():
        st.markdown("#### Algorithm Basic Information")
        cols = st.columns(4 if parameters else 3)
        cols[0].markdown(f"**Algorithm name:**<br>{algo_name}", unsafe_allow_html=True)
        cols[1].markdown(f"**Start Date:**<br>{start_date}", unsafe_allow_html=True)
        cols[2].markdown(f"**End Date:**<br>{end_date}", unsafe_allow_html=True)
        if parameters:
            param_str = ", ".join([f"{k}: {v}" for k, v in parameters.items() if v])
            st.markdown(f"**Parameters:** {param_str}")


def data_file_status_box(files_dict):
    # Helper to count types by reading lines in each file
    def count_types(file_list):
        counts = {"quote.zip": 0, "trade.zip": 0, "interest-rate.csv": 0}
        for fpath in file_list:
            try:
                with open(fpath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.endswith("_quote.zip"):
                            counts["quote.zip"] += 1
                        if line.endswith("_trade.zip"):
                            counts["trade.zip"] += 1
                        if line.endswith("interest-rate.csv"):
                            counts["interest-rate.csv"] += 1
            except Exception as e:
                continue
        return counts

    failed = files_dict.get("failed_data_requests", [])
    succeeded = files_dict.get("succeeded_data_requests", [])
    failed_counts = count_types(failed)
    succeeded_counts = count_types(succeeded)
    with st.container():
        st.markdown("#### File Type Counts")
        subcols = st.columns(3)
        for idx, filetype in enumerate(["quote.zip", "trade.zip", "interest-rate.csv"]):
            subcols[idx].markdown(
                f"<b>{filetype}</b><br>Failed: <span style='color:red'>{failed_counts[filetype]}</span><br>Succeeded: <span style='color:green'>{succeeded_counts[filetype]}</span>",
                unsafe_allow_html=True,
            )


def plot_profit_loss_bar(json_data):
    profit_loss = json_data.get("profitLoss", {})
    if not profit_loss:
        return None
    # Convert dict to DataFrame
    df = pd.DataFrame(
        list(profit_loss.items()), columns=pd.Index(["Datetime", "Change"])
    )
    df["Datetime"] = pd.to_datetime(
        df["Datetime"], format="%Y-%m-%dT%H:%M:%SZ", utc=True, errors="coerce"
    )
    df["Change"] = pd.to_numeric(df["Change"], errors="coerce")
    df = df.dropna(subset=["Datetime", "Change"])

    # Get OHLC start date
    ohlc = extract_ohlc_from_json(json_data)
    ohlc_start = ohlc["Datetime"].min()

    # Add a dummy point at the OHLC start if not present
    if ohlc_start not in df["Datetime"].values:
        df = pd.concat(
            [pd.DataFrame([{"Datetime": ohlc_start, "Change": 0}]), df],
            ignore_index=True,
        )
        df = df.sort_values("Datetime")

    fig = go.Figure(
        data=[go.Bar(x=df["Datetime"], y=df["Change"], marker_color="gray")]
    )
    fig.update_layout(
        title="Profit/Loss Per Trade",
        xaxis_title="Datetime",
        yaxis_title="Change",
        height=200,
        margin=dict(l=40, t=40, b=40),
    )
    return fig
