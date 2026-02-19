# Инструкция по настройке Google Sheets API

## Что нужно для активации Google Sheets

Для работы с Google Sheets необходимо выполнить следующие шаги:

### 1. Создание проекта в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Войдите в свой Google аккаунт
3. Создайте новый проект:
   - Нажмите на выпадающий список проектов вверху
   - Нажмите "Новый проект"
   - Введите название проекта (например, "Telegram Bot Sheets")
   - Нажмите "Создать"

### 2. Включение необходимых API

1. В меню слева выберите **"APIs & Services"** > **"Library"**
2. Найдите и включите следующие API:
   - **Google Sheets API** - нажмите "Enable"
   - **Google Drive API** - нажмите "Enable"

### 3. Создание сервисного аккаунта

1. Перейдите в **"IAM & Admin"** > **"Service Accounts"**
2. Нажмите **"Create Service Account"** (Создать сервисный аккаунт)
3. Заполните форму:
   - **Service account name**: например, "telegram-bot-sheets"
   - **Service account ID**: будет создан автоматически
   - Нажмите **"Create and Continue"**
4. На шаге "Grant this service account access to project":
   - Роль можно пропустить или выбрать "Editor" (для тестирования)
   - Нажмите **"Continue"**
5. На шаге "Grant users access to this service account":
   - Можно пропустить
   - Нажмите **"Done"**

### 4. Создание ключа доступа (JSON)

1. В списке сервисных аккаунтов найдите созданный аккаунт
2. Нажмите на email сервисного аккаунта
3. Перейдите на вкладку **"Keys"**
4. Нажмите **"Add Key"** > **"Create new key"**
5. Выберите тип ключа: **JSON**
6. Нажмите **"Create"**
7. Файл JSON автоматически скачается на ваш компьютер

### 5. Подготовка файла credentials.json

1. Переименуйте скачанный JSON файл в `credentials.json`
2. Переместите файл `credentials.json` в корневую папку проекта:
   ```
   C:\Users\Asus\Desktop\AI assistant Alfaestet\6 ассистент с векторной базы Тест\credentials.json
   ```

### 6. Создание Google таблицы

1. Перейдите на [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу или используйте существующую
3. Скопируйте **ID таблицы** из URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
                                    ^^^^^^^^^^^^^^^^^^^^
                                    Это и есть ID таблицы
   ```
   Например, если URL такой:
   ```
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
   ```
   То ID таблицы: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

### 7. Предоставление доступа к таблице

1. Откройте созданную Google таблицу
2. Нажмите кнопку **"Настройки доступа"** (Share) в правом верхнем углу
3. В поле "Добавить людей и группы" введите **email сервисного аккаунта**
   - Email можно найти в файле `credentials.json` в поле `"client_email"`
   - Или в Google Cloud Console в разделе Service Accounts
4. Выберите уровень доступа: **"Редактор"** (Editor)
5. Снимите галочку "Уведомить людей" (если не хотите отправлять уведомление)
6. Нажмите **"Отправить"** или **"Готово"**

### 8. Настройка переменных окружения

1. Откройте файл `.env` в корне проекта
2. Добавьте или обновите следующие строки:
   ```env
   GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
   GOOGLE_SHEETS_SPREADSHEET_ID=ваш_id_таблицы_здесь
   ```
   Например:
   ```env
   GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
   GOOGLE_SHEETS_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
   ```

### 9. Проверка настройки

Запустите тест:
```bash
python sheets_service.py
```

Если все настроено правильно, вы увидите:
```
Подключено к таблице: Название вашей таблицы
```

## Структура данных в таблице

После первого использования бот автоматически создаст два листа в таблице:

### Лист "Консультации"
Столбцы:
- Дата и время
- ID пользователя
- Username
- Имя
- Телефон
- Статус

### Лист "Заказы"
Столбцы:
- Дата и время
- ID пользователя
- Username
- Информация о заказе
- Статус

## Устранение проблем

### Ошибка: "No such file or directory: 'credentials.json'"
- Убедитесь, что файл `credentials.json` находится в корне проекта
- Проверьте правильность пути в `.env` файле

### Ошибка: "Permission denied" или "Access denied"
- Проверьте, что сервисный аккаунт имеет доступ к таблице
- Убедитесь, что уровень доступа установлен как "Редактор"

### Ошибка: "Spreadsheet not found"
- Проверьте правильность `GOOGLE_SHEETS_SPREADSHEET_ID` в `.env` файле
- Убедитесь, что ID скопирован полностью из URL

### Ошибка: "API not enabled"
- Убедитесь, что Google Sheets API и Google Drive API включены в Google Cloud Console

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не публикуйте файл `credentials.json` в публичных репозиториях
- Файл уже добавлен в `.gitignore` для защиты
- Если ключ был скомпрометирован, удалите его в Google Cloud Console и создайте новый
