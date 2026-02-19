"""
Модуль Telegram бота
"""
import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode
import config
from rag_service import RAGService
from openai_service import OpenAIService
from sheets_service import SheetsService
from typing import Dict, List
from enum import Enum

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

# Хранилище флагов для отслеживания, представился ли бот
user_greeted: Dict[int, bool] = {}

# Состояния для сбора данных
class ConversationState:
    WAITING_FOR_NAME = 1
    WAITING_FOR_PHONE = 2
    WAITING_FOR_ORDER_DETAILS = 3

# Типы заявок
class RequestType:
    CONSULTATION = "consultation"
    ORDER = "order"

# Хранилище данных пользователей для заявок
user_requests: Dict[int, Dict] = {}

# Создаем постоянную клавиатуру с кнопками
def get_main_keyboard():
    """Создает постоянную клавиатуру с основными кнопками"""
    keyboard = [
        [
            KeyboardButton("Связаться с менеджером"),
            KeyboardButton("Сделать заказ")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,  # Клавиатура не должна скрываться после использования
        selective=False,  # Показывать клавиатуру всем пользователям
        input_field_placeholder="Задайте вопрос или выберите действие"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем историю диалога для пользователя
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Отмечаем, что бот уже представился
    user_greeted[user_id] = True
    
    # Получаем приветствие от OpenAI
    welcome_message = openai_service.get_response(
        user_message="/start",
        conversation_history=[],
        rag_context=None
    )
    
    # Сохраняем приветствие в историю диалога
    user_conversations[user_id].append({"role": "user", "content": "/start"})
    user_conversations[user_id].append({"role": "assistant", "content": welcome_message})
    
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
    
    # Отправляем сообщение с постоянной клавиатурой
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def send_to_group(message_text: str, bot_instance=None):
    """Отправляет сообщение в группу Telegram"""
    if not config.TELEGRAM_GROUP_ID:
        logger.warning("[WARNING] TELEGRAM_GROUP_ID не установлен. Сообщение не будет отправлено в группу.")
        return False
    
    try:
        if bot_instance:
            bot = bot_instance
        else:
            from telegram import Bot
            bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        
        await bot.send_message(
            chat_id=config.TELEGRAM_GROUP_ID,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"[OK] Сообщение отправлено в группу {config.TELEGRAM_GROUP_ID}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при отправке сообщения в группу: {e}", exc_info=True)
        return False


async def handle_button_contact_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Связаться с менеджером' - начинает сбор данных"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем заявку
    user_requests[user_id] = {
        "type": RequestType.CONSULTATION,
        "user_id": user_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    # Сохраняем нажатие кнопки в лист "Диалоги"
    try:
        sheets_service.save_dialog_message(
            user_id=user_id,
            user_message="Связаться с менеджером",
            bot_response="Начало сбора данных для консультации",
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении нажатия кнопки: {e}", exc_info=True)
    
    # Запрашиваем имя
    await update.message.reply_text(
        "📞 **Связаться с менеджером**\n\n"
        "Пожалуйста, укажите Ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationState.WAITING_FOR_NAME


async def handle_button_make_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Сделать заказ' - начинает сбор данных"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем заявку
    user_requests[user_id] = {
        "type": RequestType.ORDER,
        "user_id": user_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    # Сохраняем нажатие кнопки в лист "Диалоги"
    try:
        sheets_service.save_dialog_message(
            user_id=user_id,
            user_message="Сделать заказ",
            bot_response="Начало сбора данных для заказа",
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении нажатия кнопки: {e}", exc_info=True)
    
    # Запрашиваем имя
    await update.message.reply_text(
        "🛒 **Сделать заказ**\n\n"
        "Пожалуйста, укажите Ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationState.WAITING_FOR_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода имени"""
    user = update.effective_user
    user_id = user.id
    name = update.message.text
    
    if user_id not in user_requests:
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, начните заново, нажав на кнопку.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем имя
    user_requests[user_id]["name"] = name
    
    # Запрашиваем телефон
    await update.message.reply_text(
        "Спасибо! Теперь укажите Ваш номер телефона:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationState.WAITING_FOR_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода телефона"""
    user = update.effective_user
    user_id = user.id
    phone = update.message.text
    
    if user_id not in user_requests:
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, начните заново, нажав на кнопку.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем телефон
    user_requests[user_id]["phone"] = phone
    
    request_type = user_requests[user_id]["type"]
    
    if request_type == RequestType.CONSULTATION:
        # Для консультации - завершаем сбор данных
        return await finish_consultation_request(update, context)
    elif request_type == RequestType.ORDER:
        # Для заказа - запрашиваем детали заказа
        await update.message.reply_text(
            "Отлично! Теперь опишите, что Вы хотели бы заказать:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationState.WAITING_FOR_ORDER_DETAILS


async def handle_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода деталей заказа"""
    user = update.effective_user
    user_id = user.id
    order_details = update.message.text
    
    if user_id not in user_requests:
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, начните заново, нажав на кнопку.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем детали заказа
    user_requests[user_id]["order_details"] = order_details
    
    # Завершаем заявку на заказ
    return await finish_order_request(update, context)


async def finish_consultation_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает заявку на консультацию и отправляет данные"""
    user = update.effective_user
    user_id = user.id
    
    request_data = user_requests.get(user_id, {})
    name = request_data.get("name", "Не указано")
    phone = request_data.get("phone", "Не указан")
    
    # Формируем сообщение для группы
    group_message = (
        "📞 **Новая заявка на консультацию**\n\n"
        f"👤 **Имя:** {name}\n"
        f"📱 **Телефон:** {phone}\n"
        f"🆔 **ID пользователя:** {user_id}\n"
        f"👤 **Username:** @{request_data.get('username', 'не указан')}\n"
        f"📅 **Время:** {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Отправляем в группу
    await send_to_group(group_message, context.bot)
    
    # Сохраняем в Google Sheets
    try:
        sheets_service.save_consultation_request(
            user_id=user_id,
            name=name,
            phone=phone,
            username=request_data.get("username")
        )
        logger.info(f"[OK] Заявка на консультацию сохранена для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении заявки: {e}", exc_info=True)
    
    # Сохраняем диалог
    try:
        sheets_service.save_dialog_message(
            user_id=user_id,
            user_message=f"Консультация: Имя={name}, Телефон={phone}",
            bot_response="Заявка на консультацию принята",
            username=request_data.get("username"),
            first_name=request_data.get("first_name"),
            last_name=request_data.get("last_name")
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении диалога: {e}", exc_info=True)
    
    # Отправляем подтверждение пользователю
    await update.message.reply_text(
        "✅ **Спасибо!**\n\n"
        "Ваша заявка на консультацию принята! Наш менеджер свяжется с Вами в ближайшее время.\n\n"
        "Вы также можете задать мне вопросы о продукции, и я помогу Вам с выбором.",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Очищаем данные заявки
    if user_id in user_requests:
        del user_requests[user_id]
    
    return ConversationHandler.END


async def finish_order_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает заявку на заказ и отправляет данные"""
    user = update.effective_user
    user_id = user.id
    
    request_data = user_requests.get(user_id, {})
    name = request_data.get("name", "Не указано")
    phone = request_data.get("phone", "Не указан")
    order_details = request_data.get("order_details", "Не указано")
    
    # Формируем сообщение для группы
    group_message = (
        "🛒 **Новая заявка на заказ**\n\n"
        f"👤 **Имя:** {name}\n"
        f"📱 **Телефон:** {phone}\n"
        f"📦 **Детали заказа:** {order_details}\n"
        f"🆔 **ID пользователя:** {user_id}\n"
        f"👤 **Username:** @{request_data.get('username', 'не указан')}\n"
        f"📅 **Время:** {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Отправляем в группу
    await send_to_group(group_message, context.bot)
    
    # Сохраняем в Google Sheets
    try:
        sheets_service.save_order_request(
            user_id=user_id,
            order_info=f"Имя: {name}, Телефон: {phone}, Заказ: {order_details}",
            username=request_data.get("username")
        )
        logger.info(f"[OK] Заявка на заказ сохранена для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении заявки: {e}", exc_info=True)
    
    # Сохраняем диалог
    try:
        sheets_service.save_dialog_message(
            user_id=user_id,
            user_message=f"Заказ: Имя={name}, Телефон={phone}, Детали={order_details}",
            bot_response="Заявка на заказ принята",
            username=request_data.get("username"),
            first_name=request_data.get("first_name"),
            last_name=request_data.get("last_name")
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при сохранении диалога: {e}", exc_info=True)
    
    # Отправляем подтверждение пользователю
    await update.message.reply_text(
        "✅ **Спасибо!**\n\n"
        "Ваша заявка на заказ принята! Наш менеджер свяжется с Вами для уточнения деталей заказа.\n\n"
        "Если у Вас есть вопросы о продукции, я с радостью помогу Вам с выбором.",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Очищаем данные заявки
    if user_id in user_requests:
        del user_requests[user_id]
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущую операцию"""
    user_id = update.effective_user.id
    
    if user_id in user_requests:
        del user_requests[user_id]
    
    await update.message.reply_text(
        "Операция отменена.",
        reply_markup=get_main_keyboard()
    )
    
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user = update.effective_user
        user_id = user.id
        user_message = update.message.text
        
        # Проверяем, не является ли сообщение одной из кнопок
        if user_message == "Связаться с менеджером":
            return await handle_button_contact_manager(update, context)
        elif user_message == "Сделать заказ":
            return await handle_button_make_order(update, context)
        
        # Инициализируем историю диалога для пользователя
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        # Если бот еще не представился, отмечаем это (но не отправляем приветствие повторно)
        if user_id not in user_greeted:
            user_greeted[user_id] = False
        
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
        # Всегда передаем полную историю диалога (она уже содержит приветствие, если было /start)
        try:
            response = openai_service.get_response(
                user_message=user_message,
                conversation_history=user_conversations[user_id],
                rag_context=rag_context
            )
            
            # Обновляем историю диалога
            user_conversations[user_id].append({"role": "user", "content": user_message})
            user_conversations[user_id].append({"role": "assistant", "content": response})
            
            # Если бот еще не представился (пользователь не использовал /start), отмечаем это
            if not user_greeted.get(user_id, False):
                user_greeted[user_id] = True
            
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
                reply_markup=get_main_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка при получении ответа от OpenAI: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего запроса. Попробуйте еще раз.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_message: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
def main():
    """Запуск Telegram бота"""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    # Создаем приложение
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Создаем ConversationHandler для сбора данных
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Связаться с менеджером$"), handle_button_contact_manager),
            MessageHandler(filters.Regex("^Сделать заказ$"), handle_button_make_order),
        ],
        states={
            ConversationState.WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
            ],
            ConversationState.WAITING_FOR_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            ConversationState.WAITING_FOR_ORDER_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_details)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^Отмена$"), cancel),
        ],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
