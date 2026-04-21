# Elderly Home Care Dashboard API Guide

This document is for frontend developers who need to read environment data from
the local Python backend and render the elderly home monitoring dashboard.

## Project Overview

The system has three backend-facing modules:

- `sensor_monitor.py`: Background daemon. Reads M5Stack serial data, evaluates environment state, plays local audio, and writes logs.
- `logger.py`: Local CSV storage layer. Frontend should mainly call this module.
- `ai_coach.py`: LLM environment evaluator. Usually called by `sensor_monitor.py`, not directly by the frontend.

The Streamlit frontend should treat `logger.py` and the heartbeat file as its
main data sources.

## Data File

Environment logs are stored in:

```text
elderly_health_logs.csv
```

CSV schema:

```csv
Timestamp,Room_Temp,Room_Humi,Alert_Type
```

Field meanings:

| Field | Type | Description |
| --- | --- | --- |
| `Timestamp` | string | Local timestamp, format `YYYY-MM-DD HH:MM:SS`. |
| `Room_Temp` | number/string | Indoor room temperature in Celsius. |
| `Room_Humi` | number/string | Indoor room humidity percentage. |
| `Alert_Type` | string | Environment status label returned by AI or local fallback. |

Supported `Alert_Type` values:

| Label | Meaning | Suggested UI Severity |
| --- | --- | --- |
| `[NORMAL]` | Environment is normal. | Success / green |
| `[HOT]` | Room is hotter than ideal for older adults. | Warning / orange |
| `[COLD]` | Room is colder than ideal for older adults. | Warning / blue |
| `[HUMID]` | Room humidity is too high. | Warning / teal |
| `[CRITICAL_HOT]` | Extremely high temperature, urgent risk. | Critical / red |

Older compatibility labels may appear if old data still exists:

```text
[HOT_WARNING], [COLD_WARNING], [HUMID_WARNING]
```

Frontend should map them to the same visual meaning as `[HOT]`, `[COLD]`, and
`[HUMID]`.

## Frontend Read API

Import from `logger.py`:

```python
from logger import get_recent_logs
```

### `get_recent_logs(n=10)`

Reads the most recent environment records.

Parameters:

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `n` | int | `10` | Number of latest records to return. |

Returns:

```python
list[dict]
```

Return order:

```text
Newest first
```

Example:

```python
logs = get_recent_logs(10)
```

Example return value:

```python
[
    {
        "Timestamp": "2026-04-21 14:00:00",
        "Room_Temp": "29.5",
        "Room_Humi": "58.0",
        "Alert_Type": "[HOT]",
    },
    {
        "Timestamp": "2026-04-21 13:55:00",
        "Room_Temp": "25.0",
        "Room_Humi": "52.0",
        "Alert_Type": "[NORMAL]",
    },
]
```

Empty or error case:

```python
[]
```

The function already handles missing files, empty CSV files, malformed headers,
and basic file read errors.

## Frontend Write API

Most frontend code should not write logs directly. The background daemon writes
sensor records automatically.

If a test page or admin tool needs to append a record, import:

```python
from logger import log_environment_event
```

### `log_environment_event(room_temp, room_humi, alert_type, timestamp=None)`

Appends one row to `elderly_health_logs.csv`.

Example:

```python
log_environment_event(28.5, 62, "[HUMID]")
```

If `timestamp` is omitted, backend local time is used.

## Live Status Heartbeat

The background daemon writes a lightweight heartbeat file:

```text
sensor_monitor_heartbeat.txt
```

Format:

```text
Timestamp,Temperature,Humidity
```

Example:

```text
2026-04-21 14:00:00,25.4,51.2
```

Frontend status logic recommendation:

| Heartbeat age | Status |
| --- | --- |
| `<= 30 seconds` | `ONLINE` |
| `31-180 seconds` | `DEGRADED` |
| `> 180 seconds` or file missing | `OFFLINE` |

Use the heartbeat for top-level live metrics when available. If the heartbeat is
missing, fall back to the newest row from `get_recent_logs(1)`.

## Charting Recommendation

For temperature trend:

```python
logs = get_recent_logs(200)
```

Then reverse the list before plotting, because `get_recent_logs()` returns
newest-first records:

```python
chart_rows = list(reversed(logs))
```

Use:

- X axis: `Timestamp`
- Y axis: `Room_Temp`

Humidity can be added later with:

- Y axis: `Room_Humi`

## Alert List Recommendation

Filter out normal rows:

```python
alerts = [
    row for row in get_recent_logs(50)
    if row.get("Alert_Type") != "[NORMAL]"
]
```

Recommended English copy:

```text
2026-04-21 14:00:00 triggered a high temperature warning.
2026-04-21 15:30:00 triggered a high humidity warning.
2026-04-21 16:10:00 triggered a critical high temperature alert.
```

Recommended label mapping:

```python
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
```

## LLM Evaluation API

Frontend usually does not need this function. It is documented here only for
debugging and internal tools.

Import:

```python
from ai_coach import evaluate_environment_state
```

### `evaluate_environment_state(temp, humi)`

Returns one strict label:

```text
[HOT], [COLD], [HUMID], [NORMAL], [CRITICAL_HOT]
```

Example:

```python
label = evaluate_environment_state(28.5, 65)
```

Security note:

`ai_coach.py` reads the API key from `.env`:

```text
LLM_API_KEY=your_api_key_here
```

Never expose this value in frontend UI, logs, browser console, or GitHub.

## Mock Data

Use this script to generate local test data when hardware is unavailable:

```bash
python generate_mock_data.py
```

Warning:

This overwrites `elderly_health_logs.csv`.

## Backend Startup

Start the hardware polling daemon:

```bash
python sensor_monitor.py
```

Start the Streamlit dashboard:

```bash
streamlit run app.py
```

## Frontend Integration Notes

- Treat CSV values as strings when reading, then parse numeric fields for charts.
- Always handle an empty `get_recent_logs()` response.
- Do not assume the backend daemon is running; check heartbeat status.
- Do not call the LLM directly from the UI unless this is an explicit admin-only action.
- Do not commit `.env` or real sensor logs to GitHub.
