# screens/rag_simulation.py
import streamlit as st
import os
import torch
from utils.utils import get_address_and_verb
from utils.chroma_store import ChromaStore

# Отключаем GPU (на Streamlit Cloud нет CUDA)
os.environ["CUDA_VISIBLE_DEVICES"] = ""
torch.set_num_threads(1)

# === Твой существующий код — без изменений (эмбеддинги, TF-IDF, keywords) ===
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    pass

TFIDF_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    TFIDF_AVAILABLE = True
except Exception:
    pass

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def filter_with_embeddings(products, query):
    model = load_embedding_model()
    query_emb = model.encode(query, convert_to_tensor=True, show_progress_bar=False)
    product_texts = []
    for p in products:
        text = p.get('text', '').strip()
        if not text:
            text = f"{p['name']}. {p.get('description', '')}"
        product_texts.append(text)
    product_embs = model.encode(product_texts, convert_to_tensor=True, show_progress_bar=False)
    similarities = util.cos_sim(query_emb, product_embs)[0]
    top_k = min(5, len(products))
    top_indices = torch.topk(similarities, k=top_k).indices
    return [products[i] for i in top_indices]

def filter_with_tfidf(products, query):
    product_texts = []
    for p in products:
        text = p.get('text', '').strip()
        if not text:
            text = f"{p['name']}. {p.get('description', '')}"
        product_texts.append(text.lower())
    query_text = query.lower()
    vectorizer = TfidfVectorizer(stop_words=None, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(product_texts + [query_text])
    query_vec = tfidf_matrix[-1]
    product_vecs = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vec, product_vecs).flatten()
    top_indices = np.argsort(similarities)[::-1][:5]
    return [products[i] for i in top_indices if similarities[i] > 0.05]

def filter_with_keywords(products, query):
    query_lower = query.lower()
    saving = ["накопить", "вклад", "сбережения", "мальдив", "мечта", "цель", "копить"]
    credit = ["заем", "кредит", "долг", "срочно", "занять"]
    if any(kw in query_lower for kw in saving):
        return [p for p in products if p.get("type") in ["вклад", "сберегательный счёт", "целевой счёт"]]
    elif any(kw in query_lower for kw in credit):
        return [p for p in products if p.get("type") in ["кредит", "заем"]]
    return products[:5]

# === ⚡ get_relevant_products: Chroma → fallback (без глобальных зависимостей) ===
def get_relevant_products(products, query, eligible_ids=None, chroma_store=None):
    method_log = []

    # 🔹 Уровень 1: ChromaDB
    if chroma_store and eligible_ids is not None:
        try:
            # Защита от None и приведение к строке
            eligible_ids = [str(i) for i in eligible_ids if i is not None]
            if not eligible_ids:
                raise ValueError("No valid IDs")

            method_log.append("ChromaDB")
            results = chroma_store.query(
                query_text=query,
                where={"id": {"$in": eligible_ids}},
                n_results=5
            )
            if results and len(results) > 0:
                return results, " → ".join(method_log)
            else:
                method_log.append("(0)")
        except Exception as e:
            method_log.append(f"(error: {type(e).__name__})")

    # 🔹 Уровень 2: эмбеддинги
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        try:
            res = filter_with_embeddings(products, query)
            method_log.append("эмбеддинги")
            return res, " → ".join(method_log)
        except Exception:
            method_log.append("эмбеддинги (error)")

    # 🔹 Уровень 3: TF-IDF
    if TFIDF_AVAILABLE:
        try:
            res = filter_with_tfidf(products, query)
            method_log.append("TF-IDF")
            return res, " → ".join(method_log)
        except Exception:
            method_log.append("TF-IDF (error)")

    # 🔹 Уровень 4: ключевые слова
    res = filter_with_keywords(products, query)
    method_log.append("ключевые слова")
    return res, " → ".join(method_log)

