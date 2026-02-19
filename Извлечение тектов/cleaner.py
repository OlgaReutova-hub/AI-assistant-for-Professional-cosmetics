"""
Cleaner Module
Очищает текст от артефактов PDF верстки.
Только правила, без перефразирования или сокращений.
"""

import re
from typing import Dict


class TextCleaner:
    """Очищает текст от артефактов верстки PDF."""
    
    def __init__(self):
        # Паттерны для удаления номеров страниц
        self.page_number_patterns = [
            r'^\s*\d+\s*$',  # Отдельная строка с числом
            r'^\s*стр\.?\s*\d+\s*$',  # "стр. 5"
            r'^\s*page\s+\d+\s*$',  # "page 5"
            r'^\s*\d+\s*/\s*\d+\s*$',  # "5 / 10"
        ]
    
    def fix_hyphenation(self, text: str) -> str:
        """
        Склеивает переносы слов: гидро- лизованный → гидролизованный.
        Также убирает дефисы внутри слов.
        """
        # Паттерн: слово с дефисом в конце строки, затем пробелы и продолжение
        # Учитываем, что может быть перенос строки или пробелы
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        
        # Также обрабатываем случаи с переносом строки
        text = re.sub(r'(\w+)-\n\s*(\w+)', r'\1\2', text)
        
        # Убираем дефисы внутри слов (когда дефис окружен буквами с обеих сторон)
        # Но сохраняем дефисы в составных словах типа "24-часовой" или "А-витамин"
        # Убираем только те, где дефис разделяет части одного слова
        # Паттерн: буква-пробел-буква (перенос слова)
        text = re.sub(r'([а-яёa-z])-\s+([а-яёa-z])', r'\1\2', text, flags=re.IGNORECASE)
        text = re.sub(r'([а-яёa-z])-\n\s*([а-яёa-z])', r'\1\2', text, flags=re.IGNORECASE)
        
        return text
    
    def remove_list_markers(self, text: str) -> str:
        """
        Удаляет маркеры списка в начале строк.
        Маркеры: •, -, *, цифры с точкой/скобкой, и т.д.
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Удаляем маркеры списка в начале строки
            # • (bullet point) - удаляем маркер и все пробелы/табы после него
            line = re.sub(r'^[\s\t]*[•·▪▫][\s\t]+', '', line)
            # - или * в начале строки (но не минус в середине), должен быть пробел/таб после
            line = re.sub(r'^[\s\t]*[-*][\s\t]+', '', line)
            # Цифры с точкой или скобкой (1. 1) 1-) с пробелами/табами после
            line = re.sub(r'^[\s\t]*\d+[\.\)\-][\s\t]+', '', line)
            # Римские цифры с точкой (I. II. III.) с пробелами/табами после
            line = re.sub(r'^[\s\t]*[IVX]+[\.\)][\s\t]+', '', line, flags=re.IGNORECASE)
            # Буквы с точкой или скобкой (a. b) A-) с пробелами/табами после
            line = re.sub(r'^[\s\t]*[а-яёa-z][\.\)\-][\s\t]+', '', line, flags=re.IGNORECASE)
            
            # Убираем начальные табуляции и пробелы (остатки после удаления маркера)
            line = line.lstrip('\t ')
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def merge_lines_in_sentences(self, text: str) -> str:
        """
        Склеивает строки внутри предложений, где перенос не означает новый абзац.
        Правило: если строка не заканчивается на .!?;: и следующая не начинается с заглавной,
        то это продолжение предложения.
        """
        lines = text.split('\n')
        merged = []
        i = 0
        
        while i < len(lines):
            current = lines[i].strip()
            if not current:
                merged.append('')
                i += 1
                continue
            
            # Если строка заканчивается на знак конца предложения - это конец абзаца
            if re.search(r'[.!?]\s*$', current):
                merged.append(current)
                i += 1
                continue
            
            # Если строка заканчивается на : или ; - возможно конец секции, но не всегда
            # Проверяем следующую строку
            
            # Если следующая строка начинается с заглавной и это не цифра - возможен новый абзац
            # Но также проверяем, не является ли это частью списка или продолжением
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not next_line:
                    merged.append(current)
                    i += 1
                    continue
                
                # Если следующая строка начинается с заглавной буквы (не цифра)
                # и текущая строка заканчивается на : или ; - это новый абзац
                if (next_line[0].isupper() and not next_line[0].isdigit() and 
                    re.search(r'[;:]\s*$', current)):
                    merged.append(current)
                    i += 1
                    continue
                
                # Если следующая строка начинается с заглавной и текущая не заканчивается на запятую
                # и следующая не является продолжением (не начинается с маленькой буквы после пробела)
                if (next_line[0].isupper() and not next_line[0].isdigit() and
                    not current.endswith(',') and
                    not re.search(r'^[А-ЯЁA-Z]', next_line[:3])):  # Более строгая проверка
                    # Но если это подзаголовок (короткая строка) - не склеиваем
                    if len(current) < 50:  # Подзаголовки обычно короткие
                        merged.append(current)
                        i += 1
                        continue
            
            # Иначе склеиваем со следующей строкой
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line:
                    # Склеиваем через пробел
                    if current and not current.endswith(' ') and not next_line.startswith(' '):
                        current = current + ' ' + next_line
                    else:
                        current = (current.rstrip() + ' ' + next_line.lstrip()).strip()
                    i += 2
                    # Продолжаем склеивать, если нужно
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if not next_line:
                            break
                        # Если следующая строка заканчивается на .!? - склеиваем и останавливаемся
                        if re.search(r'[.!?]\s*$', next_line):
                            current = current + ' ' + next_line
                            i += 1
                            break
                        # Если следующая строка начинается с заглавной (не цифра) - останавливаемся
                        if next_line[0].isupper() and not next_line[0].isdigit():
                            # Но если это очень короткая строка (возможно подзаголовок) - останавливаемся
                            if len(next_line) < 50:
                                break
                        current = current + ' ' + next_line
                        i += 1
                    merged.append(current)
                else:
                    merged.append(current)
                    i += 1
            else:
                merged.append(current)
                i += 1
        
        return '\n'.join(merged)
    
    def remove_page_numbers(self, text: str) -> str:
        """Удаляет номера страниц."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            is_page_number = False
            for pattern in self.page_number_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_page_number = True
                    break
            if not is_page_number:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_text(self, page_data: Dict[int, Dict[str, str]]) -> Dict[int, Dict[str, str]]:
        """
        Очищает текст от артефактов верстки.
        
        Args:
            page_data: Словарь {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
            
        Returns:
            Dict[int, Dict[str, str]]: Та же структура с очищенным full_text
        """
        print("Очистка текста от артефактов верстки...")
        
        cleaned_by_page = {}
        
        for page_num, data in page_data.items():
            # Применяем очистку только к full_text, title и composition оставляем как есть
            text = data.get('full_text', '')
            
            # Применяем очистку по порядку
            cleaned = text
            
            # 1. Исправляем переносы слов и убираем дефисы внутри слов
            cleaned = self.fix_hyphenation(cleaned)
            
            # 2. Удаляем маркеры списка
            cleaned = self.remove_list_markers(cleaned)
            
            # 3. Удаляем номера страниц
            cleaned = self.remove_page_numbers(cleaned)
            
            # 4. Удаляем декоративный элемент "skin skin ess ess ent ent ials ials"
            cleaned = re.sub(r'skin\s+skin\s+ess\s+ess\s+ent\s+ent\s+ials\s+ials', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'skin\s+skin\s+ess\s+ess\s+ent\s+ent\s+ials\s+ials\s*', '', cleaned, flags=re.IGNORECASE)
            
            # 5. НЕ удаляем повторяющиеся заголовки/футеры (оставляем как есть)
            
            # 6. Склеиваем строки внутри предложений
            cleaned = self.merge_lines_in_sentences(cleaned)
            
            # Сохраняем структуру данных
            cleaned_by_page[page_num] = {
                'full_text': cleaned,
                'top_left_title_raw': data.get('top_left_title_raw', ''),
                'top_left_title_norm': data.get('top_left_title_norm', ''),
                'composition': data.get('composition', '')
            }
        
        print(f"Очистка завершена для {len(cleaned_by_page)} страниц")
        return cleaned_by_page
    
def clean_text(page_data: Dict[int, Dict[str, str]]) -> Dict[int, Dict[str, str]]:
    """
    Главная функция для очистки текста.
    
    Args:
        page_data: Словарь {
            page_num: {
                'full_text': str,
                'top_left_title_raw': str,
                'top_left_title_norm': str,
                'composition': str
            }
        }
        
    Returns:
        Dict[int, Dict[str, str]]: Та же структура с очищенным full_text
    """
    cleaner = TextCleaner()
    cleaned_by_page = cleaner.clean_text(page_data)
    
    return cleaned_by_page


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Использование: python cleaner.py <путь_к_raw_text.json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_text_by_page = json.load(f)
    
    # Конвертируем ключи обратно в int
    raw_text_by_page = {int(k): v for k, v in raw_text_by_page.items()}
    
    cleaned_by_page = clean_text(raw_text_by_page)
    print(f"Очистка завершена для {len(cleaned_by_page)} страниц")

