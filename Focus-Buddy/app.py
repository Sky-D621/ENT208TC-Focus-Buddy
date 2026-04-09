import time

import streamlit as st


# 25 分钟番茄钟的默认总时长（单位：秒）
DEFAULT_DURATION = 25 * 60


def init_session_state() -> None:
    """初始化页面运行所需的状态，避免每次重跑时重置倒计时。"""
    if "remaining_seconds" not in st.session_state:
        st.session_state.remaining_seconds = DEFAULT_DURATION

    if "is_running" not in st.session_state:
        # 首次进入页面时自动开始倒计时
        st.session_state.is_running = True

    if "show_emotions" not in st.session_state:
        st.session_state.show_emotions = False

    if "selected_emotion" not in st.session_state:
        st.session_state.selected_emotion = ""

    if "coach_message" not in st.session_state:
        st.session_state.coach_message = ""


def format_time(total_seconds: int) -> str:
    """把秒数转换成 MM:SS 的显示格式。"""
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def render_timer(timer_placeholder: st.delta_generator.DeltaGenerator) -> None:
    """使用 st.empty() 动态渲染大号倒计时器。"""
    time_text = format_time(st.session_state.remaining_seconds)
    timer_placeholder.markdown(
        f"""
        <div style="
            text-align: center;
            font-size: 5rem;
            font-weight: 700;
            color: #1f2937;
            background: linear-gradient(135deg, #fff7ed, #ffedd5);
            border: 2px solid #fdba74;
            border-radius: 20px;
            padding: 24px 12px;
            margin: 10px 0 24px 0;
            box-shadow: 0 10px 30px rgba(249, 115, 22, 0.12);
        ">
            {time_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def pause_for_distraction() -> None:
    """点击分心按钮后暂停倒计时，并展示情绪选项。"""
    st.session_state.is_running = False
    st.session_state.show_emotions = True
    st.session_state.selected_emotion = ""
    st.session_state.coach_message = ""


def choose_emotion(emotion: str) -> None:
    """记录用户当前情绪，并显示 AI 教练提示信息。"""
    st.session_state.selected_emotion = emotion
    st.session_state.coach_message = f"正在呼叫 AI 教练处理 {emotion}..."


def resume_timer() -> None:
    """关闭情绪面板并继续倒计时。"""
    st.session_state.is_running = True
    st.session_state.show_emotions = False


def reset_timer() -> None:
    """将番茄钟恢复到 25 分钟初始状态。"""
    st.session_state.remaining_seconds = DEFAULT_DURATION
    st.session_state.is_running = True
    st.session_state.show_emotions = False
    st.session_state.selected_emotion = ""
    st.session_state.coach_message = ""


st.set_page_config(page_title="专注番茄钟", page_icon="🍅", layout="centered")
init_session_state()

# 直接在当前文件中写入样式，满足“不使用外部 CSS 文件”的要求
st.markdown(
    """
    <style>
    .stButton button[kind="primary"] {
        background-color: #dc2626;
        color: white;
        border: none;
        font-weight: 700;
        border-radius: 12px;
        height: 3.2rem;
        width: 100%;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #b91c1c;
        color: white;
    }
    .emotion-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("专注番茄钟")
st.caption("用 25 分钟专注一件事；分心时先停下来，再让 AI 教练帮你识别状态。")

# 使用 st.empty() 作为计时器占位容器，后续每次重跑都会在这里更新倒计时
timer_placeholder = st.empty()
render_timer(timer_placeholder)

# 页面状态提示
if st.session_state.remaining_seconds == 0:
    st.success("当前番茄钟已完成，休息一下再开始下一轮吧。")
elif st.session_state.is_running:
    st.info("计时进行中，请保持专注。")
else:
    st.warning("计时已暂停。")

# 醒目的红色按钮：用户分心时触发暂停
if st.button("🆘 我分心了", type="primary", use_container_width=True):
    pause_for_distraction()
    st.rerun()

# 分心后展示情绪按钮
if st.session_state.show_emotions:
    st.markdown('<div class="emotion-title">你现在更接近哪种状态？</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    if col1.button("😰 焦虑", use_container_width=True):
        choose_emotion("😰 焦虑")
    if col2.button("🥱 枯燥", use_container_width=True):
        choose_emotion("🥱 枯燥")
    if col3.button("🤯 困难", use_container_width=True):
        choose_emotion("🤯 困难")
    if col4.button("📱 手机诱惑", use_container_width=True):
        choose_emotion("📱 手机诱惑")

    if st.session_state.coach_message:
        st.write(st.session_state.coach_message)

# 额外提供继续与重置，方便用户在暂停后恢复节奏
control_col1, control_col2 = st.columns(2)
if control_col1.button("继续专注", use_container_width=True):
    resume_timer()
    st.rerun()

if control_col2.button("重新开始 25 分钟", use_container_width=True):
    reset_timer()
    st.rerun()

# 倒计时核心逻辑：
# 1. 剩余时间存入 st.session_state，避免页面重跑时被重置
# 2. 使用 time.sleep(1) 控制每秒更新一次
# 3. 使用 st.empty() 对应的占位容器刷新倒计时显示
if st.session_state.is_running and st.session_state.remaining_seconds > 0:
    time.sleep(1)
    st.session_state.remaining_seconds -= 1
    render_timer(timer_placeholder)

    if st.session_state.remaining_seconds == 0:
        st.session_state.is_running = False
        st.session_state.show_emotions = False
        st.rerun()

    st.rerun()