# === Формирование промпта — с поддержкой Pydantic-объектов ===
def build_rag_prompt(hero, query, relevant_products):
    top_products = relevant_products[:5]
    products_text = "\n".join(
        f"- **{p['name']}**: {p.get('description', 'Описание отсутствует')}"
        for p in top_products
    )
    address, verb = get_address_and_verb(hero)
    # ✅ Точечная нотация для Pydantic
    hero_name = hero.name
    age = hero.age
    income = hero.income
    citizenship = hero.citizenship

    return f"""Ты — Сундук Мудрости, сказочный советник Княжеского банка.

{address.capitalize()}! Ты {verb} с важной финансовой целью: «{query}».
Ты — {hero_name}, возраст {age}, доход {income} золотых, гражданство: {citizenship}.

Доступные релевантные продукты:
{products_text}

Сформулируй тёплый, сказочный, полезный совет в 3–5 предложениях.
Не упоминай реальные бренды, валюты или страны.
Используй образы русских сказок: злато, терема, богатыри, мудрость.
Валюта — только «золотые».

❗ Уважай возраст героя: если возраст > 60 — подчеркни мудрость и опыт.
❗ Сохраняй сказочный тон и обращайся лично."""

# === Основной экран ===
def show():
    # 🔹 Создаём ChromaStore СВЕЖИМ при каждом входе — без кэша!
    chroma_store = None
    chroma_available = False
    try:
        chroma_store = ChromaStore()  # ← без аргументов!
        # Проверка: есть ли хоть один документ?
        if chroma_store.collection_count() >= 0:
            chroma_available = True
            st.session_state.pop("chroma_error", None)
    except Exception as e:
        st.session_state["chroma_error"] = f"{type(e).__name__}: {str(e)}"

    # 🔹 Заголовок и кнопка "Выйти" — на одном уровне
    col_title, col_exit = st.columns([14, 1], vertical_alignment = "bottom")
    with col_title:
        st.title("🧠 RAG: Chroma + fallback chain")
    with col_exit:
        if st.button("🚪 Выйти", key="exit_from_chroma"):
            for key in [
                "card_suffix", "hero", "user_query", "user_query_input",
                "messages", "chat_id"
            ]:
                st.session_state.pop(key, None)
            st.session_state.screen = "auth"
            st.rerun()


    if chroma_available:
        st.success("🟢 ChromaDB активна и участвует в retrieval")
    else:
        err = st.session_state.get("chroma_error", "неизвестная причина")
        st.warning(f"🟠 ChromaDB недоступна → используется резервный pipeline ({err})")

    st.markdown("""
    Теперь retrieval использует **ChromaDB как первый и предпочтительный метод**, но сохраняет полную отказоустойчивость.
    """)

    hero = st.session_state["hero"]
    query = st.session_state.get("user_query", "Не указана")
    eligible_products = st.session_state["eligible_products"]
    eligible_ids = [p["id"] for p in eligible_products]

    # 🔹 Запуск retrieval
    relevant_products, method = get_relevant_products(
        products=eligible_products,
        query=query,
        eligible_ids=eligible_ids,
        chroma_store=chroma_store if chroma_available else None
    )
    st.success(f"✅ Отобрано {len(relevant_products)} продуктов (метод: **{method}**).")

    with st.expander("📦 Релевантные продукты (ТОП-5)", expanded=True):
        for p in relevant_products[:5]:
            st.markdown(f"**{p['name']}** — {p.get('description', 'Описание отсутствует')}")

    prompt = build_rag_prompt(hero, query, relevant_products)
    st.subheader("📜 Сформированный промпт для LLM")
    st.code(prompt, language="text")
    st.info("Этот промпт будет отправлен в языковую модель.")


    # 🔹 Кнопки навигации
    st.divider()

    col_spacer, col_back, col_next = st.columns([1,0.3,0.2], gap="small")

    with col_back:
        if st.button("⬅️ Вернуться к ChromaDB Inspector", use_container_width=True, key="back_to_preprocessing"):
            st.session_state["screen"] = "chroma_inspector"
            st.rerun()

    with col_next:
        if st.button("➡️ Отправить в LLM", type="primary", use_container_width=True, key="to_llm"):
            st.session_state["final_prompt"] = prompt
            st.session_state["screen"] = "llm_response"
            st.rerun()