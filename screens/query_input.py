import streamlit as st


def show():
    hero = st.session_state.get("hero")
    # Защита: если герой не загружен — показываем дефолт
    hero_name = hero.name if hero else "добрый путник"

    # 🔹 Заголовок и кнопка "Выйти" — единообразно ([6, 1], без vertical_alignment)
    col_title, col_exit = st.columns([6, 1])
    with col_title:
        st.title("🏦 Сундук Мудрости")
    with col_exit:
        if st.button("🚪 Выйти", key="exit_from_query"):
            # Очищаем только сессионные данные, связанные с текущим диалогом
            for key in [
                "hero", "user_query", "user_query_input"
            ]:
                st.session_state.pop(key, None)
            st.session_state.screen = "auth"
            st.rerun()

    st.caption("*Сказочный финансовый советник Княжеского банка*")

    st.markdown(
        f"🌟 **Приветствуем тебя, {hero_name}!**  \n"
        "Добро пожаловать в Княжеский банк — место, где золотые мечты превращаются в реальность!",
        unsafe_allow_html=False  # ← можно без HTML
    )

    st.divider()

    query = st.text_area(
        "Задайте свой вопрос Сундуку Мудрости:",
        placeholder="Например: «Как накопить на терем на Мальдивах за 2 месяца?»",
        height=100,
        key="query_input_textarea"
    ).strip()

    # 🔹 Кнопка отправки — компактно, в правом углу
    st.divider()
    col_spacer, col_submit = st.columns([1, 0.25], gap="small")

    with col_submit:
        if st.button(
                "➤ Получить совет",
                type="primary",
                use_container_width=True,
                key="query_submit"
        ):
            if not query:
                st.error("❗ Пожалуйста, напишите свой вопрос.")
                return

            st.session_state["user_query"] = query
            st.session_state["screen"] = "preprocessing"
            st.rerun()