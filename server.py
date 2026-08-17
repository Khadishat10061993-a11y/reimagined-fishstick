from flask import Flask, request, jsonify, send_from_directory
import threading
import os
import bot

app = Flask(__name__, static_folder=".")


# =========================
# ГЛАВНАЯ СТРАНИЦА
# =========================

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# =========================
# ПРОВЕРКА СЕРВЕРА
# =========================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Ceko Hub"
    })


# =========================
# ОПЛАТА
# =========================

@app.route("/api/create-payment", methods=["POST"])
def create_payment():

    data = request.get_json(silent=True) or {}

    payment_type = data.get("type")
    amount = data.get("amount")
    stars = data.get("stars")
    target = data.get("target")
    username = data.get("username")

    if not payment_type:
        return jsonify({
            "ok": False,
            "message": "Не указан тип покупки"
        }), 400

    if not amount or not stars:
        return jsonify({
            "ok": False,
            "message": "Некорректные данные покупки"
        }), 400

    # Здесь создаётся заявка.
    #
    # Реальную оплату Stars нужно создавать через Telegram Bot API
    # внутри bot.py, потому что именно бот получает
    # successful_payment и после этого выдаёт товар.

    return jsonify({
        "ok": True,
        "message": "Заявка создана",
        "type": payment_type,
        "amount": amount,
        "stars": stars,
        "target": target,
        "username": username
    })


# =========================
# ПРОМОКОД
# =========================

@app.route("/api/promo", methods=["POST"])
def promo():

    data = request.get_json(silent=True) or {}

    code = str(
        data.get("code", "")
    ).strip().upper()

    if not code:
        return jsonify({
            "ok": False,
            "message": "Введите промокод"
        }), 400

    # Само хранение и активация промокодов
    # должно находиться в bot.py,
    # чтобы сайт нельзя было использовать
    # для накрутки баланса.

    return jsonify({
        "ok": True,
        "message": "Промокод отправлен на обработку"
    })


# =========================
# ЗАКАЗ ДЕФ
# =========================

@app.route("/api/order", methods=["POST"])
def order():

    data = request.get_json(silent=True) or {}

    amount = data.get("amount")

    if not amount:
        return jsonify({
            "ok": False,
            "message": "Количество Деф не указано"
        }), 400

    return jsonify({
        "ok": True,
        "message": "Заявка на заказ отправлена"
    })


# =========================
# ВОПРОС К CEKO
# =========================

@app.route("/api/question", methods=["POST"])
def question():

    data = request.get_json(silent=True) or {}

    text = str(
        data.get("text", "")
    ).strip()

    if not text:
        return jsonify({
            "ok": False,
            "message": "Введите вопрос"
        }), 400

    # Вопрос должен передаваться в bot.py,
    # где он отправляется администратору.

    return jsonify({
        "ok": True,
        "message": "Вопрос отправлен администратору ✅"
    })


# =========================
# ЗАПУСК БОТА
# =========================

def run_bot():

    try:
        bot.main()
    except Exception as e:
        print("Ошибка запуска бота:", e)


# =========================
# ЗАПУСК СЕРВЕРА
# =========================

if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    port = int(
        os.environ.get("PORT", 8080)
    )

    print("================================")
    print(" Ceko Hub server")
    print(" Server started")
    print(" Port:", port)
    print("================================")

    app.run(
        host="0.0.0.0",
        port=port
    )
