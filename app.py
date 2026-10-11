import html
import re
import unicodedata
from datetime import date, datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="TAPPAD Radar",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


def normalizar(text):
    if not text:
        return ""
    text = str(text).lower().strip()
    reemplazos = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
    for a, b in reemplazos:
        text = text.replace(a, b)
    return text
