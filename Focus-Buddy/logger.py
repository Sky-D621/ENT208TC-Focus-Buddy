import csv
from datetime import datetime
from pathlib import Path


# 数据文件保存到当前脚本所在目录，便于项目内直接使用
CSV_FILE = Path(__file__).resolve().parent / "focus_data.csv"


def log_distraction(study_duration, emotion) -> None:
    """
    记录一次分心事件到本地 CSV 文件中。

    参数：
        study_duration: 用户已经专注的时长，例如“12分钟”或 720
        emotion: 本次触发分心的情绪原因，例如“😰 焦虑”
    """
    # 获取当前系统时间戳，格式清晰，方便后续查看和分析
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 判断文件是否已存在；不存在时先写入表头
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["Timestamp", "Duration", "Emotion"])

        writer.writerow([timestamp, study_duration, emotion])


if __name__ == "__main__":
    # 简单示例：直接运行此文件时，会写入一条测试数据
    log_distraction("10分钟", "😰 焦虑")
    print(f"记录已写入：{CSV_FILE}")
