import requests


# 请将下面的配置替换成你自己的 OpenAI 兼容接口信息
API_KEY = "请在这里填写你的 API_KEY"
API_URL = "https://api.example.com/v1/chat/completions"
MODEL_NAME = "your-model-name"

# 当接口调用失败时，返回这条备用提示
FALLBACK_TEXT = "深呼吸3次，然后闭眼休息2分钟。"


def get_micro_task(emotion: str) -> str:
    """
    根据用户当前的分心情绪，调用大模型生成一个可立即执行的微动作指令。

    参数：
        emotion: 用户当前的情绪，例如“😰 焦虑”“🥱 枯燥”

    返回：
        模型生成的微动作指令；如果调用失败，则返回备用字符串。
    """
    # 按要求硬编码 System Prompt，并把 emotion 动态插入提示词中
    system_prompt = (
        "你是一个针对极度焦虑大学生的行为干预教练。严禁说教、严禁灌鸡汤。"
        f"用户现在正处于认知过载状态，由于【{emotion}】而分心。"
        "你必须在 40 个字以内，给出一个不需要动脑的、立刻能执行的物理微动作指令"
        "（例如：喝水、深呼吸、在纸上画圈），帮助他们重置注意力。"
    )

    # 如果还没有填写真实 API_KEY，就直接返回备用结果，避免请求报错
    if not API_KEY or "请在这里填写" in API_KEY:
        return FALLBACK_TEXT

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"我的分心情绪是：{emotion}。请直接给我一个微动作指令。",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 50,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        if content:
            return content
        return FALLBACK_TEXT

    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        return FALLBACK_TEXT


if __name__ == "__main__":
    # 这里给一个简单的本地测试示例，方便你单独运行此脚本时验证效果
    test_emotion = "😰 焦虑"
    print(get_micro_task(test_emotion))
