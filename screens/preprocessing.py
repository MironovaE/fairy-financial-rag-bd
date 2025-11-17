# screens/preprocessing.py
import streamlit as st
import os
from typing import List, Dict, Any
from models import Hero
from utils.chroma_store import ChromaStore

# 🔹 Кэширование ресурса — создаётся один раз на сессию
@st.cache_resource
def get_chroma_store():
    # Гарантируем, что папка существует — критично для Cloud
    os.makedirs("chroma_db", exist_ok=True)
    return ChromaStore()


def filter_products_by_profile(products: List[Dict[str, Any]], hero: Hero) -> List[Dict[str, Any]]:
    """Фильтрует продукты по профилю героя: возраст, доход, гражданство."""
    filtered = []
    for p in products:
        eligibility = p.get("eligibility", {})
        min_age = eligibility.get("min_age")
        max_age = eligibility.get("max_age")
        min_income = eligibility.get("min_income")
        citizenship_allowed = eligibility.get("citizenship_allowed")

        # Возраст
        if min_age is not None and hero.age < min_age:
            continue
        if max_age is not None and hero.age > max_age:
            continue

        # Доход
        if min_income is not None and hero.income < min_income:
            continue

        # Гражданство
        if citizenship_allowed:
            allowed = citizenship_allowed if isinstance(citizenship_allowed, list) else [citizenship_allowed]
            if hero.citizenship not in allowed:
                continue

        filtered.append(p)
    return filtered


def ensure_eligibility_defaults(product: Dict[str, Any]) -> None:
    """Гарантирует наличие базовых полей в eligibility (in-place)."""
    el = product.setdefault("eligibility", {})
    el.setdefault("min_age", 0)
    el.setdefault("max_age", 999)
    el.setdefault("min_income", 0)


def show():
    # 🔹 Защита от некорректного входа
    if "hero" not in st.session_state or "products_data" not in st.session_state:
        st.error("⚠️ Отсутствуют данные. Пройдите этапы по порядку.")
        st.stop()

    hero: Hero = st.session_state["hero"]
    query = st.session_state.get("user_query", "Не указана")
    products: List[Dict[str, Any]] = st.session_state["products_data"]

    # 🔹 Заголовок и кнопка "Выйти"
    col_title, col_exit = st.columns([6, 1])
    with col_title:
        st.title("⚙️ Препроцессинг: отбор подходящих продуктов")
    with col_exit:
        if st.button("🚪 Выйти", key="exit_from_preprocessing"):
            # Очищаем только сессионные данные, кроме heroes/products
            for key in [
                "hero", "user_query", "user_query_input", "eligible_products",
                "eligible_ids", "chroma_loaded_for_eligible"
            ]:
                st.session_state.pop(key, None)
            st.session_state.screen = "auth"
            st.rerun()

    st.caption(
        "Подготовка списка финансовых продуктов, которые:\n"
        "- **Физически доступны герою** по его профилю (возраст, доход, гражданство),\n"
        "- **Будут использоваться дальше** в RAG-имитации."
    )

    # 🔹 Профиль героя
    st.subheader("👤 Профиль героя")
    profile_cols = st.columns(2)
    with profile_cols[0]:
        st.markdown(f"**Имя:** {hero.name}")
        st.markdown(f"**Возраст:** {hero.age} лет")
        st.markdown(f"**Доход:** {hero.income} золотых")
        st.markdown(f"**Гражданство:** {hero.citizenship}")
    with profile_cols[1]:
        st.markdown(f"**Карта (последние 4):** {hero.card_suffix}")
        st.markdown(f"**Социальный удел:** {hero.traits or '—'}")
        st.markdown(f"**🎯 Запрос:** _«{query}»_")
        st.markdown(f"**📦 Всего продуктов:** {len(products)}")

    # 🔹 Фильтрация
    eligible = filter_products_by_profile(products, hero)
    st.session_state["eligible_products"] = eligible
    st.session_state["eligible_ids"] = [p["id"] for p in eligible]  # id уже str (по Pydantic)

    # 🔹 Загрузка в ChromaDB
    st.subheader("💾 ChromaDB: загрузка подходящих продуктов")

    need_reload = st.session_state.get("chroma_loaded_for_eligible") != len(eligible)

    if need_reload:
        with st.status("⏳ Подготовка и загрузка в ChromaDB...", expanded=True) as status:
            try:
                chroma_store = get_chroma_store()  # ← кэшированный, безопасный
                status.update(label="🔹 Очистка коллекции...")
                chroma_store.clear_collection()

                # 3. Загрузка
                if eligible:
                    status.update(label=f"🔹 Подготовка {len(eligible)} продуктов...")
                    # Гарантируем наличие полей
                    for p in eligible:
                        ensure_eligibility_defaults(p)

                    status.update(label="🔹 Загрузка в ChromaDB...")
                    chroma_store.upsert_products(eligible)

                    count = chroma_store.collection_count()
                    status.update(label=f"✅ Успешно: {count} документов", state="complete")
                    st.success(f"✅ ChromaDB: загружено {len(eligible)} продуктов → в коллекции: {count}")
                    st.session_state["chroma_loaded_for_eligible"] = len(eligible)
                else:
                    status.update(label="⚠️ Нет подходящих продуктов", state="complete")
                    st.warning("⚠️ ChromaDB: 0 документов — нет подходящих продуктов.")
                    st.session_state["chroma_loaded_for_eligible"] = 0

            except Exception as e:
                status.update(label=f"❌ Ошибка: {type(e).__name__}", state="error")
                if st.session_state.get("debug", False):
                    st.exception(e)
                else:
                    st.error(f"🟠 ChromaDB: {type(e).__name__}: {str(e)}")
    else:
        # ✅ Уже загружено
        st.success(f"✅ ChromaDB: данные уже загружены ({len(eligible)} продуктов)")
        st.caption("ℹ️ Чтобы перезагрузить — нажмите «Очистить коллекцию» в ChromaDB Inspector")

    # 🔹 Итоги
    excluded = len(products) - len(eligible)
    st.success(f"✅ Отобрано {len(eligible)} продуктов по профилю героя.")
    if excluded:
        st.warning(f"⚠️ Исключено {excluded} по бизнес-ограничениям.")

    with st.expander("📋 Список отобранных продуктов", expanded=False):
        for p in eligible:
            st.markdown(f"- **{p['name']}**")

    # 🔹 Навигация
    st.divider()
    col_spacer, col_back, col_next = st.columns([1, 0.25, 0.35], gap="small")

    with col_back:
        if st.button(
                "⬅️ Вернуться к вопросу",
                use_container_width=True,
                key="preprocessing_back_to_query"
        ):
            for key in ["user_query", "user_query_input", "eligible_products", "eligible_ids"]:
                st.session_state.pop(key, None)
            st.session_state.screen = "query_input"
            st.rerun()

    with col_next:
        if st.button(
                "➡️ Перейти к ChromaDB Inspector",
                type="primary",
                use_container_width=True,
                key="preprocessing_to_chroma"
        ):
            st.session_state.screen = "chroma_inspector"
            st.rerun()