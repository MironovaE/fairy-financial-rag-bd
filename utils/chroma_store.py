import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional, Any
import os
import logging

# Настройка логгера (опционально, но для продакшена — must-have)
logger = logging.getLogger(__name__)


class ChromaStore:
    """
    Обёртка над ChromaDB для fairy-financial-rag.
    Поддерживает:
    - persistent-режим (локально) и in-memory (Streamlit Cloud),
    - безопасную загрузку продуктов,
    - отказоустойчивый query и очистку.
    """

    def __init__(self):
        # Определяем режим: persistent (локально) vs in-memory (облако)
        is_cloud = "STREAMLIT_CLOUD" in os.environ
        persist_dir = None if is_cloud else "./chroma_db"

        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()

        # Создаём/получаем коллекцию
        self.collection = self.client.get_or_create_collection(
            name="fairy_products",
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu"
            ),
            metadata={"hnsw:space": "cosine"}
        )

    @staticmethod
    def _prepare_metadata(product: Dict[str, Any]) -> Dict[str, Any]:
        """Готовит метаданные продукта для Chroma (все поля — сериализуемы)."""
        el = product.get("eligibility", {})

        # Безопасное извлечение числовых значений
        def safe_int(val, default):
            if val is None:
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def safe_float(val, default):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Гражданство: всегда список строк → строка через запятую
        citizenship_allowed = el.get("citizenship_allowed")
        if isinstance(citizenship_allowed, str):
            citizenship_allowed = [citizenship_allowed]
        citizenship_str = ",".join(citizenship_allowed) if citizenship_allowed else ""

        return {
            "id": str(product["id"]),
            "name": str(product.get("name", "")),
            "type": str(product.get("type", "")),
            "min_amount": safe_float(product.get("min_amount"), 0.0),
            "term_months": safe_int(product.get("term_months"), 0),
            "interest_rate": safe_float(product.get("interest_rate"), 0.0),
            "eligibility_min_age": safe_int(el.get("min_age"), 0),
            "eligibility_max_age": safe_int(el.get("max_age"), 999),
            "eligibility_min_income": safe_int(el.get("min_income"), 0),
            "citizenship_allowed": citizenship_str,
        }

    def upsert_products(self, products: List[Dict[str, Any]]) -> None:
        """Загружает продукты в Chroma. Ожидает список dict (как в products_data)."""
        if not products:
            logger.warning("upsert_products вызван с пустым списком")
            return

        ids = [str(p["id"]) for p in products]
        documents = [
            f"{p.get('name', '')}. {p.get('description', '')}. {p.get('text', '')}"
            for p in products
        ]
        metadatas = [self._prepare_metadata(p) for p in products]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query(
            self,
            query_text: str,
            n_results: int = 5,
            where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет запрос к коллекции.
        Возвращает список продуктов в формате, совместимом с products_data.
        """
        if not query_text.strip():
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=["metadatas", "documents"]
            )
        except Exception as e:
            logger.error(f"Chroma query failed: {e}")
            return []

        hits = []
        ids_list = results.get("ids", [[]])[0]
        metadatas_list = results.get("metadatas", [[]])[0]
        documents_list = results.get("documents", [[]])[0]

        for i in range(len(ids_list)):
            try:
                meta = metadatas_list[i]
                doc = documents_list[i]

                # Восстанавливаем citizenship_allowed из строки
                citizenship_str = meta.get("citizenship_allowed", "")
                citizenship_allowed = citizenship_str.split(",") if citizenship_str else []

                # Собираем eligibility
                eligibility = {
                    "min_age": meta.get("eligibility_min_age", 0),
                    "max_age": meta.get("eligibility_max_age", 999),
                    "min_income": meta.get("eligibility_min_income", 0),
                }
                if citizenship_allowed:
                    eligibility["citizenship_allowed"] = citizenship_allowed

                hits.append({
                    "id": ids_list[i],
                    "name": meta.get("name", ""),
                    "type": meta.get("type", ""),
                    "description": doc,
                    "eligibility": eligibility,
                    # Остальные поля можно добавить по необходимости
                })
            except (IndexError, KeyError, TypeError) as e:
                logger.warning(f"Пропущен некорректный результат из Chroma: {e}")
                continue

        return hits

    def collection_count(self) -> int:
        """Возвращает количество документов в коллекции."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.warning(f"Не удалось получить count: {e}")
            return 0

    def clear_collection(self) -> None:
        """Безопасно очищает коллекцию и пересоздаёт её."""
        try:
            self.client.delete_collection(name=self.collection.name)
        except ValueError:
            # Коллекции не существует — это OK
            pass
        finally:
            self.collection = self.client.get_or_create_collection(
                name="fairy_products",
                embedding_function=self.collection._embedding_function,
                metadata=self.collection.metadata
            )