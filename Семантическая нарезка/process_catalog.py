import json
import re
import os
from openai import OpenAI
from pathlib import Path
import httpx

# Настройки API
PROXY_API_URL = "https://api.proxyapi.ru/openai/v1"
# Читаем ключ из файла
try:
    with open("Keys.txt", "r", encoding="utf-8") as f:
        key_line = f.read().strip()
        if "=" in key_line:
            API_KEY = key_line.split("=")[-1].strip()
        else:
            API_KEY = key_line
except:
    API_KEY = "sk-sb0T53Nsm3XSwM4RLLDFNi6h8hlifsW0"  # Fallback

# Инициализация клиента с увеличенным таймаутом
client = OpenAI(
    api_key=API_KEY,
    base_url=PROXY_API_URL,
    http_client=httpx.Client(timeout=900.0)  # 15 минут для очень больших файлов
)

def transliterate(text):
    """Простая транслитерация для создания slug"""
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    result = ''
    for char in text:
        if char in translit_map:
            result += translit_map[char]
        elif char.isalnum():
            result += char
        else:
            result += '-'
    # Очистка от множественных дефисов
    result = re.sub(r'-+', '-', result)
    return result.lower().strip('-')

def extract_products_and_knowledge(text_content, brand_name):
    """Использует GPT-4o mini для извлечения продуктов и знаний из текста"""
    
    system_prompt = """Ты — эксперт по структурированию косметических каталогов. Твоя задача — преобразовать ВЕСЬ текст в JSON структуру.

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

1. ПРОДУКТЫ (products):
   - ОБЯЗАТЕЛЬНО обработай ВСЕ разделы каталога: СРЕДСТВА ДЛЯ ОЧИЩЕНИЯ, ПИЛИНГ / ЭКСФОЛИАЦИЯ, АКТИВАЦИЯ И ПОДГОТОВКА КОЖИ, УВЛАЖНЕНИЕ, ЗАЩИТА ОТ СОЛНЦА и ВСЕ ОСТАЛЬНЫЕ разделы
   - Продукт ВСЕГДА имеет название (name_ru) и (почти всегда) артикул
   - ВАЖНО: Артикулы часто указаны ПОСЛЕ описания продукта. Если видишь строку "Артикул 12345", но нет названия продукта — это артикул ПРЕДЫДУЩЕГО продукта. Добавь его в массив skus того продукта.
   - НИКОГДА не создавай объект продукта, если у него нет name_ru (названия)
   - Если у продукта несколько артикулов (разные объемы), создай несколько объектов в массиве skus
   - Формат skus: [{"art": "80009", "vol": "200 мл", "type": "home"}, {"art": "80227", "vol": "500 мл", "type": "pro"}]
   - ПОЛЕ description_full: ОБЯЗАТЕЛЬНО сохрани ПОЛНЫЙ текст из всех разделов (Механизм действия, Активные ингредиенты, Основные преимущества). НЕ сокращай текст! Объедини все разделы в один связный текст, сохранив всю информацию о механизме действия, ингредиентах и эффектах. Убери только маркетинговые слоганы в CAPS LOCK и повторы названия продукта в тексте.
   - Поле usage: ПОЛНАЯ инструкция по применению - скопируй текст из раздела "Использование в домашних условиях" ИЛИ "Использование в кабинете косметолога" (или оба, если указаны). НЕ сокращай текст инструкции!
   - Поле line: название линии (если указано, например "Skinessentials", "SKINDICATION", "Skintelligence")
   - Поле category: ТОЧНО скопируй название раздела из заголовка (например "ПИЛИНГ / ЭКСФОЛИАЦИЯ", "ПРОБЛЕМНАЯ КОЖА (акне, себорейный дерматит, жирная себорея)", "ЛЕЧЕНИЕ КУПЕРОЗА", "УВЛАЖНЕНИЕ"). НЕ меняй формулировку!
   - Поле type: тип средства определяется из названия продукта или описания (крем, тоник, сыворотка, молочко, гель, эмульсия, концентрат, маска, спрей, лосьон, пудра, бальзам, флюид и т.д.). Если в названии есть тип - используй его.
   - Поле skin_type: тип кожи / показания - скопируй текст из раздела "Для..." или "Показания". Сохрани весь текст без сокращений.
   - Поле name_en: английское название продукта, если указано в тексте после названия (например, "cleansing milk", "thermal tonic"). Если в тексте нет английского названия - оставь поле пустым.

2. ЗНАНИЯ (knowledge):
   - Любые смысловые блоки НЕ про конкретный продукт:
     * Описание проблем кожи
     * Философия бренда
     * Технологии и ингредиенты (общие)
     * Протоколы ухода
     * Этапы ухода
     * Общие рекомендации
   - Оформляй отдельными карточками с type="knowledge"
   - Поле category: категория знания (например "Типы кожи", "Протоколы ухода", "Технологии")
   - Поле recommendations: массив рекомендаций (если есть)

3. СТРУКТУРА JSON:
   {
     "products": [
       {
         "id": "brand_line_product_slug",
         "brand": "Reviderm",
         "name_ru": "Очищающее молочко",
         "name_en": "cleansing milk",
         "line": "Skinessentials",
         "category": "СРЕДСТВА ДЛЯ ОЧИЩЕНИЯ",
         "type": "молочко",
         "skin_type": "Для нормальной и сухой кожи",
         "usage": "Использование в домашних условиях: Используйте утром и вечером. Нанесите на лицо, шею и зону декольте, слегка помассируйте влажными руками. Смойте теплой водой, используя спонжи REVIDERM.",
         "description_full": "Полное подробное описание продукта с механизмом действия, всеми активными ингредиентами, их эффектами и применением. Включи ВСЮ информацию из разделов Механизм действия, Активные ингредиенты, Основные преимущества.",
         "skus": [{"art": "80009", "vol": "200 мл", "type": "home"}]
       }
     ],
     "knowledge": [
       {
         "type": "knowledge",
         "category": "Типы кожи",
         "title": "Уход за проблемной кожей",
         "content": "Полный текст знания",
         "recommendations": ["Рекомендация 1", "Рекомендация 2"]
       }
     ]
   }

4. ОБЯЗАТЕЛЬНО верни валидный JSON с ключами "products" и "knowledge"."""

    user_prompt = f"""Извлеки из следующего текста ВСЕ продукты и знания из ВСЕХ разделов. Бренд: {brand_name}

КАТЕГОРИЧЕСКИ ВАЖНО: Файл содержит несколько разделов (например, "СРЕДСТВА ДЛЯ ОЧИЩЕНИЯ", "ПИЛИНГ / ЭКСФОЛИАЦИЯ", "АКТИВАЦИЯ И ПОДГОТОВКА КОЖИ", "УВЛАЖНЕНИЕ", "ЗАЩИТА ОТ СОЛНЦА" и т.д.). ОБЯЗАТЕЛЬНО обработай ВСЕ разделы полностью, а не только первый!

ТЕКСТ:
{text_content}

Верни ТОЛЬКО валидный JSON в формате:
{{
  "products": [...],
  "knowledge": [...]
}}"""

    max_retries = 5  # Увеличиваем количество попыток
    retry_delay = 10  # Увеличиваем задержку между попытками
    
    for attempt in range(max_retries):
        try:
            print(f"Размер текста для обработки: {len(text_content)} символов")
            if attempt > 0:
                print(f"Повторная попытка {attempt + 1}/{max_retries}...")
                import time
                time.sleep(retry_delay)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=600.0  # 10 минут для больших файлов
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Генерация последовательных ID и извлечение name_en из старого ID
            products = result.get("products", [])
            print(f"Обработка {len(products)} продуктов для генерации ID...")
            
            for idx, product in enumerate(products, 1):
                # Сохраняем старый ID для извлечения name_en
                old_id = product.get("id", "")
                
                # Если name_en не указан, извлекаем его из старого ID ПЕРЕД перезаписью ID
                if not product.get("name_en") and old_id:
                    # Старый ID может быть в формате "reviderm_skinessentials_cleansing_milk"
                    # Нужно извлечь английскую часть (после бренда и линии)
                    parts = old_id.split("_")
                    # Если ID состоит из нескольких частей (бренд_линия_название)
                    if len(parts) >= 3:
                        # Берем последние части (после бренда и линии) - это английское название
                        potential_name_parts = parts[2:]
                        potential_name = "_".join(potential_name_parts)
                        # Проверяем, что это выглядит как английское название (только латиница, цифры, дефисы)
                        if all(c.isalnum() or c in ['-', '_'] for c in potential_name) and any(c.isalpha() for c in potential_name):
                            # Преобразуем в читаемый формат: cleansing_milk -> "cleansing milk"
                            # Не используем .title(), чтобы сохранить оригинальный регистр
                            product["name_en"] = potential_name.replace("_", " ")
                
                # Создаем последовательный ID в формате 000001, 000002, 000003...
                # ПЕРЕЗАПИСЫВАЕМ всегда, независимо от того, что было в старом ID
                product["id"] = f"{idx:06d}"
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка при обработке через GPT (попытка {attempt + 1}/{max_retries}): {error_msg}")
            if attempt == max_retries - 1:
                # Последняя попытка не удалась
                print("Все попытки исчерпаны. Возвращаю пустой результат.")
                return {"products": [], "knowledge": []}
            # Продолжаем цикл для следующей попытки
            # Продолжаем цикл для следующей попытки

