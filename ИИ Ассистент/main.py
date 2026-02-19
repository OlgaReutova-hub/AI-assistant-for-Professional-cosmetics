"""
Основной файл запуска приложения
"""
import logging
from telegram_bot import main as run_bot

# Настройка логирования
# Логи будут выводиться в консоль И сохраняться в файл bot.log
import os
from datetime import datetime

# Создаем директорию для логов, если её нет
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Имя файла лога с датой
log_filename = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

# Настройка логирования: вывод в консоль и в файл
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),  # Сохранение в файл
        logging.StreamHandler()  # Вывод в консоль
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Запуск приложения...")
        run_bot()
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        error_msg = str(e)
        if "Conflict" in error_msg or "getUpdates" in error_msg:
            logger.error("=" * 60)
            logger.error("ОШИБКА: Запущено несколько экземпляров бота!")
            logger.error("=" * 60)
            logger.error("Решение:")
            logger.error("1. Остановите все другие экземпляры бота")
            logger.error("2. Или используйте stop_bot.bat для остановки всех процессов")
            logger.error("3. Затем запустите бота снова")
            logger.error("=" * 60)
        else:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
