import streamlit as st
from models import Hero
from typing import List, Optional


def find_hero_by_suffix(heroes: List[Hero], suffix: str) -> Optional[Hero]:
    """Возвращает героя по последним 4 цифрам карты, или None."""
    for hero in heroes:
        if hero.card_suffix == suffix:
            return hero
    return None


def show():
    st.title("🏦 Сундук Мудрости")
    st.caption("*Сказочный финансовый советник Княжеского банка*")
    st.subheader("🔑 Авторизация")

    heroes: List[Hero] = st.session_state.get("heroes", [])

    # 🔹 Список героев (только если есть данные)
    if heroes:
        with st.expander("📖 Доступные герои", expanded=False):
            for hero in heroes:
                st.text(f"{hero.card_suffix} — {hero.name}, {hero.age} л., {hero.income} зл., {hero.citizenship}")

    # 🔹 Ввод
    card_suffix = st.text_input(
        "Последние 4 цифры карты:",
        max_chars=4,
        placeholder="Например: 1357",
        key="auth_card_input"
    ).strip()

    # 🔹 Вход
    if st.button("Войти", type="primary", use_container_width=True, key="auth_submit"):
        if not card_suffix.isdigit() or len(card_suffix) != 4:
            st.error("❗ Введите ровно 4 цифры.")
            return

        hero = find_hero_by_suffix(heroes, card_suffix)

        if not hero:
            # 🧩 Герой-заглушка
            hero = Hero(
                card_suffix=card_suffix,
                name="Добрый путник",
                age=18,
                income=0,
                citizenship="Княжество",
                gender="мужской",
                traits="Герой не найден в базе"
            )

        st.session_state["hero"] = hero
        st.session_state["screen"] = "query_input"
        st.rerun()