from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import threading
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import asyncio

app = Flask(__name__, static_url_path='/static')
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели базы данных
class User(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    balance = db.Column(db.Integer, default=0)
    transactions = db.relationship('Transaction', backref='user', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image = db.Column(db.String(255))


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'))
    type = db.Column(db.String(20))  # deposit, withdraw, purchase, transfer_in, transfer_out
    amount = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    admin = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)


# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()

# Конфигурация
TOKEN = "7978464693:AAHfahvoHcalAmK17Op05OVY-2o8IMbXLxY"
WEB_APP_URL = "https://telegram-application-gcf2.vercel.app/"
ADMIN_URL = f"{WEB_APP_URL}admin.html"
users_db = {}


# API Endpoints

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'GET':
        try:
            products = Product.query.all()
            return jsonify([{
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "description": p.description,
                "category": p.category,
                "image": p.image
            } for p in products])
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400

            # Проверяем обязательные поля
            required_fields = ['name', 'price', 'image', 'category']
            for field in required_fields:
                if field not in data:
                    return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

            new_product = Product(
                name=data['name'],
                price=int(data['price']),
                description=data.get('description', ''),
                category=data['category'],
                image=data['image']
            )
            db.session.add(new_product)
            db.session.commit()
            return jsonify({
                "status": "success",
                "product": {
                    "id": new_product.id,
                    "name": new_product.name,
                    "price": new_product.price,
                    "description": new_product.description,
                    "category": new_product.category,
                    "image": new_product.image
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"status": "success"})


@app.route('/api/user')
def get_user():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400  # Вернем ошибку, если нет user_id

        user = User.query.get(user_id)
        if not user:
            user = User(id=user_id, balance=0)
            db.session.add(user)
            db.session.commit()

        return jsonify({
            "balance": user.balance,
            "transactions": [t.to_dict() for t in user.transactions]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Возвращаем ошибку с сообщением в формате JSON



@app.route('/api/user/deposit', methods=['POST'])
def deposit_funds():
    try:
        user_id = request.json.get('user_id')
        amount = request.json.get('amount')
        admin = request.json.get('admin', 'system')

        if not user_id or amount is None:
            return jsonify({"error": "user_id and amount are required"}), 400

        user = User.query.get(user_id)
        if not user:
            user = User(id=user_id, balance=0)
            db.session.add(user)

        user.balance += amount
        db.session.commit()

        return jsonify({"status": "success", "new_balance": user.balance})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route('/api/user/transfer', methods=['POST'])
def transfer_funds():
    from_user_id = request.json.get('from_user')
    to_user_id = request.json.get('to_user')
    amount = request.json.get('amount')

    from_user = User.query.get_or_404(from_user_id)
    to_user = User.query.get(to_user_id)
    if not to_user:
        to_user = User(id=to_user_id, balance=0)
        db.session.add(to_user)

    if from_user.balance < amount:
        return jsonify({"status": "error", "message": "Insufficient funds"}), 400

    from_user.balance -= amount
    to_user.balance += amount

    # Записываем транзакции
    out_transaction = Transaction(
        user_id=from_user_id,
        type="transfer_out",
        amount=amount,
        details=f"Transfer to {to_user_id}"
    )

    in_transaction = Transaction(
        user_id=to_user_id,
        type="transfer_in",
        amount=amount,
        details=f"Transfer from {from_user_id}"
    )

    db.session.add_all([out_transaction, in_transaction])
    db.session.commit()

    return jsonify({"status": "success"})


# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Создаем контекст приложения и получаем/обновляем пользователя
    with app.app_context():
        db_user = db.session.get(User, str(user.id))  # Получаем данные из базы данных
        if not db_user:
            # Если пользователя нет в базе, создаем нового с начальным балансом 1000
            db_user = User(id=str(user.id), balance=1000)
            db.session.add(db_user)
            db.session.commit()

        # Обновляем словарь для Telegram-бота
        users_db[str(user.id)] = {"balance": db_user.balance}

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎁 Магазин", web_app=WebAppInfo(WEB_APP_URL)),
        InlineKeyboardButton("🛠 Админка", web_app=WebAppInfo(ADMIN_URL))
    ]])

    # Отправляем сообщение с актуальным балансом
    await update.message.reply_text(
        f"Баланс: {db_user.balance} ⭐",
        reply_markup=keyboard
    )


def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()


def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Запускаем бота в основном потоке
    asyncio.run(run_bot())  # Обновлено для асинхронного запуска бота
