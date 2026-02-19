# Развертывание бота в Docker контейнере

## Требования

- Docker
- Docker Compose

## Быстрый старт

### 1. Подготовка файлов

Убедитесь, что у вас есть:
- Все Python файлы (`main.py`, `telegram_bot.py`, и т.д.)
- `requirements.txt`
- `credentials.json` (Google Sheets)
- Папка `chroma_db/` с векторной базой данных
- `.env` файл с переменными окружения

### 2. Создание .env файла

Создайте файл `.env` в корне проекта:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
OPENAI_PROXY_API_URL=https://api.proxyapi.ru/openai/v1
OPENAI_API_KEY=ваш_openai_api_ключ
OPENAI_MODEL=gpt-4o-mini
GOOGLE_SHEETS_SPREADSHEET_ID=id_вашей_таблицы
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

### 3. Запуск контейнера

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```

## Управление контейнером

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f telegram-bot

# Просмотр последних 100 строк логов
docker-compose logs --tail=100 telegram-bot

# Вход в контейнер (для отладки)
docker-compose exec telegram-bot bash

# Пересборка образа
docker-compose build --no-cache
```

## Структура volumes

- `./chroma_db` → `/app/chroma_db` - векторная база данных
- `./logs` → `/app/logs` - логи приложения
- `./credentials.json` → `/app/credentials.json` - Google Sheets credentials (read-only)

## Проверка работы

```bash
# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs telegram-bot

# Проверка базы данных (в контейнере)
docker-compose exec telegram-bot python -c "from rag_service import RAGService; r = RAGService(); print(f'Документов: {r.collection.count()}')"
```

## Обновление бота

```bash
# Остановить контейнер
docker-compose down

# Обновить код (если нужно)
# ... внести изменения в файлы ...

# Пересобрать и запустить
docker-compose up -d --build
```

## Устранение проблем

### Контейнер не запускается
```bash
# Проверьте логи
docker-compose logs telegram-bot

# Проверьте .env файл
cat .env

# Проверьте наличие credentials.json
ls -la credentials.json
```

### База данных не работает
```bash
# Проверьте, что папка chroma_db существует и содержит файлы
ls -la chroma_db/

# Проверьте права доступа
chmod -R 755 chroma_db
```

### Google Sheets не работает
```bash
# Проверьте наличие credentials.json
ls -la credentials.json

# Проверьте права доступа
chmod 600 credentials.json
```

## Production настройки

Для production рекомендуется:

1. Использовать `.env.production` файл
2. Настроить логирование в отдельный volume
3. Настроить резервное копирование `chroma_db`
4. Использовать Docker secrets для чувствительных данных

Пример `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    restart: always
    env_file:
      - .env.production
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
      - ./credentials.json:/app/credentials.json:ro
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```
