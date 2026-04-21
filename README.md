# Elderly Home Environment Companion

> A lightweight Python-based environment sensing and family dashboard system for elders living alone.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Serial](https://img.shields.io/badge/Hardware-M5Stack%20Serial-green.svg)](https://pyserial.readthedocs.io/)

## Project Overview

This project has shifted from a Pomodoro focus tool into an independent-living elder-care prototype.

The system listens to temperature and humidity data sent by an M5Stack device through a serial port, evaluates the room environment with an OpenAI-compatible LLM, plays local voice reminders when needed, records local CSV logs, and provides a Streamlit dashboard for family members to review the latest home conditions.

The current goal is not medical diagnosis. It is a lightweight environmental awareness and companionship layer that helps families notice uncomfortable or risky indoor conditions such as high temperature, low temperature, or high humidity.

## Core Features

- **Serial Sensor Monitoring:** `sensor_monitor.py` continuously listens to M5Stack serial data and automatically reconnects if the hardware disconnects.
- **Environment Evaluation:** `ai_coach.py` exposes `evaluate_environment_state(temp, humi)` and returns strict labels such as `[HOT]`, `[COLD]`, `[HUMID]`, `[NORMAL]`, and `[CRITICAL_HOT]`.
- **Alarm Cooldown:** The backend prevents the same abnormal state from repeatedly triggering AI calls and voice playback within a 30-minute window.
- **Local Audio Playback:** Warning labels are mapped to local audio files under the `audio/` directory.
- **Local CSV Logging:** `logger.py` writes environment events into `elderly_health_logs.csv` with UTF-8-safe encoding.
- **Family Dashboard:** `app.py` displays live temperature, live humidity, historical temperature trend, recent alert records, and backend polling status.
- **Mock Data Generator:** `generate_mock_data.py` can generate realistic test data when no hardware is connected.

## Technical Architecture

- **Hardware Input:** M5Stack sends temperature and humidity strings over Serial.
- **Backend Daemon:** `sensor_monitor.py` parses sensor readings, handles reconnects, enforces cooldown, calls AI evaluation, plays audio, and logs events.
- **AI Layer:** `ai_coach.py` calls an OpenAI-compatible `/v1/chat/completions` endpoint using `LLM_API_KEY` from `.env`.
- **Persistence:** `logger.py` stores local environment logs in CSV format.
- **Dashboard:** `app.py` uses Streamlit to render metrics, charts, alerts, and backend health status.

## Directory Structure

```text
ENT/
├── .env                         # Local environment variables, ignored by Git
├── .gitignore                   # Ignore rules for secrets, caches, and local data
├── README.md                    # Project documentation
└── Focus-Buddy/
    ├── app.py                   # Streamlit family dashboard
    ├── ai_coach.py              # LLM environment evaluation logic
    ├── logger.py                # Local CSV logging and recent log queries
    ├── sensor_monitor.py        # Background serial-monitoring daemon
    ├── generate_mock_data.py    # Mock elder-care environment data generator
    ├── requirements.txt         # Python dependencies
    ├── elderly_health_logs.csv  # Generated local environment logs
    └── audio/                   # Local voice reminder files
```

## Environment Variables

Create a `.env` file in the project root. Do not commit this file to GitHub.

```dotenv
LLM_API_KEY=your_api_key_here
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-chat
SENSOR_SERIAL_PORT=COM3
SENSOR_BAUD_RATE=115200
```

Notes:

- `LLM_API_KEY` is required for real LLM evaluation.
- `LLM_API_URL` can be changed to any OpenAI-compatible provider, such as DeepSeek or Kimi.
- `SENSOR_SERIAL_PORT` should match the port used by your M5Stack device.
- If the LLM request fails, backend logic falls back to deterministic local rules where applicable.

## Installation

From the project directory:

```bash
cd Focus-Buddy
python -m venv venv
```

Activate the virtual environment:

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install streamlit requests python-dotenv pyserial pygame pandas
```

If you prefer using the existing dependency file:

```bash
pip install -r requirements.txt
```

## Running the System

Start the backend sensor daemon in one terminal:

```bash
cd Focus-Buddy
python sensor_monitor.py
```

Start the Streamlit dashboard in another terminal:

```bash
cd Focus-Buddy
streamlit run app.py
```

The dashboard will open at:

```text
http://localhost:8501
```

## Testing Without Hardware

If the M5Stack device is not connected yet, generate local mock records:

```bash
cd Focus-Buddy
python generate_mock_data.py
```

This creates or overwrites:

```text
elderly_health_logs.csv
```

Then run:

```bash
streamlit run app.py
```

The dashboard should show temperature metrics, a historical trend chart, and recent alert rows based on mock data.

## Expected Serial Input Format

`sensor_monitor.py` accepts several common text formats, for example:

```text
temp=28.5,humi=60
temperature: 28.5 humidity: 60
T:28.5 H:60
```

Each valid line should contain one temperature value and one humidity value.

## Data Files

The main local log file is:

```text
Focus-Buddy/elderly_health_logs.csv
```

Its schema is:

```csv
Timestamp,Room_Temp,Room_Humi,Alert_Type
```

The backend health indicator uses:

```text
Focus-Buddy/sensor_monitor_heartbeat.txt
```

The Streamlit dashboard checks this heartbeat file to determine whether `sensor_monitor.py` is actively polling hardware.

## Privacy And Safety

All sensor logs are stored locally in CSV files. The only external request is the environment evaluation request sent to the configured LLM API provider, which contains room temperature and humidity values.

This project is an environmental monitoring prototype. It should not be used as a medical device, emergency response system, or sole safety mechanism for an elder living alone.

## Git Safety

Secrets and local runtime data should not be committed.

Recommended ignored files include:

```gitignore
.env
__pycache__/
*.pyc
Focus-Buddy/elderly_health_logs.csv
Focus-Buddy/sensor_monitor_heartbeat.txt
```
