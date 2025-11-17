# utils/config.py
import streamlit as st
from typing import Optional

def get_groq_api_key() -> Optional[str]:
    """Безопасно получает GROQ_API_KEY из secrets или session_state."""
    # 1. Сначала из session_state (например, введённый пользователем)
    if api_key := st.session_state.get("GROQ_API_KEY"):
        return api_key

    # 2. Затем из secrets — но защищённо
    try:
        return st.secrets["GROQ_API_KEY"]
    except (FileNotFoundError, KeyError, AttributeError):
        return None