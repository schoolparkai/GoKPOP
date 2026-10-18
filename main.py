"""GOKPOP 2.0 Community Cloud entry point."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
import streamlit as st
from gokpop_public.ui import render
st.set_page_config(page_title='GOKPOP 2.0 · 함께 읽는 노래', page_icon='📖', layout='centered', initial_sidebar_state='collapsed')
render(ROOT)
