"""Verified legacy branding and official performance media, separate from E2."""
from pathlib import Path
import base64
import hashlib
import streamlit as st

CHANNEL = 'https://www.youtube.com/@yonsei-humanart'
INSTITUTION = '연세대학교 인문예술진흥사업단'
SUPPORT_TEXT = '본 페이지는 연세대학교 인문예술진흥사업단의 제작 지원을 받아 제작되었습니다.'
CHANNEL_TEXT = '@yonsei-humanart 유튜브 채널에서 더 많은 영상을 확인해보세요.'
LOGO_PATH = 'assets/yonsei_logo.png'
LOGO_SHA256 = '95ae2d1470cbcd84f8125e169b655166c346d22639e71f4c7e9619c6158e2df4'
PERFORMANCE_ID = 'XGf2PO4rHzU'
PERFORMANCE_URL = 'https://www.youtube.com/watch?v=' + PERFORMANCE_ID
THUMBNAIL_URL = 'https://i.ytimg.com/vi/' + PERFORMANCE_ID + '/maxresdefault.jpg'


def support_banner(root):
    try:
        raw = (Path(root) / LOGO_PATH).read_bytes()
        if hashlib.sha256(raw).hexdigest() != LOGO_SHA256:
            raise ValueError('로고 원본과 다릅니다.')
    except (OSError, ValueError):
        st.warning('제작 지원 로고를 확인할 수 없습니다.')
        return
    encoded = base64.b64encode(raw).decode('ascii')
    st.markdown(f'''<div class="support-banner"><a class="support-logo" href="{CHANNEL}" target="_blank" rel="noopener noreferrer" aria-label="연세 인문학 아케이드 채널 열기"><img src="data:image/png;base64,{encoded}" alt="연세 인문학 아케이드 원본 로고"></a><div><p>{SUPPORT_TEXT}</p><a class="support-channel" href="{CHANNEL}" target="_blank" rel="noopener noreferrer">{CHANNEL_TEXT}</a></div></div>''', unsafe_allow_html=True)


def performance_video():
    st.header('지금 바로 감상해보세요!', anchor=False)
    st.video(PERFORMANCE_URL, autoplay=False)
    st.link_button('YouTube에서 감상하기 ↗', PERFORMANCE_URL, width='stretch')
    st.caption('임영웅 공식 공연 영상 · 점수에 사용한 원곡 Art Track과는 별개의 영상입니다.')
