import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from logger import get_recent_logs

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parent
HEARTBEAT_FILE = BASE / "sensor_monitor_heartbeat.txt"
SETTINGS_FILE  = BASE / "settings.json"


# ── 实时状态 ──────────────────────────────────────────────
@app.get("/api/status")
def status():
    try:
        if not HEARTBEAT_FILE.exists():
            return {"status": "OFFLINE", "temp": None, "humi": None,
                    "timestamp": None, "message": ""}

        raw = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
        parts = raw.split(",", 3)
        timestamp = parts[0]
        temp      = float(parts[1])
        humi      = float(parts[2])
        message   = parts[3] if len(parts) > 3 else ""

        age = datetime.now().timestamp() - HEARTBEAT_FILE.stat().st_mtime
        if age <= 30:
            label = "ONLINE"
        elif age <= 180:
            label = "DEGRADED"
        else:
            label = "OFFLINE"

        return {"status": label, "temp": temp, "humi": humi,
                "timestamp": timestamp, "message": message}

    except Exception:
        return {"status": "OFFLINE", "temp": None, "humi": None,
                "timestamp": None, "message": ""}


# ── 历史记录 ──────────────────────────────────────────────
@app.get("/api/logs")
def logs(n: int = 50):
    return get_recent_logs(n)


# ── 子女端设置（读取） ─────────────────────────────────────
@app.get("/api/settings")
def get_settings():
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── 子女端设置（保存） ─────────────────────────────────────
@app.post("/api/settings")
async def save_settings(request: Request):
    try:
        data = await request.json()
        SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
