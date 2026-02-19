"""
Скрипт для создания векторной базы данных из JSON файлов
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import config


def normalize_id(text: str) -> str:
    """Нормализация текста для использования в ID"""
    if not text:
        return "unknown"
    text = str(text).lower()
    text = re.sub(r'[^\w\s-]', '', text)  # Удаляем спецсимволы
    text = re.sub(r'\s+', '_', text)  # Заменяем пробелы на подчеркивания
    text = text.strip('_')  # Убираем подчеркивания в начале и конце
    if not text:
        return "unknown"
    return text


def load_json_files(json_dir: str) -> List[Dict[str, Any]]:
    """Загрузка всех JSON файлов из директории"""
    json_path = Path(json_dir)
    json_files = list(json_path.glob("*.json"))
    
    print(f"Найдено JSON файлов: {len(json_files)}")
    
    all_data = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.append(data)
                print(f"  ✓ Загружен: {json_file.name}")
        except Exception as e:
            print(f"  ✗ Ошибка при загрузке {json_file.name}: {e}")
    
    return all_data


def process_products(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Обработка продуктов из всех JSON файлов"""
    products = []
    
    for data in all_data:
        if "products" in data:
            products.extend(data["products"])
    
    print(f"Найдено продуктов: {len(products)}")
    
    processed_products = []
    seen_ids = set()
    
    for idx, product in enumerate(products):
        # Формируем текст для эмбеддинга с префиксом passage:
        name_ru = product.get("name_ru", "")
        name_en = product.get("name_en", "")
        brand = product.get("brand", "")
        line = product.get("line", "")
        description_full = product.get("description_full", "")
        
        passage_text = f"passage: Продукт: {name_ru} / {name_en}\nБренд: {brand}\nЛиния: {line}\n{description_full}"
        
        # Формируем детерминированный ID
        product_id = f"product_{normalize_id(brand)}_{normalize_id(name_en)}"
        
        # Обработка дубликатов ID
        original_id = product_id
        counter = 1
        while product_id in seen_ids:
            product_id = f"{original_id}_{counter}"
            counter += 1
        seen_ids.add(product_id)
        
        # Преобразуем skus в строку для метаданных
        skus_str = json.dumps(product.get("skus", []), ensure_ascii=False)
        
        # Метаданные
        metadata = {
            "type": "product",
            "name_ru": name_ru,
            "brand": brand,
            "line": line,
            "skin_type": product.get("skin_type", ""),
            "skus": skus_str
        }
        
        processed_products.append({
            "id": product_id,
            "text": passage_text,
            "metadata": metadata
        })
    
    return processed_products


