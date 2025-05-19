import logging
import json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота (РЕКОМЕНДУЕТСЯ использовать os.environ или .env файл)
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"

# URL вашего Web App
WEB_APP_URL = "https://your-bot-market.vercel.app/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение с кнопкой для открытия Web App."""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="🎁 Открыть маркетплейс",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    ]])
    await update.message.reply_text(
        "Добро пожаловать в маркетплейс подарков!",
        reply_markup=keyboard
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает данные, полученные из Web App."""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"Получены данные из Web App: {data}")

        if data.get("type") == "order_completed":
            await update.effective_message.reply_text(
                f"🎉 Заказ на {data['total']} звёзд успешно оформлен!\n"
                f"Остаток на счету: {data['balance']} ⭐"
            )
    except Exception as e:
        logger.error(f"Ошибка обработки Web App данных: {e}")
        await update.effective_message.reply_text("Произошла ошибка при обработке данных.")

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Обработчик данных из Web App
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
