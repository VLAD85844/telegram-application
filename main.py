from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import os

app = Flask(__name__)
CORS(app)

if not os.path.exists('static'):
    os.makedirs('static/css')
    os.makedirs('static/js')
    print("Создана структура папок для статических файлов")

# База данных
users_db = {}
products_db = []

# Конфигурация
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"
WEB_APP_URL = "https://telegram-application-gcf2.vercel.app/"
ADMIN_URL = f"{WEB_APP_URL}admin.html"


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/admin.html')
def admin_panel():
    return send_from_directory('static', 'admin.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# API Endpoints
@app.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        new_product = {
            "id": len(products_db) + 1,
            **request.json
        }
        products_db.append(new_product)
        return jsonify({"status": "success", "product": new_product})
    return jsonify(products_db)


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    global products_db
    products_db = [p for p in products_db if p['id'] != product_id]
    return jsonify({"status": "success"})


@app.route('/api/user')
def get_user():
    user_id = request.args.get('user_id')
    return jsonify(users_db.get(user_id, {"balance": 0}))


# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_db[str(user.id)] = {"balance": 1000}

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎁 Магазин", web_app=WebAppInfo(WEB_APP_URL)),
        InlineKeyboardButton("🛠 Админка", web_app=WebAppInfo(ADMIN_URL))
    ]])

    await update.message.reply_text(
        f"Баланс: {users_db[str(user.id)]['balance']} ⭐",
        reply_markup=keyboard
    )


def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)