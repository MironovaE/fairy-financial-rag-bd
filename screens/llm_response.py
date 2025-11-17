import streamlit as st
from groq import Groq
from utils.utils import get_address_and_verb
from utils.config import get_groq_api_key


def call_groq(prompt: str, api_key: str) -> str:
    """Выполняет запрос к Groq. Предполагается, что api_key валиден."""
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
            stream=False,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        st.session_state.setdefault("llm_errors", []).append(str(e))
        return (
            "⚠️ Сундук Мудрости не смог связаться с волшебным кристаллом Groq.\n\n"
            "Но не отчаивайся! Вот мудрый совет от самого Сундука:"
        )


def mock_response(hero, query: str) -> str:
    address, verb = get_address_and_verb(hero)
    eligible_products = st.session_state.get("eligible_products", [])

    base = (
        f"{address.capitalize()}! Ты {verb} с важным вопросом: «{query}». "
        "Увы, волшебный кристалл Groq сегодня устал. Но не беда! "
        "Сундук Мудрости всегда найдёт выход."
    )

    if eligible_products:
        product = eligible_products[0]
        suggestion = (
            f"\n\n👆 Вот мой мудрый совет:\n"
            f"**{product['name']}** — {product.get('description', 'то, что тебе нужно')}."
        )
    else:
        suggestion = (
            "\n\nПока я не нашёл продуктов, подходящих под твой профиль. "
            "Попробуй уточнить цель — например: «Хочу накопить на терем» или «Нужен заем на коня»."
        )

    return f"{base}{suggestion}\n\nА если хочешь больше — обратись к Князю, он всезнающ и мудр.✨"


def show():
    # 🔹 Заголовок и кнопка "Выйти"
    col_title, col_exit = st.columns([6, 1])
    with col_title:
        st.title("🧙 Сундук Мудрости отвечает")
    with col_exit:
        if st.button("🚪 Выйти", key="exit_from_llm"):
            for key in [
                "hero", "user_query", "user_query_input", "eligible_products",
                "eligible_ids", "chroma_loaded_for_eligible", "final_prompt", "llm_response"
            ]:
                st.session_state.pop(key, None)
            st.session_state.screen = "auth"
            st.rerun()

    hero = st.session_state["hero"]
    query = st.session_state.get("user_query", "Не указана")

    st.markdown(f"**Герой:** {hero.name}")
    st.markdown(f"**Цель:** _«{query}»_")
    st.divider()

    # 🔹 Генерация ответа (только один раз)
    if "llm_response" not in st.session_state:
        with st.spinner("Сундук Мудрости обращается к волшебному кристаллу Groq..."):
            prompt = st.session_state["final_prompt"]

            # 🔑 Получаем ключ БЕЗОПАСНО
            api_key = get_groq_api_key()

            if not api_key:
                # ❌ Ключ не задан — даём понятную инструкцию
                response = (
                    "🗝️ **GROQ_API_KEY не настроен**\n\n"
                    "Чтобы Сундук Мудрости мог обратиться к волшебному кристаллу Groq, "
                    "необходим API-ключ. Вы можете:\n\n"
                    "- 📁 Создать файл `.streamlit/secrets.toml` в корне проекта:\n"
                    "  ```toml\n"
                    "  GROQ_API_KEY = \"ваш_ключ_здесь\"\n"
                    "  ```\n"
                    "- 🌐 Получить бесплатный ключ на [console.groq.com](https://console.groq.com/keys)\n"
                    "- ➕ Добавить экран ввода ключа (в будущем)\n\n"
                )
                st.session_state["llm_response"] = response + mock_response(hero, query)
            else:
                # ✅ Ключ есть — вызываем Groq
                try:
                    response = call_groq(prompt, api_key)
                    # Дополняем моком, если ответ пустой или ошибка
                    if not response or response.startswith("⚠️"):
                        response = response.rstrip() + "\n\n" + mock_response(hero, query)
                    st.session_state["llm_response"] = response
                except Exception as e:
                    # Редкий случай: ошибка в call_groq при валидном ключе
                    fallback = mock_response(hero, query)
                    st.session_state["llm_response"] = f"⚠️ Неожиданная ошибка: {type(e).__name__}\n\n{fallback}"

    # 🔹 Отображение
    st.subheader("💬 Совет Сундука Мудрости")
    st.markdown(f"> {st.session_state['llm_response']}")

    # 🔹 Навигация
    st.divider()
    col_spacer, col_back, col_restart = st.columns([1, 0.25, 0.25], gap="small")

    with col_back:
        if st.button("⬅️ Вернуться к RAG", use_container_width=True, key="llm_back_to_rag"):
            st.session_state.screen = "rag_simulation"
            st.rerun()

    with col_restart:
        if st.button("🔄 Начать заново", use_container_width=True, key="llm_restart_flow"):
            st.session_state.clear()
            st.rerun()