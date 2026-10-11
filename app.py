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


def normalizar(text
