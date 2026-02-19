"""
Модуль для работы с RAG системой (Chroma DB)
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import config
import os


class RAGService:
    """Сервис для работы с векторной базой данных Chroma DB"""
    
    def __init__(self):
        """Инициализация RAG сервиса"""
        self.embedding_model = None
        self._model_loaded = False
        
        # Инициализация Chroma DB
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Получаем или создаем коллекцию
        self.collection = self.client.get_or_create_collection(
            name="cosmetics_products",
            metadata={"hnsw:space": "cosine"}
        )
    
    def _load_model(self):
        """Ленивая загрузка модели (только при первом использовании)"""
        if not self._model_loaded:
            try:
                print(f"Загрузка модели эмбеддингов: {config.EMBEDDING_MODEL}...")
                self.embedding_model = SentenceTransformer(
                    config.EMBEDDING_MODEL,
                    device='cpu'  # Используем CPU для экономии памяти
                )
                self._model_loaded = True
                print("[OK] Модель успешно загружена")
            except Exception as e:
                print(f"[ERROR] Ошибка при загрузке модели {config.EMBEDDING_MODEL}: {e}")
                print("Попытка использовать более легкую модель...")
                try:
                    # Пробуем более легкую модель
                    fallback_model = "paraphrase-multilingual-MiniLM-L12-v2"
                    print(f"Загрузка альтернативной модели: {fallback_model}...")
                    self.embedding_model = SentenceTransformer(fallback_model, device='cpu')
                    self._model_loaded = True
                    print("[OK] Альтернативная модель успешно загружена")
                except Exception as e2:
                    print(f"[ERROR] Критическая ошибка: не удалось загрузить ни одну модель: {e2}")
                    raise
    
    def _get_embedding(self, text: str):
        """Получить эмбеддинг для текста"""
        if not self._model_loaded:
            self._load_model()
        if self.embedding_model is None:
            raise RuntimeError("Модель эмбеддингов не загружена")
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def search(self, query: str, n_results: int = 5):
        """
        Поиск в векторной базе по запросу
        
        Args:
            query: Текстовый запрос пользователя
            n_results: Количество результатов для возврата
            
        Returns:
            Список результатов поиска
        """
        try:
            query_embedding = self._get_embedding(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
        except Exception as e:
            print(f"Ошибка при поиске в RAG: {e}")
            return None
    
    def get_all_products(self):
        """Получить все продукты из базы (для тестирования)"""
        try:
            results = self.collection.get()
            return results
        except Exception as e:
            print(f"Ошибка при получении всех продуктов: {e}")
            return None


if __name__ == "__main__":
    # Тестирование RAG сервиса
    print("Инициализация RAG сервиса...")
    rag = RAGService()
    
    print(f"Коллекция создана: {rag.collection.name}")
    print(f"Количество документов в коллекции: {rag.collection.count()}")
    
    # Тестовый поиск
    if rag.collection.count() > 0:
        print("\nТестовый поиск...")
        results = rag.search("косметика для жирной кожи")
        if results and results['documents']:
            print(f"Найдено результатов: {len(results['documents'][0])}")
            print("\nПервые результаты:")
            for i, doc in enumerate(results['documents'][0][:3]):
                print(f"{i+1}. {doc[:200]}...")
    else:
        print("База данных пуста. Необходимо добавить данные в Chroma DB.")
