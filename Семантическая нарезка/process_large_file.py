#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт для обработки больших файлов по частям"""

import sys
import json
from pathlib import Path
from process_catalog import extract_products_and_knowledge

def split_text_into_chunks(text, chunk_size=20000):
    """Разбивает текст на части примерно по chunk_size символов, стараясь не разрывать продукты"""
    chunks = []
    current_chunk = ""
    
    # Разбиваем по строкам
    lines = text.split('\n')
    
    for line in lines:
        # Если добавление строки не превысит размер чанка
        if len(current_chunk) + len(line) + 1 < chunk_size:
            current_chunk += line + '\n'
        else:
            # Сохраняем текущий чанк
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Начинаем новый чанк
            current_chunk = line + '\n'
    
    # Добавляем последний чанк
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def process_large_file(input_file_path, output_file_path, brand_name):
    """Обрабатывает большой файл по частям и объединяет результаты"""
    print(f"Чтение файла: {input_file_path}")
    
    with open(input_file_path, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Размер файла: {len(text_content)} символов")
    
    # Разбиваем на части по 20000 символов
    chunks = split_text_into_chunks(text_content, chunk_size=20000)
    print(f"Файл разбит на {len(chunks)} частей")
    
    all_products = []
    all_knowledge = []
    product_counter = 1  # Счетчик для последовательных ID
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n{'='*60}")
        print(f"Обработка части {i}/{len(chunks)} (размер: {len(chunk)} символов)")
        print(f"{'='*60}")
        
        try:
            result = extract_products_and_knowledge(chunk, brand_name)
            
            products = result.get("products", [])
            knowledge = result.get("knowledge", [])
            
            print(f"Найдено в части {i}: {len(products)} продуктов, {len(knowledge)} знаний")
            
            # Перенумеровываем ID продуктов
            for product in products:
                product["id"] = f"{product_counter:06d}"
                product_counter += 1
            
            all_products.extend(products)
            all_knowledge.extend(knowledge)
            
        except Exception as e:
            print(f"Ошибка при обработке части {i}: {e}")
            continue
    
    # Объединяем результаты
    final_result = {
        "products": all_products,
        "knowledge": all_knowledge
    }
    
    print(f"\n{'='*60}")
    print(f"ИТОГО:")
    print(f"Всего продуктов: {len(all_products)}")
    print(f"Всего знаний: {len(all_knowledge)}")
    print(f"{'='*60}")
    
    # Сохранение результата
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        print(f"\nРезультат сохранен в: {output_file_path}")
        
        # Проверка сохранения
        with open(output_file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            if len(saved_data.get('products', [])) != len(all_products):
                print(f"ВНИМАНИЕ: Сохранено {len(saved_data.get('products', []))} продуктов, ожидалось {len(all_products)}")
    except Exception as e:
        print(f"ОШИБКА при сохранении файла: {e}")
        raise
    
    return final_result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python process_large_file.py <путь_к_файлу>")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_dir = Path("output_new_json")
    output_dir.mkdir(exist_ok=True)
    
    if not input_file.exists():
        print(f"Файл не найден: {input_file}")
        sys.exit(1)
    
    # Определение бренда по имени файла
    file_name = input_file.name.lower()
    if "skindication" in file_name or "skinessentials" in file_name or "skintelligence" in file_name or "skinprofessional" in file_name:
        brand = "Reviderm"
    elif "seboradin" in file_name:
        brand = "Seboradin"
    elif "spiller" in file_name or "dr.spiller" in file_name or "dr" in file_name:
        brand = "Dr. Spiller"
    else:
        brand = "Reviderm"  # По умолчанию
    
    # Определяем имя выходного файла
    output_file = output_dir / f"{input_file.stem}.json"
    
    print(f"Обработка большого файла: {input_file.name}")
    print(f"Бренд: {brand}")
    print("-" * 50)
    
    result = process_large_file(input_file, output_file, brand)
    
    print(f"\nОбработка завершена!")
    print(f"Найдено продуктов: {len(result.get('products', []))}")
    print(f"Найдено знаний: {len(result.get('knowledge', []))}")
