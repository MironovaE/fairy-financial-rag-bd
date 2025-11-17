import streamlit as st
import os
from utils.chroma_store import ChromaStore


def show():
    # 🔹 Заголовок и кнопка "Выйти" — на одном уровне
    col_title, col_exit = st.columns([6, 1])
    with col_title:
        st.title("🗃 ChromaDB Inspector")
    with col_exit:
        if st.button("🚪 Выйти", key="exit_from_chroma"):
            # Очистка сессии, кроме данных (hero/products остаются — чтобы не грузить заново)
            for key in [
                "user_query", "user_query_input", "eligible_products", "eligible_ids",
                "chroma_loaded_for_eligible", "final_prompt", "llm_response"
            ]:
                st.session_state.pop(key, None)
            st.session_state.screen = "auth"
            st.rerun()

    st.caption("Технический экран: состояние векторного хранилища и данные")

    try:
        chroma_store = ChromaStore()
        collection = chroma_store.collection

        # 🔹 Статус подключения
        is_cloud = "STREAMLIT_CLOUD" in os.environ
        mode = "☁️ In-memory (Streamlit Cloud)" if is_cloud else "💾 Persistent (./chroma_db)"
        st.success(f"✅ Подключение активно | Режим: {mode}")

        # 🔹 Счётчик документов
        try:
            count = chroma_store.collection_count()
        except Exception:
            count = 0
        st.metric("Документов в коллекции", count)

        # 🔹 Пример документа
        if count > 0:
            try:
                sample = collection.peek(limit=1)
                ids = sample.get("ids", [])
                metadatas = sample.get("metadatas", [])
                documents = sample.get("documents", [])

                if ids:
                    doc_id = ids[0]
                    name = metadatas[0].get("name", "—") if metadatas else "—"
                    st.caption(f"✅ Пример продукта в базе: **{name}** (ID: `{doc_id}`)")
                else:
                    st.caption("Коллекция существует, но документов не видно.")
            except Exception as e:
                st.caption(f"⚠️ Ошибка получения примера: {type(e).__name__}")

        # 🔹 Пробный поиск
        if count > 0:
            st.subheader("🔍 Пробный поиск")
            st.caption("Проверьте, как ChromaDB отвечает на реальные запросы")

            query = st.text_input(
                "Введите запрос для теста",
                "Накопить на домик в лесу",
                key="chroma_test_query"
            )

            if st.button("🔎 Найти в ChromaDB", key="chroma_search_btn") and query.strip():
                try:
                    results = chroma_store.query(query_text=query, n_results=3)
                    if results:
                        st.success(f"✅ Найдено {len(results)} похожих продуктов:")
                        for r in results:
                            desc = (r.get("description") or r.get("text") or "").strip()
                            st.markdown(f"- **{r['name']}** → {desc[:120]}…")
                    else:
                        st.warning("⚠️ По вашему запросу ничего не найдено.")
                except Exception as e:
                    st.error(f"❌ Ошибка поиска: {type(e).__name__} — {str(e)[:100]}…")

        # 🔹 Параметры коллекции
        with st.expander("⚙️ Параметры коллекции", expanded=False):
            st.json({
                "name": collection.name,
                "metadata": collection.metadata or {},
                "embedding_function": "paraphrase-multilingual-MiniLM-L12-v2",
                "path": "./chroma_db" if not is_cloud else "in-memory"
            })

        # 🔹 Просмотр данных (только если ≤ 20)
        if 0 < count <= 20:
            st.subheader("📋 Документы в базе")
            try:
                all_data = collection.get(include=["metadatas", "documents"])
                ids = all_data.get("ids", [])
                metadatas = all_data.get("metadatas", [])
                documents = all_data.get("documents", [])

                for i, doc_id in enumerate(ids[:20]):
                    meta = metadatas[i] if i < len(metadatas) else {}
                    doc_text = documents[i] if i < len(documents) else ""
                    name = meta.get("name", "—")

                    with st.expander(f"📄 {doc_id} — {name}", expanded=False):
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            st.markdown("**Метаданные:**")
                            st.json(meta)
                        with col2:
                            st.markdown("**Текст (для эмбеддинга):**")
                            st.text(doc_text[:300] + "..." if len(doc_text) > 300 else doc_text)
            except Exception as e:
                st.error(f"Ошибка чтения документов: {e}")

        elif count > 20:
            st.info(f"📌 В базе {count} документов — полный просмотр отключён. Используйте **пробный поиск**.")

        # 🔹 Управление
        st.divider()
        st.subheader("🛠 Управление")

        col_refresh, col_clear = st.columns([1, 1], gap="small")

        with col_refresh:
            if st.button("🔄 Обновить статус", use_container_width=True, key="chroma_refresh"):
                st.rerun()

        with col_clear:
            if st.button("🗑️ Очистить коллекцию", type="secondary", use_container_width=True, key="chroma_clear"):
                chroma_store.clear_collection()
                st.session_state.pop("chroma_loaded_for_eligible", None)
                st.success("✅ Коллекция очищена. Перейдите в препроцессинг для перезагрузки.")
                st.rerun()

    except Exception as e:
        st.error("❌ ChromaDB недоступна")
        st.code(str(e), language="python")
        st.info("Проверьте: установлен ли `chromadb`, доступна ли директория `./chroma_db`.")

    # 🔹 Навигация
    st.divider()

    col_spacer, col_back, col_next = st.columns([1, 0.3, 0.3])

    with col_back:
        if st.button(
                "⬅️ Вернуться к препроцессингу",
                use_container_width=True,
                key="chroma_back_to_preprocessing"
        ):
            st.session_state.screen = "preprocessing"
            st.rerun()

    with col_next:
        if st.button(
                "➡️ Перейти к RAG-имитации",
                type="primary",
                use_container_width=True,
                key="chroma_to_rag_simulation"
        ):
            st.session_state.screen = "rag_simulation"
            st.rerun()