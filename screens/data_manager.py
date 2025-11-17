"""
🗃 Data Manager — enterprise-grade загрузка и валидация данных.
Поддержка:
- Демо-режим (автозагрузка демо-данных из demo_data/)
- Кастомные данные (загрузка heroes.json и products.json)
"""

import streamlit as st
import json
from pathlib import Path
from models import Hero, Product
from typing import List, Dict, Any


def load_demo_data() -> tuple[List[Hero], List[Product], List[Dict[str, Any]]]:
    """Загружает демо-данные. Возвращает героев (Pydantic), продукты (Pydantic), продукты (dict)."""
    base_dir = Path(__file__).parent.parent

    with open(base_dir / "demo_data" / "heroes.json", encoding="utf-8") as f:
        raw_heroes = json.load(f)
    heroes = [Hero.model_validate(h) for h in raw_heroes]

    with open(base_dir / "demo_data" / "products.json", encoding="utf-8") as f:
        raw_products = json.load(f)
    products = [Product.model_validate(p) for p in raw_products]

    return heroes, products, raw_products


def show():
    st.title("🗃 Управление данными")

    # 🔹 Этап 1: выбор режима
    if "data_mode" not in st.session_state:
        st.subheader("Выберите источник данных")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧙‍♂️ Демо-режим", type="primary", use_container_width=True, key="btn_demo"):
                st.session_state.data_mode = "demo"
                st.rerun()
        with col2:
            if st.button("🧾 Свои данные", use_container_width=True, key="btn_custom"):
                st.session_state.data_mode = "custom"
                st.rerun()
        return

    # 🔹 Этап 2: демо-режим
    if st.session_state.data_mode == "demo":
        if "data_loaded" not in st.session_state:
            try:
                heroes, products, raw_products = load_demo_data()

                st.session_state.heroes = heroes
                st.session_state.products = products
                st.session_state.products_data = raw_products  # ← для Chroma/RAG

                st.session_state.data_loaded = True
                st.session_state.ready_for_auth = True

                st.success("✅ Демо-данные загружены и проверены.")
                st.info(f"🎭 Герои: {len(heroes)} · 💰 Продукты: {len(products)}")

            except FileNotFoundError as e:
                st.error("❌ Файл не найден")
                st.code(f"{e}", language="text")
                st.caption("Убедитесь, что папка `demo_data/` существует и содержит `heroes.json`, `products.json`.")
                return
            except json.JSONDecodeError as e:
                st.error("❌ Некорректный JSON")
                st.code(f"{e}", language="text")
                return
            except Exception as e:
                st.error(f"❌ Ошибка загрузки: {type(e).__name__}")
                st.exception(e) if st.session_state.get("debug") else None
                return

    # 🔹 Этап 3: кастомный режим
    elif st.session_state.data_mode == "custom":
        st.subheader("🧾 Загрузка собственных данных")
        st.markdown("Для работы необходимы **оба файла**: `heroes.json`, `products.json`.")

        with st.expander("📋 Требования к heroes.json", expanded=bool(st.session_state.get("heroes_error"))):
            st.markdown("""
            **Обязательные поля:**
            | Поле | Тип | Ограничения |
            |------|-----|-------------|
            | `card_suffix` | str | 4 цифры |
            | `name` | str | не пустая |
            | `age` | int | 0–200 |
            | `income` | int | ≥0 |
            | `citizenship` | str | не пустая |
            | `gender` | str | `"мужской"`/`"женский"` |
            """)

        with st.expander("📋 Требования к products.json", expanded=bool(st.session_state.get("products_error"))):
            st.markdown("""
            **Обязательные поля:**  
            `id`, `name`, `type`, `min_amount`, `term_months`,  
            `interest_rate`, `currency`, `description`, `text`, `eligibility`.
            """)

        col1, col2 = st.columns(2)
        with col1:
            uploaded_heroes = st.file_uploader("🎭 heroes.json", type=["json"], key="uploader_heroes")
        with col2:
            uploaded_products = st.file_uploader("💰 products.json", type=["json"], key="uploader_products")

        heroes_valid = products_valid = False

        # 🔹 Валидация героев
        if uploaded_heroes:
            try:
                raw_heroes = json.load(uploaded_heroes)
                heroes = [Hero.model_validate(h) for h in raw_heroes]
                st.session_state.heroes = heroes
                heroes_valid = True
                st.session_state.pop("heroes_error", None)
                st.success(f"✅ Герои: {len(heroes)}")
            except (json.JSONDecodeError, ValueError) as e:
                st.error("❌ Некорректный JSON или нарушена валидация")
                st.session_state.heroes_error = True
            except Exception as e:
                st.error(f"❌ Ошибка: {type(e).__name__}")
                st.session_state.heroes_error = True

        # 🔹 Валидация продуктов
        if uploaded_products:
            try:
                raw_products = json.load(uploaded_products)
                products = [Product.model_validate(p) for p in raw_products]
                st.session_state.products = products
                st.session_state.products_data = raw_products
                products_valid = True
                st.session_state.pop("products_error", None)
                st.success(f"✅ Продукты: {len(products)}")
            except (json.JSONDecodeError, ValueError) as e:
                st.error("❌ Некорректный JSON или нарушена валидация")
                st.session_state.products_error = True
            except Exception as e:
                st.error(f"❌ Ошибка: {type(e).__name__}")
                st.session_state.products_error = True

        # 🔹 Готовность к переходу
        st.session_state.ready_for_auth = heroes_valid and products_valid

    # 🔹 Навигация
    st.divider()
    col_spacer, col_back, col_next = st.columns([1, 0.3, 0.35], gap="small")

    with col_back:
        if st.button(
                "↩️ Назад к выбору режима",
                use_container_width=True,
                key="dm_back_to_mode"
        ):
            # Удаляем ВСЁ, связанное с данным этапом
            keys_to_clear = [
                "data_mode", "upload_step", "heroes", "products",
                "products_data", "data_loaded", "ready_for_auth",
                "heroes_error", "products_error"
            ]
            for k in keys_to_clear:
                st.session_state.pop(k, None)
            st.rerun()

    with col_next:
        if st.session_state.get("ready_for_auth"):
            if st.button(
                    "➡️ Продолжить к авторизации",
                    type="primary",
                    use_container_width=True,
                    key="dm_continue_to_auth"
            ):
                st.session_state.screen = "auth"
                st.rerun()