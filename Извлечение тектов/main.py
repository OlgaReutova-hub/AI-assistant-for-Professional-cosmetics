"""
Главный скрипт для извлечения, очистки и сборки текста из PDF-каталогов косметики.
"""

import sys
import io
from pathlib import Path
from extractor import extract_pdf
from cleaner import clean_text
from assembler import assemble_text
from qc import check_quality

# Устанавливаем UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def process_pdf_catalog(pdf_path: str, output_dir: str = "output"):
    """
    Обрабатывает PDF-каталог через все этапы:
    1. Extractor - извлечение raw текста
    2. Cleaner - очистка от артефактов
    3. Assembler - сборка в логические блоки
    4. QC - контроль качества
    """
    print("=" * 80)
    print("ОБРАБОТКА PDF-КАТАЛОГА")
    print("=" * 80)
    print(f"Входной файл: {pdf_path}")
    print(f"Выходная директория: {output_dir}")
    print()
    
    # Создаем выходную директорию
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Этап 1: Извлечение
    print("\n[ЭТАП 1] ИЗВЛЕЧЕНИЕ RAW ТЕКСТА")
    print("-" * 80)
    control_dir = output_path / "stage1_raw_text_control"
    raw_text_by_page = extract_pdf(pdf_path, str(control_dir))
    print(f"✓ Извлечено {len(raw_text_by_page)} страниц")
    
    # Этап 2: Очистка
    print("\n[ЭТАП 2] ОЧИСТКА ОТ АРТЕФАКТОВ")
    print("-" * 80)
    cleaned_by_page = clean_text(raw_text_by_page)
    print(f"✓ Очищено {len(cleaned_by_page)} страниц")
    
    # Этап 3: Сборка
    print("\n[ЭТАП 3] СБОРКА В ЛОГИЧЕСКИЕ БЛОКИ")
    print("-" * 80)
    blocks = assemble_text(cleaned_by_page)
    print(f"✓ Собрано {len(blocks)} блоков")
    
    # Создаем финальный cleaned.txt
    print("\n[ФИНАЛЬНЫЙ ЭТАП] СОЗДАНИЕ CLEANED.TXT")
    print("-" * 80)
    cleaned_txt_path = output_path / "cleaned.txt"
    with open(cleaned_txt_path, 'w', encoding='utf-8') as f:
        for i, block in enumerate(blocks):
            if i > 0:
                f.write("\n\n")
            f.write(block)
    print(f"✓ Финальный текст сохранен в: {cleaned_txt_path}")
    
    # Этап 4: Контроль качества
    print("\n[ЭТАП 4] КОНТРОЛЬ КАЧЕСТВА")
    print("-" * 80)
    with open(cleaned_txt_path, 'r', encoding='utf-8') as f:
        cleaned_text = f.read()
    
    # Для QC нужен полный текст из raw (извлекаем из структуры)
    raw_text_by_page_for_qc = {}
    for page_num, page_data in raw_text_by_page.items():
        raw_text_by_page_for_qc[page_num] = page_data.get('full_text', '')
    
    qc_passed = check_quality(raw_text_by_page_for_qc, cleaned_text, str(output_path))
    
    # Итоги
    print("\n" + "=" * 80)
    print("ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 80)
    print(f"Финальный файл: {cleaned_txt_path}")
    print(f"Отчет QC: {output_path / 'qc_report.txt'}")
    print()
    
    if qc_passed:
        print("✓ Контроль качества пройден: все якоря найдены")
    else:
        print("⚠ Контроль качества: обнаружены отсутствующие якоря")
        print("  Проверьте qc_report.txt для деталей")
    
    return qc_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python main.py <путь_к_pdf> [output_dir]")
        print()
        print("Пример:")
        print("  python main.py 'каталог.pdf'")
        print("  python main.py 'каталог.pdf' output")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    try:
        process_pdf_catalog(pdf_path, output_dir)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

