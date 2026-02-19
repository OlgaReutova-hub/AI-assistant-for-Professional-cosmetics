"""
QC Module
Контроль качества: проверка полноты извлечения по якорям.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json


class QualityController:
    """Проверяет полноту извлечения текста по якорям."""
    
    def __init__(self):
        # Паттерны для якорей
        self.article_pattern = re.compile(r'Артикул\s+(\d+)', re.IGNORECASE)
        self.product_title_pattern = re.compile(r'([А-ЯЁа-яё\s\-]+)\s*/\s*([A-Za-z\s\-]+)')
        self.ph_pattern = re.compile(r'\bpH\s*[=:]?\s*[\d.]+', re.IGNORECASE)
        self.subheading_patterns = [
            re.compile(r'^Для\s+', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Основные\s+активные\s+ингредиенты', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Механизм\s+действия', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Использование', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Основные\s+преимущества', re.MULTILINE | re.IGNORECASE),
        ]
    
    def extract_anchors_from_raw(self, raw_text_by_page: Dict[int, str]) -> Dict[str, Set[str]]:
        """
        Извлекает якоря из raw текста.
        
        Returns:
            Dict[str, Set[str]]: Словарь {тип_якоря: множество_значений}
        """
        anchors = {
            'articles': set(),
            'product_titles': set(),
            'ph_values': set(),
            'subheadings': set(),
        }
        
        # Объединяем весь raw текст
        full_raw_text = '\n'.join(raw_text_by_page.values())
        
        # Извлекаем артикулы
        for match in self.article_pattern.finditer(full_raw_text):
            article = match.group(1)
            anchors['articles'].add(article)
        
        # Извлекаем названия продуктов
        for match in self.product_title_pattern.finditer(full_raw_text):
            title = match.group(0).strip()
            anchors['product_titles'].add(title)
        
        # Извлекаем pH значения
        for match in self.ph_pattern.finditer(full_raw_text):
            ph_value = match.group(0).strip()
            anchors['ph_values'].add(ph_value)
        
        # Извлекаем подзаголовки
        for pattern in self.subheading_patterns:
            for match in pattern.finditer(full_raw_text):
                subheading = match.group(0).strip()
                anchors['subheadings'].add(subheading)
        
        return anchors
    
    def extract_anchors_from_cleaned(self, cleaned_text: str) -> Dict[str, Set[str]]:
        """
        Извлекает якоря из очищенного текста.
        
        Returns:
            Dict[str, Set[str]]: Словарь {тип_якоря: множество_значений}
        """
        anchors = {
            'articles': set(),
            'product_titles': set(),
            'ph_values': set(),
            'subheadings': set(),
        }
        
        # Извлекаем артикулы
        for match in self.article_pattern.finditer(cleaned_text):
            article = match.group(1)
            anchors['articles'].add(article)
        
        # Извлекаем названия продуктов
        for match in self.product_title_pattern.finditer(cleaned_text):
            title = match.group(0).strip()
            anchors['product_titles'].add(title)
        
        # Извлекаем pH значения
        for match in self.ph_pattern.finditer(cleaned_text):
            ph_value = match.group(0).strip()
            anchors['ph_values'].add(ph_value)
        
        # Извлекаем подзаголовки
        for pattern in self.subheading_patterns:
            for match in pattern.finditer(cleaned_text):
                subheading = match.group(0).strip()
                anchors['subheadings'].add(subheading)
        
        return anchors
    
    def find_missing_anchors(self, raw_anchors: Dict[str, Set[str]], 
                            cleaned_anchors: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """
        Находит отсутствующие якоря в очищенном тексте.
        
        Returns:
            Dict[str, Set[str]]: Словарь {тип_якоря: множество_отсутствующих_значений}
        """
        missing = {}
        
        for anchor_type in raw_anchors.keys():
            raw_set = raw_anchors.get(anchor_type, set())
            cleaned_set = cleaned_anchors.get(anchor_type, set())
            missing_set = raw_set - cleaned_set
            if missing_set:
                missing[anchor_type] = missing_set
        
        return missing
    
    def find_page_for_anchor(self, anchor: str, raw_text_by_page: Dict[int, str]) -> List[int]:
        """
        Находит страницы, где встречается якорь.
        
        Returns:
            List[int]: Список номеров страниц
        """
        pages = []
        for page_num, text in raw_text_by_page.items():
            if anchor in text:
                pages.append(page_num + 1)  # +1 для человекочитаемого формата
        return pages
    
    def generate_qc_report(self, raw_text_by_page: Dict[int, str], 
                          cleaned_text: str, output_file: Path):
        """
        Генерирует отчет о контроле качества.
        
        Args:
            raw_text_by_page: Raw текст по страницам
            cleaned_text: Финальный очищенный текст
            output_file: Путь к файлу отчета
        """
        print("Генерация отчета контроля качества...")
        
        # Извлекаем якоря
        raw_anchors = self.extract_anchors_from_raw(raw_text_by_page)
        cleaned_anchors = self.extract_anchors_from_cleaned(cleaned_text)
        
        # Находим отсутствующие
        missing = self.find_missing_anchors(raw_anchors, cleaned_anchors)
        
        # Генерируем отчет
        report_lines = []
        report_lines.append("ОТЧЕТ КОНТРОЛЯ КАЧЕСТВА")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if not missing:
            report_lines.append("✓ ВСЕ ЯКОРЯ НАЙДЕНЫ")
            report_lines.append("")
            report_lines.append("Статистика:")
            report_lines.append(f"  Артикулы: {len(raw_anchors['articles'])} найдено")
            report_lines.append(f"  Названия продуктов: {len(raw_anchors['product_titles'])} найдено")
            report_lines.append(f"  pH значения: {len(raw_anchors['ph_values'])} найдено")
            report_lines.append(f"  Подзаголовки: {len(raw_anchors['subheadings'])} найдено")
        else:
            report_lines.append("⚠ ОБНАРУЖЕНЫ ОТСУТСТВУЮЩИЕ ЯКОРЯ")
            report_lines.append("")
            
            for anchor_type, missing_set in missing.items():
                report_lines.append(f"\n{anchor_type.upper()}:")
                report_lines.append("-" * 80)
                
                for anchor in sorted(missing_set):
                    pages = self.find_page_for_anchor(anchor, raw_text_by_page)
                    pages_str = ", ".join(map(str, pages))
                    report_lines.append(f"  {anchor} (страницы: {pages_str})")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("РЕКОМЕНДАЦИИ:")
        report_lines.append("Если обнаружены отсутствующие якоря, необходимо:")
        report_lines.append("1. Проверить соответствующие страницы в raw тексте")
        report_lines.append("2. Улучшить правила очистки или сборки")
        report_lines.append("3. НЕ сокращать текст - только переизвлечь/пересобрать")
        
        # Сохраняем отчет
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"Отчет сохранен в: {output_file}")
        
        if missing:
            print(f"⚠ Обнаружено {sum(len(s) for s in missing.values())} отсутствующих якорей")
            return False
        else:
            print("✓ Все якоря найдены")
            return True


def check_quality(raw_text_by_page: Dict[int, str], cleaned_text: str, 
                 output_dir: str = "output") -> bool:
    """
    Главная функция для контроля качества.
    
    Args:
        raw_text_by_page: Raw текст по страницам
        cleaned_text: Финальный очищенный текст
        output_dir: Директория для сохранения отчета
        
    Returns:
        bool: True если все якоря найдены, False если есть пропуски
    """
    qc = QualityController()
    output_path = Path(output_dir)
    report_file = output_path / "qc_report.txt"
    
    return qc.generate_qc_report(raw_text_by_page, cleaned_text, report_file)


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Использование: python qc.py <путь_к_raw_text.json> <путь_к_cleaned.txt> [output_dir]")
        sys.exit(1)
    
    raw_json_path = sys.argv[1]
    cleaned_txt_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    with open(raw_json_path, 'r', encoding='utf-8') as f:
        raw_text_by_page = json.load(f)
    raw_text_by_page = {int(k): v for k, v in raw_text_by_page.items()}
    
    with open(cleaned_txt_path, 'r', encoding='utf-8') as f:
        cleaned_text = f.read()
    
    check_quality(raw_text_by_page, cleaned_text, output_dir)

