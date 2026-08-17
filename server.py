from flask import Flask
import threading
import os
import bot

app = Flask(__name__)


@app.route("/")
def home():
    return "Ceko Hub server is running ✅"


@app.route("/health")
def health():
    return "OK"


def run_bot():
    bot.main()


if __name__ == "__main__":
    # Запускаем Telegram-бота отдельным потоком
    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    # Порт хостинга
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )
