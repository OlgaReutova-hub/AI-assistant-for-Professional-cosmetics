"""
Конфигурация для модуля создания векторной базы данных
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Chroma DB
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Embedding Model
# Используем более легкую модель по умолчанию для экономии памяти
# Альтернативы: "intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
