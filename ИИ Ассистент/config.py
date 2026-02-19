"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI Proxy API
OPENAI_PROXY_API_URL = os.getenv("OPENAI_PROXY_API_URL", "https://api.proxyapi.ru/openai/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Google Sheets API
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

# Chroma DB
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../chroma_db")

# Embedding Model
# Используем более легкую модель по умолчанию для экономии памяти
# Альтернативы: "intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# Проверка обязательных переменных (только предупреждения для тестирования)
if not TELEGRAM_BOT_TOKEN:
    import os
    if not os.getenv("SKIP_ENV_CHECK"):  # Позволяем пропустить проверку при тестировании
        print("Предупреждение: TELEGRAM_BOT_TOKEN не установлен в .env файле")
if not OPENAI_API_KEY:
    import os
    if not os.getenv("SKIP_ENV_CHECK"):
        print("Предупреждение: OPENAI_API_KEY не установлен в .env файле")
if not GOOGLE_SHEETS_SPREADSHEET_ID:
    print("Предупреждение: GOOGLE_SHEETS_SPREADSHEET_ID не установлен")
