import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from logger import CSV_HEADERS, LOG_FILE


def classify_mock_environment(room_temp: float, room_humi: float) -> str:
    """
    Classify generated mock sensor values using the same label family as the app.

    This is intentionally deterministic so generated data can exercise the
    dashboard without requiring a live sensor or LLM API key.
    """
    if room_temp >= 40:
        return "[CRITICAL_HOT]"
    if room_temp > 26:
        return "[HOT]"
    if room_temp < 22:
        return "[COLD]"
    if room_humi > 60:
        return "[HUMID]"
    return "[NORMAL]"


def generate_mock_csv(filename: str | Path = LOG_FILE, num_records: int = 80) -> None:
    """
    Generate mock elder-care environment logs for local dashboard testing.

    The output file matches logger.py's current schema:
    Timestamp, Room_Temp, Room_Humi, Alert_Type
    """
    output_file = Path(filename)
    base_time = datetime.now()
    mock_data = []

    for index in range(num_records):
        # Spread records across the last 24 hours in chronological order.
        minutes_ago = (num_records - index) * random.randint(8, 20)
        record_time = base_time - timedelta(minutes=minutes_ago)
        timestamp = record_time.strftime("%Y-%m-%d %H:%M:%S")

        # Generate mostly comfortable values with occasional abnormal spikes.
        scenario = random.choices(
            population=["normal", "hot", "cold", "humid", "critical_hot"],
            weights=[68, 12, 8, 10, 2],
            k=1,
        )[0]

        if scenario == "hot":
            room_temp = round(random.uniform(26.5, 31.5), 1)
            room_humi = round(random.uniform(42, 58), 1)
        elif scenario == "cold":
            room_temp = round(random.uniform(15.5, 21.5), 1)
            room_humi = round(random.uniform(38, 56), 1)
        elif scenario == "humid":
            room_temp = round(random.uniform(22.5, 25.8), 1)
            room_humi = round(random.uniform(61, 82), 1)
        elif scenario == "critical_hot":
            room_temp = round(random.uniform(40, 42.5), 1)
            room_humi = round(random.uniform(45, 68), 1)
        else:
            room_temp = round(random.uniform(22, 26), 1)
            room_humi = round(random.uniform(40, 60), 1)

        alert_type = classify_mock_environment(room_temp, room_humi)
        mock_data.append([timestamp, room_temp, room_humi, alert_type])

    mock_data.sort(key=lambda row: row[0])

    try:
        with open(output_file, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADERS)
            writer.writerows(mock_data)

        print(f"[Success] Generated mock environment logs: {output_file}")
        print(f"[Info] Records: {num_records}")
        print(f"[Info] Headers: {', '.join(CSV_HEADERS)}")

    except OSError as exc:
        print(f"[Error] Failed to generate mock data: {exc}")


if __name__ == "__main__":
    generate_mock_csv()
