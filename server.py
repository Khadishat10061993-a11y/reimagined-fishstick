from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)


# =========================
# САЙТ
# =========================

@app.route("/")
def home():
    return send_file("index.html")


# =========================
# ПРОВЕРКА
# =========================

@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "message": "Ceko Hub server работает ✅"
    })


# =========================
# СОЗДАНИЕ ПЛАТЕЖА
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
            "message": "Неверная сумма"
        }), 400

    print("НОВЫЙ ЗАКАЗ")
    print("Тип:", payment_type)
    print("Количество:", amount)
    print("Stars:", stars)
    print("Получатель:", target)
    print("Username:", username)

    return jsonify({
        "ok": True,
        "message": "Заказ создан ✅"
    })


# =========================
# ПРОМОКОД
# =========================

@app.route("/api/promo", methods=["POST"])
def promo():

    data = request.get_json(silent=True) or {}

    code = str(
        data.get("code", "")
    ).strip()

    if not code:
        return jsonify({
            "ok": False,
            "message": "Введите промокод"
        }), 400

    print("ПРОМОКОД:", code)

    return jsonify({
        "ok": True,
        "message": "Промокод отправлен боту"
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

    print("ЗАКАЗ ДЕФ:", amount)

    return jsonify({
        "ok": True,
        "message": "Заявка отправлена ✅"
    })


# =========================
# ВОПРОС
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

    print("ВОПРОС:")
    print(text)

    return jsonify({
        "ok": True,
        "message": "Вопрос отправлен ✅"
    })


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 8080)
    )

    print("================================")
    print("       CEKO HUB SERVER")
    print("================================")
    print("PORT:", port)
    print("SERVER STARTED ✅")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