def process_knowledge(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Обработка статей из базы знаний"""
    knowledge_items = []
    
    for data in all_data:
        if "knowledge" in data:
            knowledge_items.extend(data["knowledge"])
    
    print(f"Найдено статей: {len(knowledge_items)}")
    
    processed_guides = []
    seen_ids = set()
    
    for item in knowledge_items:
        title = item.get("title", "")
        content = item.get("content", "")
        
        # Формируем текст для эмбеддинга с префиксом passage:
        passage_text = f"passage: Тема: {title}\n{content}"
        
        # Формируем детерминированный ID
        guide_id = f"guide_{normalize_id(title)}"
        
        # Обработка дубликатов ID
        original_id = guide_id
        counter = 1
        while guide_id in seen_ids:
            guide_id = f"{original_id}_{counter}"
            counter += 1
        seen_ids.add(guide_id)
        
        # Метаданные
        metadata = {
            "type": "guide",
            "title": title
        }
        
        processed_guides.append({
            "id": guide_id,
            "text": passage_text,
            "metadata": metadata
        })
    
    return processed_guides


def create_preview(products: List[Dict[str, Any]], guides: List[Dict[str, Any]], preview_file: str = "chunks_preview.txt"):
    """Создание preview файла с первыми 5 продуктами и 5 статьями"""
    with open(preview_file, 'w', encoding='utf-8') as f:
        f.write("[DOCUMENT PREVIEW]\n")
        f.write("=" * 80 + "\n\n")
        
        # Продукты
        f.write("ПРОДУКТЫ (первые 5):\n")
        f.write("-" * 80 + "\n\n")
        
        for i, product in enumerate(products[:5], 1):
            f.write(f"[Продукт {i}]\n")
            f.write(f"ID: {product['id']}\n")
            f.write(f"Metadata: {json.dumps(product['metadata'], ensure_ascii=False, indent=2)}\n")
            content_preview = product['text'][:200] + "..." if len(product['text']) > 200 else product['text']
            f.write(f"Content: {content_preview}\n")
            f.write("-" * 80 + "\n\n")
        
        # Статьи
        f.write("\nСТАТЬИ (первые 5):\n")
        f.write("-" * 80 + "\n\n")
        
        for i, guide in enumerate(guides[:5], 1):
            f.write(f"[Статья {i}]\n")
            f.write(f"ID: {guide['id']}\n")
            f.write(f"Metadata: {json.dumps(guide['metadata'], ensure_ascii=False, indent=2)}\n")
            content_preview = guide['text'][:200] + "..." if len(guide['text']) > 200 else guide['text']
            f.write(f"Content: {content_preview}\n")
            f.write("-" * 80 + "\n\n")
    
    print(f"\n✓ Preview файл создан: {preview_file}")
    print(f"  Просмотрите файл перед продолжением.")


def build_rag_database(json_dir: str = "JSON файлы", chroma_db_path: str = "../chroma_db"):
    """Основная функция для создания RAG базы данных"""
    
    print("=" * 80)
    print("СОЗДАНИЕ ВЕКТОРНОЙ БАЗЫ ДАННЫХ")
    print("=" * 80)
    print()
    
    # 1. Загрузка JSON файлов
    print("ШАГ 1: Загрузка JSON файлов...")
    all_data = load_json_files(json_dir)
    print()
    
    if not all_data:
        print("Ошибка: Не найдено JSON файлов для обработки!")
        return
    
    # 2. Обработка данных
    print("ШАГ 2: Обработка данных...")
    products = process_products(all_data)
    guides = process_knowledge(all_data)
    print()
    
    if not products and not guides:
        print("Ошибка: Не найдено данных для обработки!")
        return
    
    # 3. Создание preview
    print("ШАГ 3: Создание preview файла...")
    create_preview(products, guides)
    print()
    
    # 4. Ожидание подтверждения
    print("=" * 80)
    print("ПРЕВЬЮ СОЗДАН. Просмотрите файл chunks_preview.txt")
    print("=" * 80)
    input("Нажмите Enter для продолжения загрузки в ChromaDB или Ctrl+C для отмены...")
    print()
    
    # 5. Инициализация модели и базы данных
    print("ШАГ 4: Инициализация модели эмбеддингов...")
    print(f"  Модель: {config.EMBEDDING_MODEL}")
    embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    print("  ✓ Модель загружена")
    print()
    
    print("ШАГ 5: Инициализация ChromaDB...")
    client = chromadb.PersistentClient(
        path=chroma_db_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Получаем или создаем коллекцию
    collection = client.get_or_create_collection(
        name="cosmetics_products",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Очищаем коллекцию перед загрузкой новых данных
    print("  Очистка существующей коллекции...")
    try:
        collection.delete()
        collection = client.create_collection(
            name="cosmetics_products",
            metadata={"hnsw:space": "cosine"}
        )
        print("  ✓ Коллекция очищена")
    except:
        print("  ✓ Коллекция создана")
    print()
    
    # 6. Загрузка данных в ChromaDB
    print("ШАГ 6: Загрузка данных в ChromaDB...")
    
    all_documents = products + guides
    total_docs = len(all_documents)
    
    print(f"  Всего документов для загрузки: {total_docs}")
    print(f"    - Продуктов: {len(products)}")
    print(f"    - Статей: {len(guides)}")
    print()
    
    # Подготовка данных для батч-загрузки
    ids = []
    texts = []
    metadatas = []
    
    for doc in tqdm(all_documents, desc="Подготовка эмбеддингов"):
        ids.append(doc["id"])
        texts.append(doc["text"])
        metadatas.append(doc["metadata"])
    
    # Генерация эмбеддингов
    print("\nГенерация эмбеддингов...")
    embeddings = []
    batch_size = 32
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Создание эмбеддингов"):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = embedding_model.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        embeddings.extend(batch_embeddings.tolist())
    
    # Загрузка в ChromaDB
    print("\nЗагрузка в ChromaDB...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    
    print()
    print("=" * 80)
    print("УСПЕШНО ЗАВЕРШЕНО!")
    print("=" * 80)
    print(f"✓ JSON файлов обработано: {len(all_data)}")
    print(f"✓ Продуктов обработано: {len(products)}")
    print(f"✓ Статей обработано: {len(guides)}")
    print(f"✓ Документов добавлено в ChromaDB: {total_docs}")
    print(f"✓ База данных сохранена в: {chroma_db_path}")
    print()


if __name__ == "__main__":
    build_rag_database()
