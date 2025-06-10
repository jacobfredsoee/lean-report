import os
import glob
import re


def find_backtest_files(folder):
    """
    Find and categorize backtest-related files in the given folder.
    Returns a dictionary with lists of main, summary, order-events, monitor-report, and all JSON files.
    """
    # Find all JSON files
    all_json = glob.glob(os.path.join(folder, "*.json"))
    # Filter out summary, order-events, and monitor-report
    main_json = [
        f
        for f in all_json
        if not (
            f.endswith("-summary.json")
            or f.endswith("-order-events.json")
            or os.path.basename(f).startswith("data-monitor-report")
        )
    ]
    summary_json = [f for f in all_json if f.endswith("-summary.json")]
    order_events_json = [f for f in all_json if f.endswith("-order-events.json")]
    monitor_report_json = [
        f for f in all_json if os.path.basename(f).startswith("data-monitor-report")
    ]

    # Find all CSV files
    all_txt = glob.glob(os.path.join(folder, "*.txt"))
    log_txt = [f for f in all_txt if f.endswith("-log.txt")]
    failed_data_requests_txt = [
        f for f in all_txt if os.path.basename(f).startswith("failed-data-requests")
    ]
    succeeded_data_requests_txt = [
        f for f in all_txt if os.path.basename(f).startswith("succeeded-data-requests")
    ]

    return {
        "main": main_json,
        "summary": summary_json,
        "order_events": order_events_json,
        "monitor_report": monitor_report_json,
        "log": log_txt,
        "failed_data_requests": failed_data_requests_txt,
        "succeeded_data_requests": succeeded_data_requests_txt,
    }


def parse_log_file(filepath, n_lines):
    """
    Parse up to n_lines from a log file, grouping consecutive identical events.
    Returns a list of dicts with 'datetime' and 'event'.
    """
    entries = []
    with open(filepath, "r") as f:
        lines = [line.rstrip() for line in f.readlines()[:n_lines]]
    last_event = None
    last_start = None
    last_end = None
    for line in lines:
        m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(.*)$", line)
        if m:
            dt, event = m.group(1), m.group(2)
        else:
            dt, event = "", line
        if event == last_event:
            last_end = dt or last_end
        else:
            if last_event is not None:
                if last_start and last_end and last_start != last_end:
                    dt_range = f"{last_start} ... {last_end}"
                else:
                    dt_range = last_start or ""
                entries.append({"datetime": dt_range, "event": last_event})
            last_event = event
            last_start = dt
            last_end = dt
    # Add the last group
    if last_event is not None:
        if last_start and last_end and last_start != last_end:
            dt_range = f"{last_start} ... {last_end}"
        else:
            dt_range = last_start or ""
        entries.append({"datetime": dt_range, "event": last_event})
    return entries
