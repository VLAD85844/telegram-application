import logging
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
)

app = Flask(__name__)
CORS(app)  # Разрешаем CORS

# База данных
users_db = {}
products_db = []

# Конфигурация Telegram
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"
WEB_APP_URL = "https://telegram-application-vlads-projects-09d1df59.vercel.app/"
ADMIN_URL = "https://telegram-application-vlads-projects-09d1df59.vercel.app/admin.html"

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory('static/css', filename)

@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory('static/js', filename)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/admin.html')
def admin_panel():
    return send_from_directory('static', 'admin.html')

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        new_product = {
            "id": len(products_db) + 1,
            "name": request.json['name'],
            "price": int(request.json['price']),
            "description": request.json.get('description', ''),
            "category": request.json.get('category', 'popular'),
            "image": request.json.get('image', '')
        }
        products_db.append(new_product)
        return jsonify({"status": "success", "product": new_product})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products')
def get_products():
    return jsonify(products_db)


@app.route('/api/user')
def get_user():
    user_id = request.args.get('user_id')
    return jsonify(users_db.get(user_id, {"balance": 0}))


@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    user_id = data['user_id']

    if user_id not in users_db:
        return jsonify({"status": "error", "message": "User not found"}), 404

    total = sum(item['price'] * item['quantity'] for item in data['cart'])

    if users_db[user_id]['balance'] >= total:
        users_db[user_id]['balance'] -= total
        return jsonify({"status": "success", "new_balance": users_db[user_id]['balance']})
    else:
        return jsonify({"status": "error", "message": "Недостаточно средств"}), 400


# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_db[str(user.id)] = {"balance": 1000}  # Инициализация баланса для пользователя

    # Создаем клавиатуру с двумя кнопками: для магазина и админки
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="🎁 Открыть магазин",
                web_app=WebAppInfo(url=WEB_APP_URL)  # Ссылка на магазин
            )
        ],
        [
            InlineKeyboardButton(
                text="🛠 Открыть админку",
                web_app=WebAppInfo(url=ADMIN_URL)  # Ссылка на админку
            )
        ]
    ])

    # Отправляем сообщение с клавиатурой
    await update.message.reply_text(
        f"Ваш баланс: {users_db[str(user.id)]['balance']} ⭐",
        reply_markup=keyboard
    )


def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()  # Запуск бота


if __name__ == '__main__':
    from threading import Thread

    # Запуск Flask сервера в отдельном потоке
    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000}).start()

    # Запуск бота
    run_bot()