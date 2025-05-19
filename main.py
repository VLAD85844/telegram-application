import logging
import json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
)
from flask import Flask, jsonify, request

# Инициализация Flask
app = Flask(__name__)

# Mock база данных
users_db = {"demo_user": {"balance": 150}}
products_db = [
    {
        "id": 1,
        "name": "Кофе",
        "price": 50,
        "category": "popular",
        "description": "Ароматный кофе на выбор",
        "image": "https://via.placeholder.com/150?text=Coffee"
    }
]


# Flask Endpoints
@app.route('/api/products')
def get_products():
    return jsonify(products_db)


@app.route('/api/user')
def get_user():
    user_id = request.args.get('user_id')
    return jsonify(users_db.get(user_id, {}))


@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    user = users_db.get(data['user_id'])

    total = sum(item['product']['price'] * item['quantity'] for item in data['cart'])

    if user['balance'] >= total:
        user['balance'] -= total
        return jsonify({"status": "success", "new_balance": user['balance']})
    else:
        return jsonify({"status": "error", "message": "Недостаточно средств"}), 400


# Telegram Bot
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"
WEB_APP_URL = "https://your-bot-market.vercel.app/"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="🎁 Открыть маркетплейс",
            web_app=WebAppInfo(url=WEB_APP_URL))
    ]])
    await update.message.reply_text("Добро пожаловать!", reply_markup=keyboard)


def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()


if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    from threading import Thread

    Thread(target=app.run, kwargs={'port': 5000}).start()

    # Запуск Telegram бота
    run_bot()