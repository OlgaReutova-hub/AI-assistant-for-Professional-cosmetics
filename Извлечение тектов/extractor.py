"""
Extractor Module
Извлекает raw текст из PDF файлов по страницам.
Также извлекает заголовки продуктов из левого верхнего угла (ROI).
Детерминированный, без использования LLM.
"""

import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, Tuple, Optional
import re
import io

# OCR импорты (опциональные)
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class PDFExtractor:
    """Извлекает текст из PDF файлов с fallback на pdfplumber."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
    def extract_top_left_roi_text(self, page) -> Tuple[str, str]:
        """
        Извлекает текст из левого верхнего угла страницы (ROI).
        ROI: левая часть страницы (например, 40-50% слева), верхняя часть (первые 20-30%).
        
        Returns:
            Tuple[str, str]: (raw_text, normalized_text)
        """
        try:
            # Получаем размеры страницы
            rect = page.rect
            
            # Определяем ROI: левая 50% страницы, верхние 25%
            roi_width = rect.width * 0.5
            roi_height = rect.height * 0.25
            
            roi_rect = fitz.Rect(
                0,                        # x0 (левая граница - начало страницы)
                0,                        # y0 (верхняя граница)
                roi_width,                # x1 (правая граница ROI)
                roi_height                # y1 (нижняя граница)
            )
            
            # Извлекаем текст из ROI
            raw_text = page.get_text("text", clip=roi_rect)
            
            # Нормализуем текст
            normalized = self.normalize_title(raw_text)
            
            return raw_text, normalized
        except Exception as e:
            print(f"Ошибка при извлечении ROI: {e}")
            return "", ""
    
    def find_product_title_in_text(self, full_text: str) -> Optional[Tuple[str, str]]:
        """
        Ищет название продукта в тексте страницы по паттерну "RU / EN".
        Название может быть разбито на несколько строк.
        
        Args:
            full_text: Полный текст страницы
            
        Returns:
            Optional[Tuple[str, str]]: (title, composition) или None
        """
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # Ищем паттерн "RU / EN" или "RU/EN", где название может быть разбито на строки
        # Собираем строки до и после слеша
        for i in range(len(lines)):
            line = lines[i]
            
            # Проверяем, есть ли в строке слеш с кириллицей слева и латиницей справа
            if '/' in line:
                parts = line.split('/', 1)
                if len(parts) == 2:
                    left_part = parts[0].strip()
                    right_part = parts[1].strip()
                    
                    # Проверяем, что слева кириллица, справа латиница
                    has_cyrillic = bool(re.search(r'[А-ЯЁа-яё]', left_part))
                    has_latin = bool(re.search(r'[a-zA-Z]', right_part))
                    
                    if has_cyrillic and has_latin:
                        # Собираем полное русское название (может быть на предыдущих строках)
                        russian_parts = []
                        
                        # Идем назад, собирая русские строки
                        for j in range(i - 1, max(-1, i - 5), -1):
                            prev_line = lines[j].strip()
                            if not prev_line:
                                break
                            # Если строка содержит только кириллицу или начинается с заглавной
                            if re.search(r'^[А-ЯЁа-яё]', prev_line) and not re.search(r'[a-zA-Z]', prev_line):
                                russian_parts.insert(0, prev_line)
                            else:
                                break
                        
                        # Добавляем текущую часть
                        russian_parts.append(left_part)
                        russian = ' '.join(russian_parts)
                        
                        # Собираем полное английское название (может быть на следующих строках)
                        english_parts = [right_part]
                        
                        # Идем вперед, собирая английские строки
                        for j in range(i + 1, min(len(lines), i + 4)):
                            next_line = lines[j].strip()
                            if not next_line:
                                break
                            # Если строка содержит только латиницу
                            if re.search(r'^[a-zA-Z]', next_line) and not re.search(r'[А-ЯЁа-яё]', next_line):
                                # Пропускаем слишком длинные строки (описание)
                                if len(next_line) > 100:
                                    break
                                english_parts.append(next_line)
                            else:
                                break
                        
                        english = ' '.join(english_parts)
                        
                        # Пропускаем слишком короткие или явно не названия продуктов
                        if len(russian) < 5 or len(english) < 3:
                            continue
                        
                        # Пропускаем служебные строки
                        if any(skip in russian.lower() for skip in ['объем', 'артикул', 'содержание', 'страница', 'линия']):
                            continue
                        
                        title = f"{russian} / {english}"
                        
                        # Ищем состав после английского названия (следующие 2-4 строки)
                        composition = ""
                        search_start = i + len(english_parts)
                        search_end = min(search_start + 4, len(lines))
                        
                        composition_lines = []
                        for j in range(search_start, search_end):
                            comp_line = lines[j].strip()
                            if not comp_line:
                                continue
                            # Пропускаем строки с артикулом, объемом
                            if re.search(r'артикул|объем|мл|ml|для|предназначен', comp_line, re.IGNORECASE):
                                break
                            # Пропускаем слишком длинные строки (описание)
                            if len(comp_line) > 120:
                                break
                            # Если строка содержит ингредиенты
                            if re.search(r'экстракт|содержание|масло|кислот|витамин|липид|пантенол|триклозан', comp_line, re.IGNORECASE):
                                composition_lines.append(comp_line)
                                if len(composition_lines) >= 2:  # Берем до 2 строк состава
                                    break
                        
                        composition = ' '.join(composition_lines)
                        
                        return title, composition
        
        return None
    
    def extract_composition_text(self, page) -> str:
        """
        Извлекает текст состава (ингредиентов) из области ниже названия.
        ROI: левая часть страницы (40-50% слева), область от 20% до 40% высоты страницы.
        
        Returns:
            str: Текст состава
        """
        try:
            # Получаем размеры страницы
            rect = page.rect
            
            # Определяем ROI: левая 50% страницы, область от 20% до 40% высоты
            roi_width = rect.width * 0.5
            roi_y0 = rect.height * 0.20
            roi_y1 = rect.height * 0.40
            
            roi_rect = fitz.Rect(
                0,                        # x0 (левая граница)
                roi_y0,                   # y0 (верхняя граница - 20% от высоты)
                roi_width,                # x1 (правая граница ROI)
                roi_y1                    # y1 (нижняя граница - 40% от высоты)
            )
            
            # Извлекаем текст из ROI
            composition_text = page.get_text("text", clip=roi_rect)
            
            return composition_text.strip()
        except Exception as e:
            print(f"Ошибка при извлечении состава: {e}")
            return ""
    
    def normalize_title(self, raw_title: str) -> str:
        """
        Нормализует заголовок продукта из ROI.
        
        Правила:
        - Убрать пустые строки и мусор
        - Если 2 строки (RU+EN или EN+RU), собрать в формат: RU / EN
        """
        if not raw_title:
            return ""
        
        lines = [line.strip() for line in raw_title.split('\n') if line.strip()]
        
        # Убираем мусор (очень короткие строки, содержащие только спецсимволы)
        filtered_lines = []
        for line in lines:
            # Пропускаем строки, состоящие только из спецсимволов или цифр
            if len(line) < 2:
                continue
            # Пропускаем строки с только цифрами и спецсимволами
            if re.match(r'^[\d\s\-\.]+$', line):
                continue
            filtered_lines.append(line)
        
        if not filtered_lines:
            return ""
        
        # Если одна строка - проверяем, есть ли в ней формат "RU / EN"
        if len(filtered_lines) == 1:
            line = filtered_lines[0]
            # Если уже есть формат с слешем - возвращаем как есть
            if '/' in line and re.search(r'[А-ЯЁа-яё]', line) and re.search(r'[a-zA-Z]', line):
                return line.strip()
            return line.strip()
        
        # Если две или больше строк - пытаемся найти пару RU + EN
        russian_line = None
        english_line = None
        
        for line in filtered_lines:
            # Проверяем, есть ли кириллица
            has_cyrillic = bool(re.search(r'[А-ЯЁа-яё]', line))
            # Проверяем, есть ли латиница (но нет кириллицы)
            has_latin_only = bool(re.search(r'[a-zA-Z]', line) and not re.search(r'[А-ЯЁа-яё]', line))
            
            if has_cyrillic and not russian_line:
                russian_line = line
            elif has_latin_only and not english_line:
                english_line = line
        
        # Если нашли обе строки - формируем заголовок
        if russian_line and english_line:
            # Определяем порядок (обычно RU идет первым, но может быть наоборот)
            ru_idx = filtered_lines.index(russian_line)
            en_idx = filtered_lines.index(english_line)
            
            if ru_idx < en_idx:
                return f"{russian_line} / {english_line}"
            else:
                return f"{russian_line} / {english_line}"  # Всегда RU / EN
        
        # Если не удалось определить - возвращаем первую строку
        return filtered_lines[0]
    
    def extract_with_pymupdf(self) -> Dict[int, Dict[str, str]]:
        """
        Извлечение текста с помощью PyMuPDF (fitz).
        
        Returns:
            Dict[int, Dict[str, str]]: {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
        """
        result = {}
        
        try:
            doc = fitz.open(str(self.pdf_path))
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Полный текст страницы
                full_text = page.get_text()
                
                # Сначала пытаемся найти название продукта в тексте страницы
                title_from_text = self.find_product_title_in_text(full_text)
                
                if title_from_text:
                    # Нашли название в тексте
                    title, composition = title_from_text
                    roi_raw = title
                    roi_norm = title
                else:
                    # Используем ROI из левого верхнего угла
                    roi_raw, roi_norm = self.extract_top_left_roi_text(page)
                    # Текст состава (ингредиентов)
                    composition = self.extract_composition_text(page)
                
                result[page_num] = {
                    'full_text': full_text,
                    'top_left_title_raw': roi_raw,
                    'top_left_title_norm': roi_norm,
                    'composition': composition
                }
            doc.close()
            return result
        except Exception as e:
            print(f"Ошибка при извлечении через PyMuPDF: {e}")
            return {}
    
    def extract_with_ocr(self) -> Dict[int, Dict[str, str]]:
        """
        Извлечение текста с помощью OCR (Tesseract).
        Используется как последний fallback для сканированных PDF.
        
        Returns:
            Dict[int, Dict[str, str]]: {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
        """
        if not OCR_AVAILABLE:
            raise Exception("OCR не доступен. Установите pytesseract и Pillow: pip install pytesseract Pillow")
        
        result = {}
        
        try:
            doc = fitz.open(str(self.pdf_path))
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Конвертируем страницу в изображение
                # Увеличиваем разрешение для лучшего качества OCR
                zoom = 2.0  # Увеличение для лучшего качества
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Конвертируем в PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Извлекаем текст через OCR (русский и английский языки)
                try:
                    # Пробуем с русским и английским языками
                    full_text = pytesseract.image_to_string(img, lang='rus+eng')
                except:
                    # Если русский язык не установлен, используем только английский
                    try:
                        full_text = pytesseract.image_to_string(img, lang='eng')
                    except:
                        # Если ничего не работает, используем без указания языка
                        full_text = pytesseract.image_to_string(img)
                
                # Пытаемся найти название продукта в тексте
                title_from_text = self.find_product_title_in_text(full_text)
                
                if title_from_text:
                    title, composition = title_from_text
                    roi_raw = title
                    roi_norm = title
                else:
                    # Извлекаем ROI из левого верхнего угла
                    # Обрезаем изображение для ROI
                    rect = page.rect
                    roi_width = int(rect.width * zoom * 0.5)
                    roi_height = int(rect.height * zoom * 0.25)
                    roi_img = img.crop((0, 0, roi_width, roi_height))
                    
                    try:
                        roi_raw = pytesseract.image_to_string(roi_img, lang='rus+eng')
                    except:
                        try:
                            roi_raw = pytesseract.image_to_string(roi_img, lang='eng')
                        except:
                            roi_raw = pytesseract.image_to_string(roi_img)
                    
                    roi_norm = self.normalize_title(roi_raw)
                    
                    # Извлекаем состав (ингредиенты)
                    composition_y0 = int(rect.height * zoom * 0.20)
                    composition_y1 = int(rect.height * zoom * 0.40)
                    composition_img = img.crop((0, composition_y0, roi_width, composition_y1))
                    
                    try:
                        composition = pytesseract.image_to_string(composition_img, lang='rus+eng')
                    except:
                        try:
                            composition = pytesseract.image_to_string(composition_img, lang='eng')
                        except:
                            composition = pytesseract.image_to_string(composition_img)
                    
                    composition = composition.strip()
                
                result[page_num] = {
                    'full_text': full_text,
                    'top_left_title_raw': roi_raw if not title_from_text else title,
                    'top_left_title_norm': roi_norm if not title_from_text else title,
                    'composition': composition if not title_from_text else composition
                }
            
            doc.close()
            return result
        except Exception as e:
            print(f"Ошибка при извлечении через OCR: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def extract_with_pdfplumber(self) -> Dict[int, Dict[str, str]]:
        """
        Извлечение текста с помощью pdfplumber (fallback).
        
        Returns:
            Dict[int, Dict[str, str]]: {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
        """
        result = {}
        
        try:
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Полный текст страницы
                    full_text = page.extract_text() or ""
                    
                    # Сначала пытаемся найти название продукта в тексте страницы
                    title_from_text = self.find_product_title_in_text(full_text)
                    
                    if title_from_text:
                        # Нашли название в тексте
                        title, composition = title_from_text
                        roi_raw = title
                        roi_norm = title
                    else:
                        # Извлекаем текст из левого верхнего угла
                        # ROI: левая 50%, верхние 25%
                        page_width = page.width
                        page_height = page.height
                        roi_x1 = page_width * 0.5
                        roi_y1 = page_height * 0.25
                        
                        roi_bbox = (0, 0, roi_x1, roi_y1)
                        roi_page = page.crop(roi_bbox)
                        roi_raw = roi_page.extract_text() or ""
                        
                        # Нормализуем
                        roi_norm = self.normalize_title(roi_raw)
                        
                        # Извлекаем состав (ингредиенты)
                        composition_y0 = page_height * 0.20
                        composition_y1 = page_height * 0.40
                        composition_bbox = (0, composition_y0, roi_x1, composition_y1)
                        composition_page = page.crop(composition_bbox)
                        composition = composition_page.extract_text() or ""
                    
                    result[page_num] = {
                        'full_text': full_text,
                        'top_left_title_raw': roi_raw,
                        'top_left_title_norm': roi_norm,
                        'composition': composition.strip()
                    }
            return result
        except Exception as e:
            print(f"Ошибка при извлечении через pdfplumber: {e}")
            return {}
    
    def extract(self) -> Dict[int, Dict[str, str]]:
        """
        Извлекает текст из PDF.
        Пробует PyMuPDF, при неудаче использует pdfplumber.
        
        Returns:
            Dict[int, Dict[str, str]]: {
                page_num: {
                    'full_text': str,
                    'top_left_title_raw': str,
                    'top_left_title_norm': str,
                    'composition': str
                }
            }
        """
        print(f"Извлечение текста из: {self.pdf_path.name}")
        
        # Пробуем PyMuPDF
        result = self.extract_with_pymupdf()
        
        if result and any(data.get('full_text', '').strip() for data in result.values()):
            pages_with_titles = sum(1 for data in result.values() if data.get('top_left_title_norm'))
            print(f"Успешно извлечено {len(result)} страниц через PyMuPDF")
            print(f"  Найдено заголовков в ROI: {pages_with_titles}")
            return result
        
        # Fallback на pdfplumber
        print("Пробуем pdfplumber как fallback...")
        result = self.extract_with_pdfplumber()
        
        if result and any(data.get('full_text', '').strip() for data in result.values()):
            pages_with_titles = sum(1 for data in result.values() if data.get('top_left_title_norm'))
            print(f"Успешно извлечено {len(result)} страниц через pdfplumber")
            print(f"  Найдено заголовков в ROI: {pages_with_titles}")
            return result
        
        # Fallback на OCR (если доступен)
        if OCR_AVAILABLE:
            print("Пробуем OCR как последний fallback...")
            try:
                result = self.extract_with_ocr()
                
                if result and any(data.get('full_text', '').strip() for data in result.values()):
                    pages_with_titles = sum(1 for data in result.values() if data.get('top_left_title_norm'))
                    print(f"Успешно извлечено {len(result)} страниц через OCR")
                    print(f"  Найдено заголовков в ROI: {pages_with_titles}")
                    return result
            except Exception as e:
                error_msg = str(e)
                if "TesseractNotFoundError" in error_msg or "tesseract" in error_msg.lower():
                    print("⚠ Tesseract OCR не установлен в системе.")
                    print("  Для установки на Windows:")
                    print("  1. Скачайте установщик: https://github.com/UB-Mannheim/tesseract/wiki")
                    print("  2. Или установите через chocolatey: choco install tesseract")
                    print("  3. После установки добавьте Tesseract в PATH или укажите путь в коде")
                else:
                    print(f"Ошибка при использовании OCR: {e}")
        else:
            print("OCR не доступен. Установите pytesseract и Pillow для поддержки сканированных PDF.")
        
        raise Exception("Не удалось извлечь текст ни одним методом. Если PDF содержит изображения, установите Tesseract OCR.")
    
def extract_pdf(pdf_path: str, output_dir: str = None) -> Dict[int, Dict[str, str]]:
    """
    Главная функция для извлечения текста из PDF.
    
    Args:
        pdf_path: Путь к PDF файлу
        output_dir: Опционально - директория для сохранения raw текста для контроля
        
    Returns:
        Dict[int, Dict[str, str]]: {
            page_num: {
                'full_text': str,
                'top_left_title_raw': str,
                'top_left_title_norm': str,
                'composition': str
            }
        }
    """
    extractor = PDFExtractor(pdf_path)
    page_data = extractor.extract()
    
    # Сохраняем raw текст для визуального контроля, если указана директория
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем объединенный файл с полным текстом
        combined_file = output_path / "raw_text_for_control.txt"
        with open(combined_file, 'w', encoding='utf-8') as f:
            for page_num in sorted(page_data.keys()):
                data = page_data[page_num]
                f.write(f"\n{'='*80}\n")
                f.write(f"СТРАНИЦА {page_num + 1}\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"Заголовок из ROI (raw): {data.get('top_left_title_raw', '')}\n")
                f.write(f"Заголовок из ROI (norm): {data.get('top_left_title_norm', '')}\n")
                f.write(f"Состав: {data.get('composition', '')}\n")
                f.write(f"\n--- Полный текст страницы ---\n\n")
                f.write(data.get('full_text', ''))
                f.write("\n")
        
        print(f"Raw текст для контроля сохранен в: {combined_file}")
    
    return page_data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python extractor.py <путь_к_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    raw_text_by_page = extract_pdf(pdf_path, output_dir)
    print(f"Извлечено {len(raw_text_by_page)} страниц")

