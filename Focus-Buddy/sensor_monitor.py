import os
import re
import time
from datetime import datetime
from pathlib import Path

import serial
from serial import SerialException

from ai_coach import evaluate_environment_state
from logger import log_sensor_alert


# Serial port configuration.
# Override these values in .env if your M5Stack uses a different port or baud rate.
SERIAL_PORT = os.getenv("SENSOR_SERIAL_PORT", "COM3")
BAUD_RATE = int(os.getenv("SENSOR_BAUD_RATE", "115200"))
SERIAL_TIMEOUT_SECONDS = 2
RECONNECT_DELAY_SECONDS = 5

# Environment thresholds for elderly living comfort.
CRITICAL_HOT_TEMP_THRESHOLD = 40.0
HOT_TEMP_THRESHOLD = 26.0
COLD_TEMP_THRESHOLD = 22.0
HUMIDITY_THRESHOLD = 60.0

# Alarm cooldown. The same abnormal state must not trigger AI/audio again
# within this period, which prevents repeated disturbance to the elder.
ALARM_COOLDOWN_SECONDS = 30 * 60
last_alarm_at = {}

# Local audio mapping. Keep the files under ./audio beside this script.
BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_FILE = BASE_DIR / "sensor_monitor_heartbeat.txt"
AUDIO_FILES = {
    "[CRITICAL_HOT]": BASE_DIR / "audio" / "critical_hot_check_now.mp3",
    "[HOT]": BASE_DIR / "audio" / "hot_drink_water.mp3",
    "[HOT_WARNING]": BASE_DIR / "audio" / "hot_drink_water.mp3",
    "[COLD]": BASE_DIR / "audio" / "cold_keep_warm.mp3",
    "[COLD_WARNING]": BASE_DIR / "audio" / "cold_keep_warm.mp3",
    "[HUMID]": BASE_DIR / "audio" / "humid_open_window.mp3",
    "[HUMID_WARNING]": BASE_DIR / "audio" / "humid_open_window.mp3",
}

# Only these labels are valid model outputs.
VALID_LABELS = {"[CRITICAL_HOT]", "[HOT]", "[COLD]", "[HUMID]", "[NORMAL]"}


def parse_sensor_line(raw_line: str) -> tuple[float, float] | None:
    """
    Parse one serial line and extract temperature and humidity.

    This parser intentionally accepts multiple common M5Stack formats, such as:
    - "temp=28.5,humi=60"
    - "temperature: 28.5 humidity: 60"
    - "T:28.5 H:60"

    Returns:
        A tuple of (temperature, humidity), or None if parsing fails.
    """
    normalized = raw_line.strip()
    if not normalized:
        return None

    temp_match = re.search(
        r"(?:temp|temperature|t)\s*[:=]\s*(-?\d+(?:\.\d+)?)",
        normalized,
        flags=re.IGNORECASE,
    )
    humi_match = re.search(
        r"(?:humi|humidity|h)\s*[:=]\s*(-?\d+(?:\.\d+)?)",
        normalized,
        flags=re.IGNORECASE,
    )

    if not temp_match or not humi_match:
        return None

    try:
        return float(temp_match.group(1)), float(humi_match.group(1))
    except ValueError:
        return None


def detect_abnormal_state(temp: float, humi: float) -> str | None:
    """
    Convert raw sensor values into a local abnormal state key.

    The key is used before the LLM call so cooldown can block repeated requests
    and repeated audio playback for the same condition.
    """
    if temp >= CRITICAL_HOT_TEMP_THRESHOLD:
        return "极端高温"
    if temp > HOT_TEMP_THRESHOLD:
        return "高温"
    if temp < COLD_TEMP_THRESHOLD:
        return "低温"
    if humi > HUMIDITY_THRESHOLD:
        return "高湿"
    return None


def is_in_cooldown(state: str) -> bool:
    """
    Return True if the same abnormal state has already alarmed recently.
    """
    last_seen = last_alarm_at.get(state)
    if last_seen is None:
        return False

    return time.time() - last_seen < ALARM_COOLDOWN_SECONDS


def mark_alarm_time(state: str) -> None:
    """
    Store the alarm time for cooldown enforcement.
    """
    last_alarm_at[state] = time.time()


def classify_environment_with_llm(temp: float, humi: float) -> str:
    """
    Ask the LLM to classify the current environment into one strict label.

    If the API key is missing, the request fails, or the model returns invalid
    text, this function falls back to a deterministic local label. The daemon
    should keep running even when the network or LLM service is unavailable.
    """
    fallback_label = get_local_environment_label(temp, humi)

    try:
        label = evaluate_environment_state(temp, humi)

        if label in VALID_LABELS:
            return label

        print(f"Invalid LLM label received: {label!r}. Falling back locally.")
        return fallback_label

    except (
        ValueError,
        TypeError,
    ) as exc:
        print(f"Environment evaluation failed: {exc}. Falling back locally.")
        return fallback_label


