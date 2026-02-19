"""
Assembler Module
Собирает текст в логические блоки (продукты и разделы) на основе top_left_title_norm.
Главный якорь продукта: top_left_title_norm из левого верхнего угла страницы.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class TextAssembler:
    """Собирает текст в логические блоки продуктов и разделов на основе top_left_title_norm."""
    
    def __init__(self):
        # Паттерн для артикула (для информации)
        self.article_pattern = re.compile(r'Артикул\s+(\d+)', re.IGNORECASE)
        # Паттерн для названия продукта в формате "RU / EN"
        self.title_pattern = re.compile(
            r'([А-ЯЁа-яё][А-ЯЁа-яё\s\-\.,]+?)\s*/\s*([a-zA-Z][a-zA-Z\s\-\.,]+?)',
            re.IGNORECASE
        )
        # Справочник: {английское_название: полное_русское_название}
        self.title_lookup = {}
    
    def _build_title_lookup(self, cleaned_by_page: Dict[int, Dict[str, str]]) -> None:
        """
        Строит справочник названий из оглавления (первые страницы).
        Ищет названия в формате "RU / EN" и создает справочник {EN: RU}.
        
        Args:
            cleaned_by_page: Данные всех страниц
        """
        self.title_lookup = {}
        
        # Просматриваем первые 5 страниц (обычно оглавление там)
        for page_num in sorted(cleaned_by_page.keys())[:5]:
            full_text = cleaned_by_page[page_num].get('full_text', '')
            
            # Ищем все названия в формате "RU / EN"
            for match in self.title_pattern.finditer(full_text):
                russian_full = match.group(1).strip()
                english_full_original = match.group(2).strip()  # Сохраняем оригинальный регистр
                english_full_lower = english_full_original.lower()  # Для поиска
                
                # Сохраняем в справочник (английское_lower -> (русское_full, английское_full))
                # Если уже есть, берем более длинное русское название
                if (english_full_lower not in self.title_lookup or 
                    len(russian_full) > len(self.title_lookup[english_full_lower][0])):
                    self.title_lookup[english_full_lower] = (russian_full, english_full_original)
        
        print(f"Справочник названий построен: {len(self.title_lookup)} записей")
    
    def _find_english_title_in_text(self, text: str) -> Optional[str]:
        """
        Находит английское название в тексте (перед артикулом или в формате "RU / EN").
        
        Returns:
            str: Английское название (оригинальный регистр) или None
        """
        lines = text.split('\n')
        
        # Ищем перед артикулом
        article_line_idx = None
        for i, line in enumerate(lines):
            if re.search(r'Артикул\s+\d+', line, re.IGNORECASE):
                article_line_idx = i
                break
        
        if article_line_idx:
            # Ищем в 5 строках выше артикула
            search_start = max(0, article_line_idx - 5)
            for i in range(article_line_idx - 1, search_start - 1, -1):
                line = lines[i].strip()
                if not line:
                    continue
                # Проверяем, что это английская строка (латиница без кириллицы)
                if re.search(r'^[a-zA-Z]', line) and not re.search(r'[А-ЯЁа-яё]', line):
                    if not re.search(r'артикул|article|мл|ml|home|professional', line, re.IGNORECASE):
                        if 3 <= len(line) <= 150:  # Увеличили максимум для полных названий
                            return line  # Возвращаем оригинальный регистр
        
        # Ищем в тексте паттерн "RU / EN"
        match = self.title_pattern.search(text)
        if match:
            return match.group(2).strip()  # Возвращаем оригинальный регистр
        
        return None
    
    def _find_russian_title_before_article(self, text: str) -> Optional[str]:
        """
        Находит полное русское название перед артикулом.
        Собирает все строки с кириллицей перед артикулом.
        
        Returns:
            str: Полное русское название или None
        """
        lines = text.split('\n')
        
        # Находим первую строку с "Артикул"
        article_line_idx = None
        for i, line in enumerate(lines):
            if re.search(r'Артикул\s+\d+', line, re.IGNORECASE):
                article_line_idx = i
                break
        
        if article_line_idx is None:
            return None
        
        # Ищем в 8 строках выше артикула
        search_start = max(0, article_line_idx - 8)
        russian_parts = []
        
        # Идем назад от артикула
        for i in range(article_line_idx - 1, search_start - 1, -1):
            line = lines[i].strip()
            if not line:
                continue
            
            # Пропускаем служебные строки
            if re.search(r'артикул|мл|домашняя|профессиональный|липидный|уровень|увлажнения', line, re.IGNORECASE):
                continue
            
            # Проверяем кириллицу (но не английскую строку)
            has_cyrillic = bool(re.search(r'[А-ЯЁа-яё]', line))
            has_latin_only = bool(re.search(r'^[a-zA-Z]', line) and not re.search(r'[А-ЯЁа-яё]', line))
            
            if has_cyrillic and len(line) >= 2:
                # Добавляем в начало (идем назад)
                russian_parts.insert(0, line)
            elif has_latin_only:
                # Дошли до английской строки - прекращаем сбор русских
                break
        
        if russian_parts:
            return ' '.join(russian_parts)
        
        return None
    
    def _resolve_full_title(self, title_from_roi: str, page_text: str) -> str:
        """
        Разрешает полное название продукта используя:
        1. Название из ROI (может быть обрезанное)
        2. Полное русское название перед артикулом
        3. Справочник из оглавления (по английскому названию)
        
        Args:
            title_from_roi: Название из ROI (может быть обрезанное)
            page_text: Полный текст страницы
            
        Returns:
            str: Полное название в формате "RU / EN"
        """
        # Парсим название из ROI
        roi_match = self.title_pattern.search(title_from_roi)
        if roi_match:
            roi_russian = roi_match.group(1).strip()
            roi_english = roi_match.group(2).strip()
        else:
            # Если не в формате "RU / EN", пытаемся извлечь отдельно
            roi_russian = title_from_roi.strip()
            roi_english = None
        
        # Ищем английское название в тексте страницы
        # Сначала пытаемся найти полное в тексте перед артикулом
        english_title = self._find_english_title_in_text(page_text)
        
        # Если не нашли в тексте, используем из ROI
        if not english_title and roi_english:
            english_title = roi_english
        
        if not english_title:
            # Если не нашли английское, возвращаем как есть
            return title_from_roi
        
        # Нормализуем английское для поиска в справочнике (нижний регистр)
        english_lower = english_title.lower()
        
        # Ищем полное русское название и полное английское
        full_russian = None
        full_english = english_title  # Начальное значение
        
        # 1. Проверяем справочник из оглавления (по нормализованному английскому)
        lookup_value = None
        if english_lower in self.title_lookup:
            lookup_value = self.title_lookup[english_lower]
        else:
            # Проверяем частичное совпадение (если английское обрезанное)
            # Ищем наиболее подходящее совпадение
            best_match = None
            best_match_length = 0
            
            for lookup_en_lower, lookup_val in self.title_lookup.items():
                # Проверяем несколько вариантов частичного совпадения
                if isinstance(lookup_val, tuple):
                    lookup_ru, lookup_en_full = lookup_val
                else:
                    lookup_ru = lookup_val
                    lookup_en_full = lookup_en_lower
                
                # Вариант 1: обрезанное является началом полного (самый надежный)
                if lookup_en_lower.startswith(english_lower):
                    if len(lookup_en_lower) > best_match_length:
                        best_match = lookup_val
                        best_match_length = len(lookup_en_lower)
                
                # Вариант 2: полное содержит обрезанное
                elif english_lower in lookup_en_lower:
                    if len(lookup_en_lower) > best_match_length:
                        best_match = lookup_val
                        best_match_length = len(lookup_en_lower)
                
                # Вариант 3: обрезанное очень короткое (2-3 символа), проверяем по началу полного
                elif len(english_lower) >= 2 and len(english_lower) <= 4 and lookup_en_lower.startswith(english_lower):
                    if len(lookup_en_lower) > best_match_length:
                        best_match = lookup_val
                        best_match_length = len(lookup_en_lower)
            
            if best_match:
                lookup_value = best_match
        
        # Используем найденное значение из справочника
        if lookup_value:
            if isinstance(lookup_value, tuple):
                full_russian_from_lookup, full_english_from_lookup = lookup_value
                # ВСЕГДА используем полное английское из справочника, если оно найдено
                full_russian = full_russian_from_lookup
                full_english = full_english_from_lookup  # Критично: используем полное из справочника
            else:
                # Старая структура (только русское)
                full_russian = lookup_value
        # Если не нашли в справочнике - используем найденное английское (может быть обрезанное)
        
        # 2. Если не нашли в справочнике, ищем перед артикулом
        if not full_russian:
            full_russian = self._find_russian_title_before_article(page_text)
        
        # 3. Если все еще не нашли русское, используем из ROI (даже если обрезанное)
        if not full_russian and roi_russian:
            full_russian = roi_russian
        
        # Формируем итоговое название
        if full_russian and full_english:
            return f"{full_russian} / {full_english}"
        elif full_russian:
            return full_russian
        elif full_english:
            return full_english
        else:
            return title_from_roi
    
    def assemble_by_title_anchors(self, cleaned_by_page: Dict[int, Dict[str, str]]) -> List[str]:
        """
        Собирает текст в блоки продуктов на основе top_left_title_norm.
        
        Логика:
        - Идём по страницам по порядку
        - Если у страницы top_left_title_norm непустой:
          * если это новый title (не равен текущему активному) → закрыть текущий продукт и начать новый
          * если title тот же → это продолжение текущего продукта
        - Если title пустой:
          * страницу добавлять в текущий продукт, если он уже открыт
          * иначе считать это "section/вводный текст"
        
        Args:
            cleaned_by_page: Dict[int, Dict[str, str]] {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
            
        Returns:
            List[str]: Список блоков (продукты и разделы)
        """
        # Сначала строим справочник из оглавления
        self._build_title_lookup(cleaned_by_page)
        
        all_blocks = []
        current_product_title = None
        current_product_pages = []  # Список индексов страниц текущего продукта
        section_pages = []  # Страницы без title (до первого продукта)
        
        # Идем по страницам в порядке
        for page_num in sorted(cleaned_by_page.keys()):
            page_data = cleaned_by_page[page_num]
            title_norm = page_data.get('top_left_title_norm', '').strip()
            full_text = page_data.get('full_text', '')
            
            if title_norm:
                # Страница с title
                if title_norm != current_product_title:
                    # Новый продукт - закрываем предыдущий
                    if current_product_title and current_product_pages:
                        product_block = self._create_product_block(
                            current_product_title,
                            current_product_pages,
                            cleaned_by_page
                        )
                        all_blocks.append(product_block)
                    
                    # Начинаем новый продукт
                    current_product_title = title_norm
                    current_product_pages = [page_num]
                else:
                    # Продолжение текущего продукта
                    current_product_pages.append(page_num)
            else:
                # Страница без title
                if current_product_title:
                    # Добавляем к текущему продукту
                    current_product_pages.append(page_num)
                else:
                    # Вводный текст/раздел (до первого продукта)
                    section_pages.append(page_num)
        
        # Закрываем последний продукт, если он был открыт
        if current_product_title and current_product_pages:
            product_block = self._create_product_block(
                current_product_title,
                current_product_pages,
                cleaned_by_page
            )
            all_blocks.append(product_block)
        
        # Добавляем вводные разделы в начало
        if section_pages:
            section_block = self._create_section_block(section_pages, cleaned_by_page)
            if section_block.strip():
                all_blocks.insert(0, section_block)
        
        return all_blocks
    
    def _find_full_title_before_article(self, text: str) -> Optional[str]:
        """
        Ищет полное название продукта перед артикулом в тексте.
        Название может быть многострочным (несколько строк русского названия + английское).
        
        Returns:
            str: Полное название в формате "RU / EN" или None
        """
        lines = text.split('\n')
        
        # Находим первую строку с "Артикул"
        article_line_idx = None
        for i, line in enumerate(lines):
            if re.search(r'Артикул\s+\d+', line, re.IGNORECASE):
                article_line_idx = i
                break
        
        if article_line_idx is None:
            return None
        
        # Ищем в 3-10 строках выше артикула (увеличили диапазон для многострочных названий)
        search_start = max(0, article_line_idx - 10)
        search_end = article_line_idx
        
        # Собираем последовательные строки русского названия и английскую строку
        russian_parts = []
        english_line = None
        
        # Идем от артикула назад, собирая строки
        i = article_line_idx - 1
        while i >= search_start:
            line = lines[i].strip()
            
            # Пропускаем пустые строки в начале поиска
            if not line and not russian_parts and not english_line:
                i -= 1
                continue
            
            # Пропускаем служебные строки
            if re.search(r'артикул|мл|домашняя|профессиональный|липидный|уровень|увлажнения|антиоксидант', line, re.IGNORECASE):
                # Если уже собрали части названия, прекращаем поиск
                if russian_parts or english_line:
                    break
                i -= 1
                continue
            
            # Проверяем кириллицу
            has_cyrillic = bool(re.search(r'[А-ЯЁа-яё]', line))
            # Проверяем латиницу (без кириллицы)
            has_latin_only = bool(re.search(r'^[a-zA-Z]', line) and not re.search(r'[А-ЯЁа-яё]', line) and len(line) >= 3)
            
            if has_latin_only and english_line is None:
                # Нашли английскую строку (первую встреченную)
                english_line = line
            elif has_cyrillic and len(line) >= 2:
                # Добавляем русскую строку (в начало списка, т.к. идем назад)
                russian_parts.insert(0, line)
            
            i -= 1
        
        # Формируем полное название
        if russian_parts and english_line:
            # Объединяем все русские части в одну строку
            full_russian = ' '.join(russian_parts)
            return f"{full_russian} / {english_line}"
        elif russian_parts and not english_line:
            # Только русские строки
            return ' '.join(russian_parts)
        elif english_line and not russian_parts:
            # Только английская строка
            return english_line
        
        return None
    
    def _create_product_block(self, title: str, page_indices: List[int], 
                              cleaned_by_page: Dict[int, Dict[str, str]]) -> str:
        """
        Создает блок продукта из страниц.
        
        Args:
            title: Нормализованный заголовок продукта из ROI (может быть обрезанное)
            page_indices: Список индексов страниц продукта
            cleaned_by_page: Данные всех страниц
            
        Returns:
            str: Текст блока продукта с полным заголовком и составом в начале
        """
        # Собираем текст всех страниц продукта
        page_texts = []
        first_page_text = ""
        first_page_composition = ""
        for page_num in page_indices:
            full_text = cleaned_by_page[page_num].get('full_text', '')
            if full_text.strip():
                page_texts.append(full_text)
                if not first_page_text:
                    first_page_text = full_text
                    # Берем состав из первой страницы продукта
                    first_page_composition = cleaned_by_page[page_num].get('composition', '').strip()
        
        # Объединяем текст страниц
        combined_text = '\n\n'.join(page_texts)
        
        # Разрешаем полное название используя справочник и поиск перед артикулом
        full_title = self._resolve_full_title(title, combined_text)
        
        # Очищаем блок
        cleaned_text = self.clean_block(combined_text)
        
        # Формируем начало блока: название, затем состав (если есть)
        block_header = full_title
        if first_page_composition:
            block_header = f"{full_title}\n{first_page_composition}"
        
        # Вставляем заголовок и состав в начало
        if cleaned_text.strip():
            return f"{block_header}\n\n{cleaned_text}"
        else:
            return block_header
    
    def _create_section_block(self, page_indices: List[int], 
                              cleaned_by_page: Dict[int, Dict[str, str]]) -> str:
        """
        Создает блок раздела из страниц без title.
        
        Args:
            page_indices: Список индексов страниц раздела
            cleaned_by_page: Данные всех страниц
            
        Returns:
            str: Текст блока раздела
        """
        page_texts = []
        for page_num in page_indices:
            full_text = cleaned_by_page[page_num].get('full_text', '')
            if full_text.strip():
                page_texts.append(full_text)
        
        combined_text = '\n\n'.join(page_texts)
        return self.clean_block(combined_text)
    
    def clean_block(self, block_text: str) -> str:
        """Очищает блок от лишних пустых строк, сохраняя структуру."""
        lines = block_text.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            is_empty = not line.strip()
            if is_empty:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        # Убираем пустые строки в начале и конце
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)


def assemble_text(cleaned_by_page: Dict[int, Dict[str, str]]) -> List[str]:
    """
    Главная функция для сборки текста в блоки.
    
    Args:
        cleaned_by_page: Dict[int, Dict[str, str]] {
            page_num: {
                'full_text': str,
                'top_left_title_raw': str,
                'top_left_title_norm': str,
                'composition': str
            }
        }
        
    Returns:
        List[str]: Список блоков продуктов и разделов
    """
    assembler = TextAssembler()
    blocks = assembler.assemble_by_title_anchors(cleaned_by_page)
    return blocks
