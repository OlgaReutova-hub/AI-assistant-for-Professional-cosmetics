#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт для обработки части файла"""

import sys
import json
from pathlib import Path
from process_catalog import extract_products_and_knowledge, process_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python process_part.py <путь_к_файлу>")
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
    
    print(f"Обработка файла: {input_file.name}")
    print(f"Бренд: {brand}")
    print("-" * 50)
    
    result = process_file(input_file, output_file, brand)
    
    print(f"\nОбработка завершена!")
    print(f"Найдено продуктов: {len(result.get('products', []))}")
    print(f"Найдено знаний: {len(result.get('knowledge', []))}")
