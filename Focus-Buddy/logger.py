import csv
from datetime import datetime
from pathlib import Path


# Store elderly environment logs in the same directory as this script.
LOG_FILE = Path(__file__).resolve().parent / "elderly_health_logs.csv"

# Current CSV schema for the elder-care environment monitoring system.
CSV_HEADERS = ["Timestamp", "Room_Temp", "Room_Humi", "Alert_Type"]


def log_environment_event(room_temp, room_humi, alert_type, timestamp=None) -> None:
    """
    Append one environment monitoring record to elderly_health_logs.csv.

    Parameters:
        room_temp: Current room temperature.
        room_humi: Current room humidity percentage.
        alert_type: AI evaluation label, for example "[HOT]" or "[NORMAL]".
        timestamp: Optional timestamp string. If omitted, current local time is used.
    """
    log_time = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = LOG_FILE.exists()

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(CSV_HEADERS)

        writer.writerow([log_time, room_temp, room_humi, alert_type])


def log_sensor_alert(timestamp, room_temp, room_humi, alert_type) -> None:
    """
    Compatibility wrapper for the sensor monitor.

    This keeps the name used by sensor_monitor.py while writing to the new
    elderly_health_logs.csv schema.
    """
    log_environment_event(
        room_temp=room_temp,
        room_humi=room_humi,
        alert_type=alert_type,
        timestamp=timestamp,
    )


def get_recent_logs(n=10) -> list[dict]:
    """
    Read the most recent environment logs for the Streamlit dashboard.

    Parameters:
        n: Number of latest rows to return. Defaults to 10.

    Returns:
        A list of dictionaries ordered from newest to oldest. If the file does
        not exist, is empty, or cannot be read, an empty list is returned.
    """
    try:
        limit = int(n)
        if limit <= 0:
            return []

        if not LOG_FILE.exists():
            return []

        with open(LOG_FILE, mode="r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                return []

            required_fields = set(CSV_HEADERS)
            if not required_fields.issubset(set(reader.fieldnames)):
                return []

            rows = list(reader)

        return rows[-limit:][::-1]

    except (FileNotFoundError, PermissionError, OSError, csv.Error, ValueError, TypeError):
        return []


if __name__ == "__main__":
    # Local smoke test: print the latest 10 records without modifying the file.
    print(get_recent_logs())
