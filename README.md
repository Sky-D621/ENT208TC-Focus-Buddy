# Elderly Home Environment Companion

> A local elder-care prototype that connects M5Stack sensor data, AI environment judgment, family/elder frontend pages, and local event logs.

## Project Overview

This project is now an independent-living environment companion for older adults. It reads temperature and humidity data from an M5Stack device on a local serial port, evaluates the room state with an OpenAI-compatible LLM, stores local logs, and exposes a local HTTP API for the frontend pages.

The frontend has two static HTML pages:

- Family side: environment dashboard, elder profile, medication settings, and alarm settings.
- Elder side: large temperature/humidity display, reminders, browser voice output, and AI chat.

The hardware connection is handled by the Python backend, not by the browser.

## Current Architecture

```text
M5Stack sensor
  -> COM5 serial data
  -> Focus-Buddy/sensor_monitor.py
  -> Focus-Buddy/elderly_health_logs.csv + sensor_monitor_heartbeat.txt
  -> Focus-Buddy/api_server.py
  -> Focus-Buddy/frontend/family.html and elderly.html
```

`api_server.py` is the main entry point for demo usage. It starts the local HTTP API and also starts the sensor monitor in a background thread.

## Directory Structure

```text
ENT/
├── .env
├── .gitignore
├── README.md
└── Focus-Buddy/
    ├── ai_coach.py
    ├── api_server.py
    ├── sensor_monitor.py
    ├── logger.py
    ├── generate_mock_data.py
    ├── requirements-api.txt
    ├── API_DOC.md
    └── frontend/
        ├── family.html
        ├── elderly.html
        └── README.md
```

## Environment Variables

Create `.env` in the project root:

```dotenv
LLM_API_KEY=your_api_key_here
```

Optional overrides:

```dotenv
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-v4-pro
SENSOR_SERIAL_PORT=COM5
SENSOR_BAUD_RATE=115200
```

Notes:

- `LLM_API_KEY` stays local and must not be committed.
- The default model is `deepseek-v4-pro`.
- The default sensor port is `COM5`.

## Install Dependencies

From the backend folder:

```powershell
cd C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy
pip install -r requirements-api.txt
pip install pyserial python-dotenv requests
```

If `pyserial`, `python-dotenv`, and `requests` are already installed, the second command is not needed.

## Run The Demo

Start the backend API and sensor monitor:

```powershell
cd C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy
python api_server.py
```

Then open the frontend pages:

```text
C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy\frontend\family.html
C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy\frontend\elderly.html
```

The frontend pages call:

```text
http://localhost:8000
```

## Expected M5Stack Serial Format

The current M5Stack output format is:

```text
DATA:25.4,58.8
```

This means:

```text
temperature = 25.4 C
humidity = 58.8 %
```

The parser also accepts:

```text
25.4,58.8
temp=25.4,humi=58.8
temperature:25.4 humidity:58.8
温度:25.4 湿度:58.8
```

## API Endpoints

The frontend uses these local endpoints:

```text
GET  /api/status
GET  /api/logs?n=20
GET  /api/settings
POST /api/settings
POST /api/chat
```

Main status response example:

```json
{
  "status": "ONLINE",
  "temp": 25.4,
  "humi": 58.8,
  "timestamp": "2026-05-04 15:57:06",
  "message": "",
  "message_en": "",
  "source": "live"
}
```

`source` values:

- `live`: data came from the current sensor heartbeat.
- `latest_log`: data fell back to the latest CSV record.
- `none`: no data is available.

## Local Data Files

Runtime files are generated locally and ignored by Git:

```text
Focus-Buddy/elderly_health_logs.csv
Focus-Buddy/sensor_monitor_heartbeat.txt
Focus-Buddy/sensor_monitor_debug.json
Focus-Buddy/settings.json
```

Do not commit these files because they may contain private environment records or family settings.

## Testing Without Hardware

Generate mock data:

```powershell
cd C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy
python generate_mock_data.py
```

This overwrites `elderly_health_logs.csv`, so do not run it during real hardware testing unless you intentionally want to replace local logs.

## Git Notes

Before pushing, check:

```powershell
git status
```

Do not commit:

```text
.env
__pycache__/
*.pyc
elderly_health_logs.csv
sensor_monitor_heartbeat.txt
sensor_monitor_debug.json
settings.json
```

## Safety Note

This is a course/project prototype for environment awareness and companionship. It is not a medical device, emergency response system, or replacement for human care.
