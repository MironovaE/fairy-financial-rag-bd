# streamlit run app.py
import streamlit as st

# Настройка страницы — ДО ВСЕХ ОСТАЛЬНЫХ ИМПОРТОВ
st.set_page_config(
    page_title="🧙 Сундук Мудрости | Fairy Financial RAG",
    page_icon="🧙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Debug-режим через ?debug=1 (например: ?debug=1)
st.session_state["debug"] = st.query_params.get("debug") == "1"

# Импорты экранов — ленивые, чтобы избежать циклических зависимостей и ускорить старт
def get_screen_handler(screen: str):
    """Возвращает функцию отображения экрана по имени. Lazy import."""
    screen_map = {
        "intro": "screens.intro",
        "data_manager": "screens.data_manager",
        "auth": "screens.auth",
        "query_input": "screens.query_input",
        "preprocessing": "screens.preprocessing",
        "chroma_inspector": "screens.chroma_inspector",
        "rag_simulation": "screens.rag_simulation",
        "llm_response": "screens.llm_response",
    }
    if screen not in screen_map:
        raise ValueError(f"Неизвестный экран: {screen}")

    module = __import__(screen_map[screen], fromlist=["show"])
    return getattr(module, "show")


def main():
    # 🔹 Инициализация состояния навигации
    if "screen" not in st.session_state:
        st.session_state.screen = "intro"

    current_screen = st.session_state.screen

    try:
        # Получаем и вызываем обработчик экрана
        handler = get_screen_handler(current_screen)
        handler()
    except ValueError as e:
        st.error(f"❌ Ошибка навигации: {e}")
        st.session_state.screen = "intro"
        st.rerun()
    except Exception as e:
        # Критическая ошибка в экране — не скрываем, но даём возможность восстановиться
        st.error(f"💥 Критическая ошибка в экране `{current_screen}`: `{type(e).__name__}`")
        if st.button("🏠 Вернуться на главную"):
            st.session_state.screen = "intro"
            st.rerun()
        # Безопасный вывод ошибки: только при debug=1 — полный трейс
        if st.session_state.get("debug", False):
            st.exception(e)
        else:
            st.code(str(e), language="text")


if __name__ == "__main__":
    main()