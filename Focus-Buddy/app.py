from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from logger import get_recent_logs


BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_FILE = BASE_DIR / "sensor_monitor_heartbeat.txt"
HEARTBEAT_HEALTHY_SECONDS = 30
HEARTBEAT_DEGRADED_SECONDS = 180

ALERT_LABELS = {
    "[CRITICAL_HOT]": "critical high temperature alert",
    "[HOT]": "high temperature warning",
    "[HOT_WARNING]": "high temperature warning",
    "[COLD]": "low temperature warning",
    "[COLD_WARNING]": "low temperature warning",
    "[HUMID]": "high humidity warning",
    "[HUMID_WARNING]": "high humidity warning",
    "[NORMAL]": "normal status",
}


def parse_float(value):
    """Safely parse a numeric value for dashboard display."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_heartbeat() -> dict | None:
    """
    Read the latest backend heartbeat written by sensor_monitor.py.

    The expected format is:
        Timestamp,Temperature,Humidity
    """
    try:
        if not HEARTBEAT_FILE.exists():
            return None

        raw_text = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
        timestamp_text, temp_text, humi_text = raw_text.split(",", maxsplit=2)

        return {
            "Timestamp": timestamp_text,
            "Room_Temp": parse_float(temp_text),
            "Room_Humi": parse_float(humi_text),
            "Age_Seconds": datetime.now().timestamp() - HEARTBEAT_FILE.stat().st_mtime,
        }
    except (OSError, ValueError):
        return None


def get_backend_status() -> tuple[str, str, str]:
    """
    Return a dashboard-friendly status label, color, and detail text.

    This checks whether sensor_monitor.py is actively writing heartbeat updates.
    """
    heartbeat = read_heartbeat()

    if heartbeat is None:
        return (
            "OFFLINE",
            "#b91c1c",
            "No backend heartbeat found. Start sensor_monitor.py to poll hardware.",
        )

    age_seconds = heartbeat["Age_Seconds"]
    if age_seconds <= HEARTBEAT_HEALTHY_SECONDS:
        return (
            "ONLINE",
            "#047857",
            "sensor_monitor.py is actively polling hardware.",
        )

    if age_seconds <= HEARTBEAT_DEGRADED_SECONDS:
        return (
            "DEGRADED",
            "#b45309",
            f"Last heartbeat was {int(age_seconds)} seconds ago.",
        )

    return (
        "OFFLINE",
        "#b91c1c",
        f"Backend heartbeat is stale. Last update was {int(age_seconds)} seconds ago.",
    )


def get_latest_environment(logs: list[dict]) -> dict:
    """
    Choose the freshest environment values for the top metrics.

    Heartbeat data is preferred because it represents live polling. If the
    heartbeat is unavailable, the dashboard falls back to the latest CSV row.
    """
    heartbeat = read_heartbeat()
    if heartbeat and heartbeat.get("Room_Temp") is not None and heartbeat.get("Room_Humi") is not None:
        return heartbeat

    if logs:
        latest = logs[0]
        return {
            "Timestamp": latest.get("Timestamp", ""),
            "Room_Temp": parse_float(latest.get("Room_Temp")),
            "Room_Humi": parse_float(latest.get("Room_Humi")),
        }

    return {"Timestamp": "", "Room_Temp": None, "Room_Humi": None}


def format_metric(value, unit: str) -> str:
    """Format a metric value with a unit, or show a placeholder."""
    if value is None:
        return "--"
    return f"{value:.1f}{unit}"


def build_temperature_chart(logs: list[dict]) -> pd.DataFrame:
    """Build a chronological DataFrame for the temperature line chart."""
    chart_rows = []

    for row in reversed(logs):
        temp = parse_float(row.get("Room_Temp"))
        if temp is None:
            continue

        chart_rows.append(
            {
                "Timestamp": row.get("Timestamp", ""),
                "Room_Temp": temp,
            }
        )

    return pd.DataFrame(chart_rows)


def format_alert_message(row: dict) -> str:
    """Format one alert row into an English sentence for the dashboard."""
    timestamp = row.get("Timestamp", "Unknown time")
    alert_type = row.get("Alert_Type", "")
    readable_alert = ALERT_LABELS.get(alert_type, alert_type or "unknown alert")
    return f"{timestamp} triggered a {readable_alert}."


st.set_page_config(
    page_title="Elderly Home Care Dashboard",
    page_icon="🏠",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --warm-bg: #f7f1e8;
        --ink: #27302f;
        --sage: #6f8f72;
        --clay: #b66b45;
        --paper: rgba(255, 252, 247, 0.92);
    }
    .stApp {
        background:
            radial-gradient(circle at 10% 5%, rgba(182, 107, 69, 0.18), transparent 32rem),
            radial-gradient(circle at 90% 15%, rgba(111, 143, 114, 0.18), transparent 28rem),
            var(--warm-bg);
        color: var(--ink);
    }
    .status-card {
        background: var(--paper);
        border: 1px solid rgba(39, 48, 47, 0.12);
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 18px 45px rgba(39, 48, 47, 0.08);
    }
    .status-dot {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 999px;
        margin-right: 8px;
        vertical-align: middle;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin: 1rem 0 0.6rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

logs = get_recent_logs(200)
latest_environment = get_latest_environment(logs)
status_label, status_color, status_detail = get_backend_status()

st.title("Elderly Home Environment Dashboard")
st.caption("Live indoor sensing, alert history, and backend polling status for family monitoring.")

status_html = f"""
<div class="status-card">
    <span class="status-dot" style="background: {status_color};"></span>
    <strong>System Status: {status_label}</strong>
    <div style="margin-top: 6px; color: #4b5563;">{status_detail}</div>
</div>
"""
st.markdown(status_html, unsafe_allow_html=True)

metric_col1, metric_col2 = st.columns(2)
metric_col1.metric(
    label="Live Indoor Temperature",
    value=format_metric(latest_environment["Room_Temp"], "℃"),
)
metric_col2.metric(
    label="Live Indoor Humidity",
    value=format_metric(latest_environment["Room_Humi"], "%"),
)

if latest_environment.get("Timestamp"):
    st.caption(f"Latest reading time: {latest_environment['Timestamp']}")

st.markdown('<div class="section-title">Temperature Trend</div>', unsafe_allow_html=True)
temperature_chart = build_temperature_chart(logs)

if temperature_chart.empty:
    st.info("No temperature records are available yet.")
else:
    st.line_chart(
        temperature_chart,
        x="Timestamp",
        y="Room_Temp",
        height=320,
    )

with st.sidebar:
    st.header("Recent Alerts")

    alert_logs = [
        row
        for row in logs
        if row.get("Alert_Type") and row.get("Alert_Type") != "[NORMAL]"
    ][:10]

    if not alert_logs:
        st.success("No recent alerts.")
    else:
        for alert in alert_logs:
            st.warning(format_alert_message(alert))

st.markdown('<div class="section-title">Recent Environment Records</div>', unsafe_allow_html=True)
recent_logs = get_recent_logs(10)

if not recent_logs:
    st.info("No environment logs are available yet.")
else:
    st.dataframe(recent_logs, use_container_width=True, hide_index=True)
