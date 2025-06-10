import boto3
import os
from typing import List, Dict
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 Configuration
S3_CONFIG = {
    "aws_access_key_id": os.environ.get("S3_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.environ.get("S3_SECRET_ACCESS_KEY"),
    "endpoint_url": os.environ.get("S3_ENDPOINT_URL"),
    "region_name": os.environ.get("S3_REGION"),
}


def get_s3_client():
    """Get a configured S3 client with custom credentials."""
    return boto3.client("s3", **S3_CONFIG)


def normalize_path(path: str) -> str:
    """Normalize a path by removing double slashes and ensuring proper format."""
    # Remove double slashes
    while "//" in path:
        path = path.replace("//", "/")
    # Remove trailing slash
    if path.endswith("/"):
        path = path[:-1]
    return path


def parse_s3_path(s3_path: str) -> tuple[str, str]:
    """Parse an S3 path into bucket and prefix."""
    if not s3_path.startswith("s3://"):
        raise ValueError("S3 path must start with 's3://'")

    # Remove 's3://' and split into bucket and prefix
    path_without_protocol = s3_path[5:]
    bucket = path_without_protocol.split("/")[0]
    prefix = "/".join(path_without_protocol.split("/")[1:])

    # Normalize the prefix
    prefix = normalize_path(prefix)

    return bucket, prefix


def make_s3_path(bucket: str, key: str) -> str:
    """Construct a full S3 path from bucket and key."""
    # Normalize the key
    key = normalize_path(key)
    return f"s3://{bucket}/{key}"


def list_s3_directories(s3_path: str) -> List[str]:
    """List all directories (common prefixes) in an S3 path."""
    s3_client = get_s3_client()
    bucket, prefix = parse_s3_path(s3_path)

    # Ensure prefix ends with '/' if it's not empty
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=prefix, Delimiter="/"
        )

        # Extract common prefixes (directories)
        directories = []
        if "CommonPrefixes" in response:
            for prefix_obj in response["CommonPrefixes"]:
                dir_name = prefix_obj["Prefix"].split("/")[-2]
                directories.append(dir_name)

        return directories
    except Exception as e:
        logger.error(f"Error listing S3 directories: {str(e)}")
        raise


def read_s3_file(s3_path: str) -> str:
    """Read a file from S3 and return its contents as a string."""
    s3_client = get_s3_client()
    bucket, key = parse_s3_path(s3_path)

    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error(f"Error reading S3 file: {str(e)}")
        raise


def read_s3_json(s3_path: str) -> dict:
    """Read a JSON file from S3 and return its contents as a dictionary."""
    content = read_s3_file(s3_path)
    return json.loads(content)


def find_backtest_files_s3(s3_path: str) -> Dict[str, List[str]]:
    """Find and categorize backtest-related files in the given S3 path."""
    s3_client = get_s3_client()
    bucket, prefix = parse_s3_path(s3_path)

    # Ensure prefix ends with '/' if it's not empty
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    # List all objects in the prefix
    paginator = s3_client.get_paginator("list_objects_v2")
    all_files = []

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    # Store full S3 paths
                    full_path = make_s3_path(bucket, obj["Key"])
                    all_files.append(full_path)

        # Categorize files
        main_json = [
            f
            for f in all_files
            if f.endswith(".json")
            and not (
                f.endswith("-summary.json")
                or f.endswith("-order-events.json")
                or os.path.basename(f).startswith("data-monitor-report")
            )
        ]

        summary_json = [f for f in all_files if f.endswith("-summary.json")]
        order_events_json = [f for f in all_files if f.endswith("-order-events.json")]
        monitor_report_json = [
            f
            for f in all_files
            if os.path.basename(f).startswith("data-monitor-report")
        ]

        log_txt = [f for f in all_files if f.endswith("-log.txt")]
        failed_data_requests_txt = [
            f
            for f in all_files
            if os.path.basename(f).startswith("failed-data-requests")
        ]
        succeeded_data_requests_txt = [
            f
            for f in all_files
            if os.path.basename(f).startswith("succeeded-data-requests")
        ]

        result = {
            "main": main_json,
            "summary": summary_json,
            "order_events": order_events_json,
            "monitor_report": monitor_report_json,
            "log": log_txt,
            "failed_data_requests": failed_data_requests_txt,
            "succeeded_data_requests": succeeded_data_requests_txt,
        }

        return result
    except Exception as e:
        logger.error(f"Error finding backtest files: {str(e)}")
        raise


def parse_log_file_s3(s3_path: str, n_lines: int) -> List[Dict[str, str]]:
    """Parse up to n_lines from a log file in S3, grouping consecutive identical events."""
    content = read_s3_file(s3_path)
    lines = content.splitlines()[:n_lines]

    entries = []
    last_event = None
    last_start = None
    last_end = None

    for line in lines:
        import re

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
