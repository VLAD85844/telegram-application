import logging
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, Bot, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
    Updater,
)

app = Flask(__name__)
CORS(app)  # Разрешаем CORS

# База данных
users_db = {}
products_db = []

# Конфигурация Telegram
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"
bot = Bot(token="7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY")
WEB_APP_URL = "https://telegram-application-gcf2.vercel.app/"
ADMIN_URL = "https://telegram-application-gcf2.vercel.app/admin.html"
provider_token = ""
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


@app.route('/api/createInvoice', methods=['POST'])
def create_invoice():
    data = request.json
    user_id = data['userId']
    amount = data['amount']
    description = data['description']

    try:
        # Формируем инвойс с нужными параметрами
        invoice = bot.send_invoice(
            chat_id=user_id,  # Отправляем инвойс пользователю
            title="Оплата товаров",  # Название инвойса
            description=description,  # Описание
            payload="some_payload",  # Персонализированная информация о платеже
            provider_token=provider_token,  # Токен платежного провайдера
            currency="XTR",  # Валюта (если используется Stars API, это будет XTR)
            prices=[LabeledPrice("Итого", amount * 100)]
            # Сумма, умноженная на 100 (платежные системы требуют указания суммы в копейках)
        )

        return jsonify({"status": "success", "paymentUrl": invoice.url})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


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

@app.route('/webhook', methods=['POST'])
def handle_payment_confirmation():
    data = request.json
    # Проверьте статус платежа и выполните необходимые действия (например, обновление баланса)
    if data['status'] == 'paid':
        # Завершаем заказ, обновляем баланс и т.д.
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Payment failed"}), 400

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

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    global products_db
    products_db = [p for p in products_db if p['id'] != product_id]
    return jsonify({"status": "success"})

@app.route('/api/products')
def get_products():
    return jsonify(products_db)


@app.route('/api/payment', methods=['POST'])
def handle_payment():
    data = request.json
    user_id = data['user_id']
    amount = data['amount']

    # Обновляем баланс пользователя
    if user_id in users_db:
        users_db[user_id]['balance'] -= amount
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "User not found"}), 404

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