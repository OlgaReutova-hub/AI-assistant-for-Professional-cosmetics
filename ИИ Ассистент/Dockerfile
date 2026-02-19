# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем все файлы приложения
COPY main.py telegram_bot.py rag_service.py openai_service.py sheets_service.py config.py ./

# Создаем директории для данных
RUN mkdir -p /app/chroma_db /app/logs

# Устанавливаем переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV CHROMA_DB_PATH=/app/chroma_db
ENV LOG_DIR=/app/logs

# Запускаем бота
CMD ["python", "main.py"]
