"""
Модуль Telegram бота
"""
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode
import config
from rag_service import RAGService
from openai_service import OpenAIService
from sheets_service import SheetsService
from typing import Dict, List

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация сервисов
rag_service = RAGService()
openai_service = OpenAIService()
sheets_service = SheetsService()

# Проверка настройки Google Sheets
if not sheets_service.sheet:
    logger.warning("[WARNING] Google Sheets не настроен! Данные не будут сохраняться в таблицу.")
    logger.warning("Проверьте: credentials.json и GOOGLE_SHEETS_SPREADSHEET_ID в .env")
else:
    logger.info("[OK] Google Sheets успешно подключен")

# Хранилище состояний пользователей
user_conversations: Dict[int, List[Dict[str, str]]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем историю диалога для пользователя
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Получаем приветствие от OpenAI
    welcome_message = openai_service.get_response(
        user_message="/start",
        conversation_history=[],
        rag_context=None
    )
    
    # Сохраняем диалог в Google Sheets
    try:
        success = sheets_service.save_dialog_message(
            user_id=user_id,
            user_message="/start",
            bot_response=welcome_message,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        if success:
            logger.info(f"[OK] Диалог сохранен в Google Sheets для пользователя {user_id}")
        else:
            logger.warning(f"[WARNING] Не удалось сохранить диалог в Google Sheets для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении диалога: {e}", exc_info=True)
    
    # Сначала удаляем клавиатуру, затем отправляем сообщение
    await update.message.reply_text(
        welcome_message,
        reply_markup=ReplyKeyboardRemove(selective=False),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user = update.effective_user
        user_id = user.id
        user_message = update.message.text
        
        # Инициализируем историю диалога для пользователя
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        # Поиск в RAG базе
        rag_results = None
        rag_context = None
        try:
            rag_results = rag_service.search(user_message, n_results=3)
            if rag_results and rag_results['documents'] and rag_results['documents'][0]:
                # Формируем контекст из результатов RAG
                contexts = []
                for i, doc in enumerate(rag_results['documents'][0]):
                    metadata = rag_results['metadatas'][0][i] if rag_results['metadatas'] and rag_results['metadatas'][0] else {}
                    contexts.append(f"Документ {i+1}:\n{doc}\nМетаданные: {metadata}")
                rag_context = "\n\n".join(contexts)
        except Exception as e:
            logger.error(f"Ошибка при поиске в RAG: {e}")
        
        # Получаем ответ от OpenAI
        try:
            response = openai_service.get_response(
                user_message=user_message,
                conversation_history=user_conversations[user_id],
                rag_context=rag_context
            )
            
            # Обновляем историю диалога
            user_conversations[user_id].append({"role": "user", "content": user_message})
            user_conversations[user_id].append({"role": "assistant", "content": response})
            
            # Ограничиваем размер истории
            if len(user_conversations[user_id]) > 20:
                user_conversations[user_id] = user_conversations[user_id][-20:]
            
            # Сохраняем диалог в Google Sheets
            try:
                success = sheets_service.save_dialog_message(
                    user_id=user_id,
                    user_message=user_message,
                    bot_response=response,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                if success:
                    logger.info(f"[OK] Диалог сохранен в Google Sheets для пользователя {user_id} (username: {user.username or 'N/A'}, name: {user.first_name or 'N/A'})")
                else:
                    logger.warning(f"[WARNING] Не удалось сохранить диалог в Google Sheets для пользователя {user_id} (username: {user.username or 'N/A'}, name: {user.first_name or 'N/A'})")
            except Exception as e:
                logger.error(f"[ERROR] Ошибка при сохранении диалога: {e}", exc_info=True)
            
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardRemove(selective=False),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка при получении ответа от OpenAI: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего запроса. Попробуйте еще раз.",
                reply_markup=ReplyKeyboardRemove(selective=False)
            )
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_message: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(selective=False)
        )
def main():
    """Запуск Telegram бота"""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    # Создаем приложение
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