def get_local_environment_label(temp: float, humi: float) -> str:
    """
    Deterministic local fallback classifier used when the LLM is unavailable.
    """
    if temp >= CRITICAL_HOT_TEMP_THRESHOLD:
        return "[CRITICAL_HOT]"
    if temp > HOT_TEMP_THRESHOLD:
        return "[HOT]"
    if temp < COLD_TEMP_THRESHOLD:
        return "[COLD]"
    if humi > HUMIDITY_THRESHOLD:
        return "[HUMID]"
    return "[NORMAL]"


def write_monitor_heartbeat(temp: float, humi: float) -> None:
    """
    Write a lightweight heartbeat file for the Streamlit dashboard.

    The dashboard uses this file's update time to decide whether this daemon is
    actively polling hardware. Heartbeat write failures should not stop sensor
    monitoring.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        HEARTBEAT_FILE.write_text(f"{timestamp},{temp},{humi}", encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write monitor heartbeat: {exc}")


def play_audio_for_label(label: str) -> None:
    """
    Play the local audio file mapped to the warning label.

    pygame is attempted first because it is cross-platform. If pygame is not
    installed or playback fails, the function falls back to os.startfile on
    Windows. Audio failure must never crash the monitor daemon.
    """
    audio_path = AUDIO_FILES.get(label)
    if not audio_path:
        return

    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}")
        return

    try:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(str(audio_path))
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.quit()
        return
    except Exception as exc:
        print(f"pygame playback failed: {exc}. Trying OS default player.")

    try:
        if os.name == "nt":
            os.startfile(audio_path)  # noqa: S606 - Local trusted audio path.
        else:
            os.system(f'"{audio_path}"')
    except Exception as exc:
        print(f"OS audio playback failed: {exc}")


def handle_sensor_reading(temp: float, humi: float) -> None:
    """
    Process one parsed sensor reading.

    The cooldown check happens before calling the LLM and before playing audio,
    which protects both API cost and the elder's living environment.
    """
    write_monitor_heartbeat(temp, humi)

    abnormal_state = detect_abnormal_state(temp, humi)
    if abnormal_state is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_sensor_alert(timestamp, temp, humi, "[NORMAL]")
        print(f"Normal reading: temp={temp}, humi={humi}")
        return

    if is_in_cooldown(abnormal_state):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_sensor_alert(timestamp, temp, humi, get_local_environment_label(temp, humi))
        print(f"Cooldown active for {abnormal_state}; skipping AI and audio.")
        return

    label = classify_environment_with_llm(temp, humi)

    if label == "[NORMAL]":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_sensor_alert(timestamp, temp, humi, label)
        print(f"LLM returned NORMAL for abnormal local reading: temp={temp}, humi={humi}")
        return

    mark_alarm_time(abnormal_state)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sensor_alert(timestamp, temp, humi, label)
    play_audio_for_label(label)

    print(f"Alert handled: timestamp={timestamp}, temp={temp}, humi={humi}, label={label}")


def monitor_serial_forever() -> None:
    """
    Continuously listen to the serial port and auto-reconnect on failure.

    This function is intended to run as a long-lived background daemon. Any
    hardware disconnect, serial decode issue, or unexpected line format should
    be handled without terminating the process.
    """
    while True:
        serial_client = None

        try:
            print(f"Connecting to serial port {SERIAL_PORT} at {BAUD_RATE} baud...")
            serial_client = serial.Serial(
                SERIAL_PORT,
                BAUD_RATE,
                timeout=SERIAL_TIMEOUT_SECONDS,
            )
            print("Serial connection established.")

            while True:
                try:
                    raw_bytes = serial_client.readline()
                    if not raw_bytes:
                        continue

                    raw_line = raw_bytes.decode("utf-8", errors="ignore").strip()
                    parsed = parse_sensor_line(raw_line)

                    if parsed is None:
                        print(f"Skipped unparsable serial line: {raw_line!r}")
                        continue

                    temp, humi = parsed
                    handle_sensor_reading(temp, humi)

                except SerialException as exc:
                    print(f"Serial device error: {exc}. Reconnecting soon.")
                    break
                except Exception as exc:
                    print(f"Unexpected reading error: {exc}. Continuing monitor loop.")

        except SerialException as exc:
            print(f"Unable to open serial port: {exc}. Retrying in {RECONNECT_DELAY_SECONDS}s.")
        except Exception as exc:
            print(f"Unexpected monitor error: {exc}. Retrying in {RECONNECT_DELAY_SECONDS}s.")
        finally:
            if serial_client and serial_client.is_open:
                try:
                    serial_client.close()
                except SerialException:
                    pass

        time.sleep(RECONNECT_DELAY_SECONDS)


if __name__ == "__main__":
    monitor_serial_forever()
