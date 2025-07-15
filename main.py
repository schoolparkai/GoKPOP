import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from PIL import Image

# 이미지 경로
image_path = "assets/formula.png"

# 이미지 열기
image = Image.open(image_path)


# 초기 관리자 데이터 (예시 데이터)
def load_data():
    data = {
        "날짜": [
            "2025-07-10", "2025-07-11", "2025-07-12",
            "2025-07-13", "2025-07-14"
        ],
        "창작성 판단지수": [42.5, 45.3, 48.7, 50.2, 52.6]
    }
    df = pd.DataFrame(data)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df

# Streamlit 앱 시작
st.set_page_config(page_title="임영웅 창작성 판단기", layout="centered")
col_logo, col_text = st.columns([1, 6])
with col_logo:
    st.image("assets/yonsei_logo.png", width=65)
with col_text:
    st.markdown("<p style='margin: 0; font-size: 16px;'>본 페이지는 연세대학교 인문학예술진흥사업단의 제작 지원을 받아 제작되었습니다.</p>", unsafe_allow_html=True)
    st.markdown("<p style='margin: 0; font-size: 14px;'>@yonsei-humanart 유튜브 채널에서 더 많은 영상을 확인해보세요.</p>", unsafe_allow_html=True)
st.markdown("""
    <hr style='border: none; border-top: 3px dashed #f39c12; margin-bottom: 14px;'>
<div class='fireworks-bg' style='text-align: center; background: radial-gradient(circle at top left, #ffe5ec, #ffc9de, #f9a8d4); padding: 30px 20px; border-radius: 22px; animation: pulse 4s infinite, glow 3s ease-in-out infinite; box-shadow: 0 0 30px #f8bbd0;'>
    <h1 style='font-size: 42px; margin-bottom: 10px; color: #4a148c; text-shadow: 1px 1px 2px white;'>임영웅</h1>
    <h1 style='font-size: 38px; margin-top: 0; color: #880e4f; text-shadow: 1px 1px 2px white;'>&lt;사랑해요 그대를&gt; 창작성 판단기</h1>
</div>
<hr style='border: none; border-top: 3px dashed #f39c12; margin-top: 14px;'>
<style>
@keyframes explode {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.08); opacity: 0.75; }
    100% { transform: scale(1); opacity: 1; }
}
@keyframes pulse {
    0% { box-shadow: 0 0 5px #f8bbd0; }
    50% { box-shadow: 0 0 25px #f06292; }
    100% { box-shadow: 0 0 5px #f8bbd0; }
}
@keyframes fireworks {
    0% { background-position: 0 0; }
    100% { background-position: 1000px 0; }
}
.fireworks-bg {
    background-image: radial-gradient(circle, #ffcc00 1px, transparent 1px), radial-gradient(circle, #ff6699 1px, transparent 1px);
    background-size: 20px 20px;
    animation: fireworks 10s linear infinite;
    border: 3px double #ff4081;
    border-radius: 18px;
}
@keyframes glow {
    0% { box-shadow: 0 0 10px #f06292, 0 0 20px #f48fb1; }
    50% { box-shadow: 0 0 25px #ec407a, 0 0 40px #f06292; }
    100% { box-shadow: 0 0 10px #f06292, 0 0 20px #f48fb1; }
}
</style>
""", unsafe_allow_html=True)
st.markdown("<h2 style='font-size: 32px;'>창작과 감동, 데이터로 함께 분석해 봅시다!</h2>", unsafe_allow_html=True)

# 데이터 불러오기 및 표시
df = load_data()

# 사용자 입력창
st.markdown("<h3 style='font-size: 30px;'>📥 수치를 입력해 주세요</h3>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown("<p style='font-size:24px;'>👁️ 조회수</p>", unsafe_allow_html=True)
    views = st.number_input("Views", min_value=1, value=1000, format="%d", key="views")

    st.markdown("<p style='font-size:24px;'>🙋‍♀️ 구독자 수</p>", unsafe_allow_html=True)
    subscribers = st.number_input("Subscribers", min_value=1, value=500, format="%d", key="subs")

with col2:
    st.markdown("<p style='font-size:24px;'>❤️ 좋아요 수</p>", unsafe_allow_html=True)
    likes = st.number_input("Likes", min_value=0, value=300, format="%d", key="likes")
    creativity_ratio = 26.6  # 고정된 창안구 비율

    st.markdown(f"""
        <div style='border: 2px solid #999; border-radius: 16px; padding: 20px; margin-top: 30px; background: linear-gradient(145deg, #f4f4f4, #e8e8e8); text-align: center; width: 100%; transition: transform 0.3s ease-in-out;'>
            <p style='font-size: 20px; margin-bottom: 4px;'>💡 창안구의 비율</p>
            <p style='font-size: 36px; font-weight: bold; color: #004488;'>{creativity_ratio}%</p>
        </div>
    """, unsafe_allow_html=True)

# 점수 계산
impact_score = (likes / views) * 100
loyalty_score = (likes / subscribers) * 100
if loyalty_score > 100:
    loyalty_score = 100

# 총점 계산 (40% + 40% + 20%)
total_score = round((creativity_ratio * 0.4) + (impact_score * 0.4) + (loyalty_score * 0.2), 2)


# 등급 및 설명
if total_score >= 80:
    level = "🔵 매우 높음 - 창작 표현이 풍부하고 대중의 반응도 매우 뜨겁습니다."
elif total_score >= 60:
    level = "🟢 높음 - 신선한 표현이 많고 수용자에게도 잘 받아들여졌습니다."
elif total_score >= 40:
    level = "🟡 준수 - 익숙한 표현 속에서도 창의성이 어느 정도 돋보입니다."
elif total_score >= 20:
    level = "🟠 보통 - 대체로 관습적인 표현이 많지만 일부 창의적 시도가 있습니다."
else:
    level = "🔴 낮음 - 대부분 익숙한 표현으로 구성되어 있습니다."

# 결과 출력
st.markdown("---")
st.markdown(f"<h2 style='font-size: 32px;'>📊 창작성 판단지수: {total_score}점</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='font-size: 24px;'>{level}</p>", unsafe_allow_html=True)
st.progress(min(int(total_score), 100))

# 오늘 날짜와 점수를 기존 데이터에 추가
today = datetime.datetime.now().date()
new_row = pd.DataFrame({"날짜": [today], "창작성 판단지수": [total_score]})
df_updated = pd.concat([df, new_row], ignore_index=True)

import matplotlib.font_manager as fm


# 그래프 출력
st.markdown("<h3 style='font-size: 30px;'>📈 창작성 판단지수 변화 추이 ⏳</h3>", unsafe_allow_html=True)
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df_updated["날짜"], df_updated["창작성 판단지수"], marker='o')
ax.set_title("Creativity Score Trend by Date", fontsize=18)
ax.set_xlabel("Date", fontsize=16)
ax.set_ylabel("Score", fontsize=16)
ax.set_ylim(0, 100)
plt.xticks(rotation=45, fontsize=14)
plt.yticks(fontsize=14)
st.pyplot(fig)

# 창작성 판단지수 공식/ 전체 너비를 사용하여 출력
st.image(image, use_container_width=True)

# 유튜브 영상 표시
st.markdown("---")
st.markdown("<h3 style='font-size: 30px;'>🎧 지금 바로 감상해보세요!</h3>", unsafe_allow_html=True)
st.video("https://www.youtube.com/watch?v=XGf2PO4rHzU")
st.markdown("<p style='font-size: 22px;'>※ 본 결과는 수치 기반의 창작성 해석 예시입니다.</p>", unsafe_allow_html=True)
