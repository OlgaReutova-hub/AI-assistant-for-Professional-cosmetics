# Инструкция по настройке и запуску

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание .env файла

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
OPENAI_PROXY_API_URL=https://api.proxyapi.ru/openai/v1
OPENAI_API_KEY=ваш_openai_api_ключ
OPENAI_MODEL=gpt-4o-mini
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=id_вашей_таблицы
CHROMA_DB_PATH=./chroma_db
EMBEDDING_MODEL=intfloat/multilingual-e5-large
```

### 3. Настройка Telegram бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте нового бота командой `/newbot`
3. Скопируйте полученный токен в `.env` файл

### 4. Настройка Google Sheets

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API и Google Drive API
3. Создайте сервисный аккаунт и скачайте JSON ключ
4. Переименуйте файл в `credentials.json` и поместите в корень проекта
5. Создайте Google таблицу и поделитесь ею с email сервисного аккаунта
6. Скопируйте ID таблицы в `.env` файл

### 5. Создание векторной базы данных

Перед запуском бота необходимо создать векторную базу данных из JSON файлов:

```bash
python build_rag.py
```

Скрипт создаст preview файл и после подтверждения загрузит данные в ChromaDB.

### 6. Запуск бота

```bash
python main.py
```

## Важно

⚠️ **База данных Chroma DB пуста (0 документов)**. 

Для работы системы необходимо наполнить базу данных информацией о продуктах. Используйте скрипт `build_rag.py` для создания векторной базы из JSON файлов в папке `JSON файлы`.

После наполнения базы данных бот сможет отвечать на вопросы пользователей на основе знаний из RAG системы.

## Структура проекта

```
.
├── main.py                 # Точка входа приложения
├── telegram_bot.py         # Telegram бот и обработчики
├── rag_service.py          # Работа с Chroma DB
├── openai_service.py       # Интеграция с OpenAI через ProxyApi
├── sheets_service.py       # Работа с Google Sheets
├── config.py               # Конфигурация
├── build_rag.py            # Создание векторной базы из JSON файлов
├── requirements.txt        # Зависимости
├── README.md              # Документация
├── SETUP.md               # Эта инструкция
├── start_bot.bat          # Скрипт запуска бота (Windows)
├── stop_bot.bat           # Скрипт остановки бота (Windows)
├── .env                   # Переменные окружения (создать)
├── credentials.json       # Google Sheets credentials (создать)
├── JSON файлы/            # Исходные данные в формате JSON
└── chroma_db/             # Векторная база данных
```

## Устранение проблем

### База данных пуста
- Это нормально при первом запуске
- Добавьте данные о продуктах в Chroma DB

### Ошибки импорта модулей
- Убедитесь, что установлены все зависимости: `pip install -r requirements.txt`

### Ошибки Telegram бота
- Проверьте правильность `TELEGRAM_BOT_TOKEN`
- Убедитесь, что бот запущен

### Ошибки Google Sheets
- Проверьте наличие `credentials.json`
- Убедитесь, что сервисный аккаунт имеет доступ к таблице

### Ошибки OpenAI API
- Проверьте правильность `OPENAI_API_KEY`
- Убедитесь, что прокси-сервер доступен
