import streamlit as st

def show():
    st.markdown("### 🔮 Fairy Financial RAG Demo")
    st.markdown(
        """
        Это **архитектурно честный MVP** сказочного RAG-пайплайна  
        для персонализированных финансовых советов в Княжеском банке.

        **Этапы пайплайна:**
        1. Загрузка профиля героя (встроенный или ваш JSON)  
        2. Загрузка финансовых продуктов (встроенные или ваш JSON)  
        3. Фильтрация по бизнес-правилам (`eligibility`) — **до** семантического поиска,  
           как это делают настоящие финансовые системы  
        4. Семантический поиск на основе **реальных эмбеддингов** (`sentence-transformers`),  
           дополненный TF-IDF для отказоустойчивости  
        5. Генерация совета через **Groq** с fallback на мок

        **LLM уже работает:**  
        Бесплатный аккаунт Groq предоставляет до 500 000 токенов и 14 400 запросов в сутки —
        более чем достаточно для демо. При исчерпании лимита
        система незаметно переключается на заглушку. 

        **До production — всего три шага:**
        ▶️ Заменить in-memory поиск на **FAISS/Chroma**  
        ▶️ Добавить **кэширование эмбеддингов продуктов**  
        ▶️ Использовать **LLM с SLA** (Groq уже подходит)

        И при этом — это **живое учебное пособие**:  
        вы пройдёте все этапы, заглянете «под капот»  
        и даже подключите свои данные (героев и продуктов).

        Готовы окунуться в мир магии ИИ вместе с **Сундуком Мудрости** —  
        сказочным финансовым советником Княжеского банка?
        """
    )

    # Стиль для кнопки — внутри функции show()
    st.markdown(
        """
        <style>
        div.stButton > button {
            background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
            color: white;
            font-weight: bold;
            border-radius: 24px;
            padding: 14px 28px;
            font-size: 18px;
            border: none;
            box-shadow: 0 6px 12px rgba(100, 30, 150, 0.3);
            transition: all 0.3s ease;
            width: 100%;
            max-width: 320px;
            margin: 24px auto;
            display: block;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 16px rgba(100, 30, 150, 0.4);
            background: linear-gradient(135deg, #b39ddb 0%, #fcd5ce 100%);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("Начать приключение"):
        st.session_state["screen"] = "data_manager"
        st.rerun()