def process_file(input_file_path, output_file_path, brand_name):
    """Обрабатывает один файл и создает JSON"""
    print(f"Чтение файла: {input_file_path}")
    
    with open(input_file_path, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Обработка через GPT-4o mini...")
    result = extract_products_and_knowledge(text_content, brand_name)
    
    print(f"Найдено продуктов: {len(result.get('products', []))}")
    print(f"Найдено знаний: {len(result.get('knowledge', []))}")
    
    # Сохранение результата
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Результат сохранен в: {output_file_path}")
    return result

if __name__ == "__main__":
    import sys
    
    # Определение бренда по имени файла
    file_brand_map = {
        "01 Skinessentials": "Reviderm",
        "02 SKINDICATION": "Reviderm",
        "03 Skintelligence": "Reviderm",
        "04 Skinprofessional": "Reviderm",
        "Seboradin": "Seboradin",
        "КАТАЛОГ DR.SPILLER": "Dr. Spiller"
    }
    
    input_dir = Path("final_clean")
    output_dir = Path("output_json")
    output_dir.mkdir(exist_ok=True)
    
    # Список файлов
    files = list(input_dir.glob("*.txt"))
    
    if not files:
        print("Файлы не найдены в папке final_clean/")
        sys.exit(1)
    
    # Выбор файла через аргумент командной строки или интерактивно
    selected_file = None
    
    if len(sys.argv) > 1:
        # Файл указан как аргумент
        file_arg = sys.argv[1]
        # Попытка найти по номеру
        try:
            file_index = int(file_arg) - 1
            if 0 <= file_index < len(files):
                selected_file = files[file_index]
        except ValueError:
            # Поиск по имени файла
            for f in files:
                if file_arg in f.name:
                    selected_file = f
                    break
    
    if selected_file is None:
        print("\nДоступные файлы:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file.name}")
        print("\nИспользование: python process_catalog.py <номер_или_имя_файла>")
        print("Пример: python process_catalog.py 1")
        print("Или: python process_catalog.py Skinessentials")
        sys.exit(0)
    
    # Определение бренда
    brand = "Reviderm"  # По умолчанию
    for key, value in file_brand_map.items():
        if key in selected_file.name:
            brand = value
            break
    
    print(f"\nОбработка файла: {selected_file.name}")
    print(f"Бренд: {brand}")
    print("-" * 50)
    
    output_file = output_dir / f"{selected_file.stem}.json"
    process_file(selected_file, output_file, brand)
