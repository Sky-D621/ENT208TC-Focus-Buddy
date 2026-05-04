import json
import os
import threading
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logger import get_recent_logs


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_FILE = BASE_DIR / "sensor_monitor_heartbeat.txt"
SENSOR_DEBUG_FILE = BASE_DIR / "sensor_monitor_debug.json"
SETTINGS_FILE = BASE_DIR / "settings.json"

HEARTBEAT_ONLINE_SECONDS = 30
HEARTBEAT_DEGRADED_SECONDS = 180

ALERT_MESSAGES = {
    "[CRITICAL_HOT]": {
        "zh": "室内温度极高，请立即开空调或转移到凉爽处，注意防暑！",
        "en": "Extreme heat detected. Please turn on AC or move to a cooler area immediately.",
    },
    "[HOT]": {
        "zh": "室内偏热，请注意补水，适当开窗通风。",
        "en": "Room is warm. Please drink water and open windows for ventilation.",
    },
    "[COLD]": {
        "zh": "室内偏冷，请注意保暖，添加衣物。",
        "en": "Room is cold. Please keep warm and add extra clothing.",
    },
    "[HUMID]": {
        "zh": "室内湿度较高，建议开窗通风或使用除湿机。",
        "en": "High humidity detected. Please open windows or use a dehumidifier.",
    },
    "[NORMAL]": {"zh": "", "en": ""},
}

app = FastAPI(title="Elderly Home Care Local API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_history = []
sensor_thread_started = False


@app.on_event("startup")
def start_sensor_monitor_thread() -> None:
    """
    Start sensor monitoring inside the API process.

    This keeps the demo workflow simple: running api_server.py is enough to
    serve the frontend and poll the M5Stack. Set DISABLE_SENSOR_MONITOR=1 if
    you want to run sensor_monitor.py in a separate terminal for debugging.
    """
    global sensor_thread_started

    if os.getenv("DISABLE_SENSOR_MONITOR") == "1" or sensor_thread_started:
        return

    try:
        from sensor_monitor import monitor_serial_forever

        thread = threading.Thread(target=monitor_serial_forever, daemon=True)
        thread.start()
        sensor_thread_started = True
        print("Sensor monitor thread started from api_server.py.")
    except Exception as exc:
        print(f"Failed to start sensor monitor thread: {exc}")


def read_heartbeat() -> dict | None:
    """Read the latest sensor heartbeat written by sensor_monitor.py."""
    try:
        if not HEARTBEAT_FILE.exists():
            return None

        raw_text = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
        timestamp, temp, humi = raw_text.split(",", 2)
        age_seconds = datetime.now().timestamp() - HEARTBEAT_FILE.stat().st_mtime

        return {
            "timestamp": timestamp,
            "temp": float(temp),
            "humi": float(humi),
            "age_seconds": age_seconds,
        }
    except (OSError, ValueError):
        return None


def read_sensor_debug() -> dict:
    """Read serial monitor diagnostics written by sensor_monitor.py."""
    try:
        if not SENSOR_DEBUG_FILE.exists():
            return {}
        return json.loads(SENSOR_DEBUG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_backend_status(age_seconds: float | None) -> str:
    """Convert heartbeat age into a frontend-friendly status label."""
    if age_seconds is None:
        return "OFFLINE"
    if age_seconds <= HEARTBEAT_ONLINE_SECONDS:
        return "ONLINE"
    if age_seconds <= HEARTBEAT_DEGRADED_SECONDS:
        return "DEGRADED"
    return "OFFLINE"


def load_settings() -> dict:
    """Load family-side settings saved by the frontend."""
    if not SETTINGS_FILE.exists():
        return {"profile": {}, "medications": [], "alarms": []}

    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profile": {}, "medications": [], "alarms": []}


def latest_log_row() -> dict | None:
    """Return the latest environment log row if one exists."""
    logs = get_recent_logs(1)
    return logs[0] if logs else None


def message_for_label(label: str) -> dict:
    """Map a backend alert label to frontend voice/display copy."""
    return ALERT_MESSAGES.get(label, ALERT_MESSAGES["[NORMAL]"])


@app.get("/api/status")
def get_status():
    heartbeat = read_heartbeat()
    latest_row = latest_log_row()

    if heartbeat:
        status = get_backend_status(heartbeat["age_seconds"])
        temp = heartbeat["temp"]
        humi = heartbeat["humi"]
        timestamp = heartbeat["timestamp"]
    elif latest_row:
        status = "DEGRADED"
        temp = float(latest_row.get("Room_Temp", 0))
        humi = float(latest_row.get("Room_Humi", 0))
        timestamp = latest_row.get("Timestamp")
    else:
        return {
            "status": "OFFLINE",
            "temp": None,
            "humi": None,
            "timestamp": None,
            "message": "",
            "message_en": "",
            "source": "none",
            "sensor_debug": read_sensor_debug(),
        }

    latest_label = latest_row.get("Alert_Type", "[NORMAL]") if latest_row else "[NORMAL]"
    messages = message_for_label(latest_label)

    return {
        "status": status,
        "temp": temp,
        "humi": humi,
        "timestamp": timestamp,
        "message": messages["zh"],
        "message_en": messages["en"],
        "source": "live" if heartbeat else "latest_log",
        "sensor_debug": read_sensor_debug(),
    }


@app.get("/api/logs")
def get_logs(n: int = 20):
    return get_recent_logs(n)


@app.get("/api/settings")
def get_settings():
    return load_settings()


@app.post("/api/settings")
def save_settings(body: dict):
    SETTINGS_FILE.write_text(
        json.dumps(body, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True}


@app.post("/api/chat")
def chat(body: dict):
    user_message = (body.get("message") or "").strip()
    if not user_message:
        return {"reply": ""}

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return {"reply": "未配置 LLM_API_KEY，暂时无法使用聊天功能。"}

    heartbeat = read_heartbeat()
    if heartbeat:
        context = f"当前室内温度 {heartbeat['temp']}°C，湿度 {heartbeat['humi']}%。"
    else:
        context = "当前传感器离线。"

    if not chat_history:
        chat_history.append(
            {
                "role": "system",
                "content": (
                    "你是一个关爱独居老人的智能陪伴助手。"
                    "请用中文回答，语气温和，回答尽量简短。"
                    f"{context}"
                ),
            }
        )

    chat_history.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("LLM_MODEL", "deepseek-v4-pro"),
                "messages": chat_history,
                "temperature": 0.4,
                "max_tokens": 150,
            },
            timeout=10,
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()
        chat_history.append({"role": "assistant", "content": reply})

        if len(chat_history) > 21:
            del chat_history[1:3]

        return {"reply": reply}

    except (
        requests.Timeout,
        requests.ConnectionError,
        requests.HTTPError,
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ):
        return {"reply": "抱歉，我现在暂时无法连接 AI 服务。"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
