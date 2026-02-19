"""
Модуль для работы с Google Sheets API
"""
import logging

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("Предупреждение: gspread не установлен. Google Sheets функциональность будет недоступна.")

import config
from datetime import datetime
from typing import Dict, Optional

# Настройка логирования
logger = logging.getLogger(__name__)


class SheetsService:
    """Сервис для работы с Google Sheets"""
    
    def __init__(self):
        """Инициализация Google Sheets сервиса"""
        if not GSPREAD_AVAILABLE:
            self.client = None
            self.sheet = None
            return
        
        try:
            # Настройка доступа к Google Sheets API
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=scope
            )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet_id = config.GOOGLE_SHEETS_SPREADSHEET_ID
            
            if self.spreadsheet_id:
                self.sheet = self.client.open_by_key(self.spreadsheet_id)
            else:
                self.sheet = None
                print("Предупреждение: GOOGLE_SHEETS_SPREADSHEET_ID не установлен")
                
        except FileNotFoundError as e:
            print(f"[ERROR] Ошибка: Файл credentials не найден: {e}")
            print(f"   Проверьте путь: {config.GOOGLE_SHEETS_CREDENTIALS_FILE}")
            self.client = None
            self.sheet = None
        except Exception as e:
            print(f"[ERROR] Ошибка при инициализации Google Sheets: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.client = None
            self.sheet = None
    
    def save_consultation_request(self, user_id: int, name: str, phone: str, username: Optional[str] = None):
        """
        Сохранить заявку на консультацию
        
        Args:
            user_id: ID пользователя Telegram
            name: Имя пользователя
            phone: Номер телефона
            username: Username пользователя (опционально)
        """
        if not self.sheet:
            print("[WARNING] Google Sheets не настроен - заявка не будет сохранена")
            return False
        
        try:
            # Получаем или создаем лист "Консультации"
            try:
                worksheet = self.sheet.worksheet("Консультации")
            except gspread.exceptions.WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(
                    title="Консультации",
                    rows=1000,
                    cols=10
                )
                # Добавляем заголовки
                worksheet.append_row([
                    "Дата и время",
                    "ID пользователя",
                    "Username",
                    "Имя",
                    "Телефон",
                    "Статус"
                ])
            
            # Добавляем заявку
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.append_row([
                timestamp,
                str(user_id),
                username or "",
                name,
                phone,
                "Новая"
            ])
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении заявки на консультацию: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_order_request(self, user_id: int, order_info: str, username: Optional[str] = None):
        """
        Сохранить заявку на заказ
        
        Args:
            user_id: ID пользователя Telegram
            order_info: Информация о заказе
            username: Username пользователя (опционально)
        """
        if not self.sheet:
            print("[WARNING] Google Sheets не настроен - заявка не будет сохранена")
            return False
        
        try:
            # Получаем или создаем лист "Заказы"
            try:
                worksheet = self.sheet.worksheet("Заказы")
            except gspread.exceptions.WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(
                    title="Заказы",
                    rows=1000,
                    cols=10
                )
                # Добавляем заголовки
                worksheet.append_row([
                    "Дата и время",
                    "ID пользователя",
                    "Username",
                    "Информация о заказе",
                    "Статус"
                ])
            
            # Добавляем заявку
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.append_row([
                timestamp,
                str(user_id),
                username or "",
                order_info,
                "Новый"
            ])
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении заявки на заказ: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_dialog_message(
        self, 
        user_id: int, 
        user_message: str, 
        bot_response: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ):
        """
        Сохранить сообщение диалога в Google Sheets
        
        Args:
            user_id: ID пользователя Telegram
            user_message: Сообщение пользователя
            bot_response: Ответ бота
            username: Username пользователя (опционально)
            first_name: Имя пользователя (опционально)
            last_name: Фамилия пользователя (опционально)
        """
        logger.info(f"[DEBUG] save_dialog_message вызвана: user_id={user_id}, username={username}, first_name={first_name}")
        
        if not self.sheet:
            # Если Google Sheets не настроен, просто возвращаем False без ошибки
            logger.warning(f"[WARNING] Google Sheets не настроен - диалог не будет сохранен для user_id={user_id}")
            logger.debug(f"[DEBUG] self.sheet = {self.sheet}, self.client = {self.client}")
            return False
        
        try:
            logger.debug(f"[DEBUG] Пытаемся получить или создать лист 'Диалоги'")
            # Получаем или создаем лист "Диалоги"
            try:
                worksheet = self.sheet.worksheet("Диалоги")
                logger.debug(f"[DEBUG] Лист 'Диалоги' найден")
            except gspread.exceptions.WorksheetNotFound:
                logger.debug(f"[DEBUG] Лист 'Диалоги' не найден, создаем новый")
                worksheet = self.sheet.add_worksheet(
                    title="Диалоги",
                    rows=10000,
                    cols=10
                )
                logger.debug(f"[DEBUG] Лист 'Диалоги' создан")
                # Добавляем заголовки
                worksheet.append_row([
                    "Дата и время",
                    "ID пользователя",
                    "Username",
                    "Имя",
                    "Фамилия",
                    "Сообщение пользователя",
                    "Ответ бота",
                    "Длина сообщения",
                    "Длина ответа"
                ])
                logger.debug(f"[DEBUG] Заголовки добавлены в лист 'Диалоги'")
            
            # Формируем полное имя
            full_name = ""
            if first_name:
                full_name = first_name
            if last_name:
                full_name = f"{full_name} {last_name}".strip()
            
            # Добавляем запись диалога
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"[DEBUG] Подготовка данных для сохранения: timestamp={timestamp}, user_id={user_id}")
            try:
                row_data = [
                    timestamp,
                    str(user_id),
                    username or "",
                    first_name or "",
                    last_name or "",
                    user_message[:5000] if len(user_message) > 5000 else user_message,  # Ограничение длины
                    bot_response[:5000] if len(bot_response) > 5000 else bot_response,  # Ограничение длины
                    len(user_message),
                    len(bot_response)
                ]
                logger.debug(f"[DEBUG] Вызываем worksheet.append_row() для user_id={user_id}")
                worksheet.append_row(row_data)
                logger.info(f"[OK] Диалог сохранен в Google Sheets: user_id={user_id}, username={username or 'N/A'}, first_name={first_name or 'N/A'}")
                return True
            except Exception as append_error:
                logger.error(f"[ERROR] Ошибка при добавлении строки в Google Sheets: {append_error}")
                logger.error(f"   Тип ошибки: {type(append_error).__name__}")
                logger.error(f"   user_id={user_id}, username={username or 'N/A'}")
                import traceback
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении диалога: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    # Тестирование Google Sheets сервиса
    print("Инициализация Google Sheets сервиса...")
    sheets_service = SheetsService()
    
    if sheets_service.sheet:
        print(f"Подключено к таблице: {sheets_service.sheet.title}")
        
        # Тестовая заявка (закомментировано, чтобы не создавать лишние записи)
        # sheets_service.save_consultation_request(
        #     user_id=123456789,
        #     name="Тестовый пользователь",
        #     phone="+79991234567"
        # )
        # print("Тестовая заявка добавлена")
    else:
        print("Google Sheets не настроен. Проверьте credentials.json и GOOGLE_SHEETS_SPREADSHEET_ID")
