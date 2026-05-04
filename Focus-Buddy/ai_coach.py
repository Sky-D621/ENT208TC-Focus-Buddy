import os

import requests
from dotenv import load_dotenv


# Load local environment variables from .env.
load_dotenv()

# OpenAI-compatible API configuration.
API_KEY = os.getenv("LLM_API_KEY")
API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
MODEL_NAME = os.getenv("LLM_MODEL", "deepseek-v4-pro")

# The model must only return one of these labels.
VALID_LABELS = {"[HOT]", "[COLD]", "[HUMID]", "[NORMAL]", "[CRITICAL_HOT]"}


def get_local_environment_label(temp: float, humi: float) -> str:
    """
    Return a deterministic local fallback label when the LLM request fails.

    This keeps the application safe and usable even when the network or API
    provider is unavailable.
    """
    if temp >= 40:
        return "[CRITICAL_HOT]"
    if temp > 26:
        return "[HOT]"
    if temp < 22:
        return "[COLD]"
    if humi > 60:
        return "[HUMID]"
    return "[NORMAL]"


def build_environment_prompt(temp: float, humi: float) -> str:
    """
    Build the strict system prompt for elder-care environment evaluation.
    """
    return (
        "你是一个专业的独居老人监护助手。输入是当前的室内温度（temp）和湿度（humi）。"
        "请结合老年人最适宜的居住环境（22-26℃，湿度 40-60%）进行判断。\n\n"
        "输出约束： 严禁输出长篇大论。你只需要输出以下四个标签之一："
        "[HOT], [COLD], [HUMID], [NORMAL]。如果数值极其离谱（如 40 度），"
        "请输出 [CRITICAL_HOT]。"
        f"\n\n当前输入：temp={temp}, humi={humi}。"
    )


def evaluate_environment_state(temp, humi) -> str:
    """
    Evaluate the current room temperature and humidity through an LLM.

    Parameters:
        temp: Current indoor temperature.
        humi: Current indoor humidity percentage.

    Returns:
        One strict environment label:
        [HOT], [COLD], [HUMID], [NORMAL], or [CRITICAL_HOT].

    Raises:
        ValueError: If LLM_API_KEY is not configured in .env.
    """
    if not API_KEY:
        raise ValueError("未找到 LLM_API_KEY，请检查 .env 文件配置")

    try:
        temp_value = float(temp)
        humi_value = float(humi)
    except (TypeError, ValueError):
        return "[NORMAL]"

    fallback_label = get_local_environment_label(temp_value, humi_value)
    system_prompt = build_environment_prompt(temp_value, humi_value)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请只输出一个环境状态标签。"},
        ],
        "temperature": 0,
        "max_tokens": 20,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=5)
        response.raise_for_status()

        result = response.json()
        label = result["choices"][0]["message"]["content"].strip()

        if label in VALID_LABELS:
            return label

        return fallback_label

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
        return fallback_label


if __name__ == "__main__":
    print(evaluate_environment_state(28.5, 65))
