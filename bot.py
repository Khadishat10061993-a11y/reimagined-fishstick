import sqlite3
import random
import string
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = "8905175157:AAEo3tBv5V1pJGbJwWRoRXojMyj5qaJAxfw"

ADMIN_ID = 8161017993

ADMIN_USERNAME = "@netuzu"

CHANNEL_URL = "https://t.me/+lyHMe0599OtjYjEy"

START_PHOTO = "Start.jpg.PNG"
CATALOG_PHOTO = "Katalog.jpg.PNG"


# =========================================================
# ЛОГИ
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# БАЗА
# =========================================================

db = sqlite3.connect(
    "ceko_hub.db",
    check_same_thread=False
)

cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    amount INTEGER NOT NULL,
    uses_left INTEGER NOT NULL
)
""")

db.commit()


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

def register_user(user):

    cur.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, balance)
        VALUES (?, ?, 0)
        """,
        (
            user.id,
            user.username or ""
        )
    )

    cur.execute(
        """
        UPDATE users
        SET username = ?
        WHERE user_id = ?
        """,
        (
            user.username or "",
            user.id
        )
    )

    db.commit()


def balance(user_id):

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    if row:
        return row[0]

    return 0


def give_def(user_id, amount):

    cur.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    db.commit()


# =========================================================
# ПРОМОКОДЫ
# =========================================================

def new_promo():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        cur.execute(
            "SELECT code FROM promos WHERE code = ?",
            (code,)
        )

        if cur.fetchone() is None:
            return code


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def main_menu(user_id):

    buttons = [
        [
            InlineKeyboardButton(
                "🫀 Каталог",
                callback_data="CATALOG"
            ),
            InlineKeyboardButton(
                "🫆 Промокод",
                callback_data="PROMO"
            )
        ],

        [
            InlineKeyboardButton(
                "👾 Заказать Деф",
                callback_data="ORDER"
            )
        ],

        [
            InlineKeyboardButton(
                "💬 Секрет Тгк",
                callback_data="CHANNEL"
            )
        ],

        [
            InlineKeyboardButton(
                "🔰 Вопрос к Ceko",
                callback_data="QUESTION"
            )
        ],

        [
            InlineKeyboardButton(
                f"💰 Баланс: {balance(user_id)} Деф",
                callback_data="BALANCE"
            )
        ]
    ]

    if user_id == ADMIN_ID:

        buttons.append([
            InlineKeyboardButton(
                "🔐 Панель",
                callback_data="ADMIN"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def back_button():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])


def admin_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Создать промокод",
                callback_data="ADMIN_PROMO"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 Статистика",
                callback_data="ADMIN_STATS"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Главное меню",
                callback_data="BACK"
            )
        ]
    ])


# =========================================================
# УДАЛИТЬ СТАРОЕ СООБЩЕНИЕ
# =========================================================

async def delete_old(query):

    try:
        await query.message.delete()
    except Exception:
        pass


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register_user(user)

    context.user_data.clear()

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {balance(user.id)} Деф"
    )

    try:

        with open(START_PHOTO, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_menu(user.id)
            )

    except FileNotFoundError:

        await update.message.reply_text(
            text,
            reply_markup=main_menu(user.id)
        )


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    context.user_data.clear()

    await delete_old(query)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {balance(user.id)} Деф"
    )

    try:

        with open(START_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_menu(user.id)
            )

    except FileNotFoundError:

        await query.message.chat.send_message(
            text,
            reply_markup=main_menu(user.id)
        )


# =========================================================
# КАТАЛОГ
# =========================================================

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    await delete_old(query)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="BUY_1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="BUY_10"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="BUY_25"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="BUY_50"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])

    text = (
        "🤖 Каталог валюты\n\n"
        "Действуют скидки - навсегда"
    )

    try:

        with open(CATALOG_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard
            )

    except FileNotFoundError:

        await query.message.chat.send_message(
            text,
            reply_markup=keyboard
        )


# =========================================================
# ПОКУПКА
# =========================================================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    amount = int(
        query.data.replace("BUY_", "")
    )

    prices = {
        1: 1,
        10: 5,
        25: 10,
        50: 40
    }

    bears = prices[amount]

    context.user_data["buy_amount"] = amount
    context.user_data["buy_bears"] = bears

    await delete_old(query)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Готово",
                callback_data="PAYMENT_DONE"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="CATALOG"
            )
        ]
    ])

    await query.message.chat.send_message(

        f"Вы выбрали {amount} Деф очков.\n\n"
        f"Для получения перейдите в ЛС {ADMIN_USERNAME}\n"
        f"и скиньте {bears} Мишек.\n\n"
        "После оплаты нажмите «Готово».",

        reply_markup=keyboard
    )


# =========================================================
# ОПЛАТА ГОТОВА
# =========================================================

async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    amount = context.user_data.get(
        "buy_amount"
    )

    bears = context.user_data.get(
        "buy_bears"
    )

    if not amount:

        await query.answer(
            "Заявка потеряна. Откройте каталог снова.",
            show_alert=True
        )

        return

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    await delete_old(query)

    await query.message.chat.send_message(
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"CONFIRM_PAYMENT:{user.id}:{amount}"
            )
        ]
    ])

    await context.bot.send_message(

        ADMIN_ID,

        "🆕 НОВАЯ ЗАЯВКА\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Деф: {amount}\n"
        f"🧸 Мишек: {bears}\n\n"
        "Прошу проверить оплату.",

        reply_markup=keyboard
    )


# =========================================================
# ПОДТВЕРДИТЬ ОПЛАТУ
# =========================================================

async def confirm_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    await query.answer()

    parts = query.data.split(":")

    user_id = int(parts[1])
    amount = int(parts[2])

    give_def(
        user_id,
        amount
    )

    try:

        await context.bot.send_message(

            user_id,

            "✅ Администратор проверил оплату.\n\n"
            f"Вам выдано {amount} Деф очков.\n\n"
            f"💰 Баланс: {balance(user_id)} Деф"
        )

    except Exception:
        pass

    await query.message.edit_text(
        query.message.text
        + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )


# =========================================================
# ПРОМОКОД — ОТКРЫТИЕ
# =========================================================

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["PROMO_WAIT"] = True

    await delete_old(query)

    await query.message.chat.send_message(

        "🫆 Промокод\n\n"
        "Введите промокод:",

        reply_markup=back_button()
    )


# =========================================================
# ПРОМОКОД — ВВОД
# =========================================================

async def process_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "PROMO_WAIT"
    ):
        return False

    code = update.message.text.strip().upper()

    cur.execute(
        """
        SELECT amount, uses_left
        FROM promos
        WHERE code = ?
        """,
        (code,)
    )

    result = cur.fetchone()

    if not result:

        await update.message.reply_text(
            "❌ Такого промокода нет.",
            reply_markup=back_button()
        )

        return True

    amount, uses = result

    if uses <= 0:

        await update.message.reply_text(
            "❌ Промокод больше недоступен.",
            reply_markup=back_button()
        )

        return True

    give_def(
        update.effective_user.id,
        amount
    )

    cur.execute(
        """
        UPDATE promos
        SET uses_left = uses_left - 1
        WHERE code = ?
        """,
        (code,)
    )

    db.commit()

    context.user_data.clear()

    await update.message.reply_text(

        "🎉 Промокод активирован!\n\n"
        f"Вы получили {amount} Деф очков.\n\n"
        f"💰 Баланс: "
        f"{balance(update.effective_user.id)} Деф",

        reply_markup=back_button()
    )

    return True


# =========================================================
# ЗАКАЗАТЬ ДЕФ
# =========================================================

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    await delete_old(query)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Деф Очка",
                callback_data="ORDER_1"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])

    await query.message.chat.send_message(

        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",

        reply_markup=keyboard
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ ЗАКАЗА
# =========================================================

async def order_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await delete_old(query)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить заказ",
                callback_data="ORDER_CONFIRM"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="ORDER"
            )
        ]
    ])

    await query.message.chat.send_message(

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "Подтвердить заказ?",

        reply_markup=keyboard
    )


# =========================================================
# ЗАКАЗ ПОДТВЕРЖДЁН
# =========================================================

async def order_confirmed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    await delete_old(query)

    await query.message.chat.send_message(
        "✅ Ваш заказ принят!\n\n"
        "Администратор свяжется с вами."
    )

    await context.bot.send_message(

        ADMIN_ID,

        "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
        f"👤 {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Прошу перейти к пользователю.",

        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Открыть профиль",
                    url=f"tg://user?id={user.id}"
                )
            ]
        ])
    )


# =========================================================
# СЕКРЕТ ТГК
# =========================================================

async def channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await delete_old(query)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💬 Перейти в канал",
                url=CHANNEL_URL
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])

    await query.message.chat.send_message(

        "💬 Секрет Тгк\n\n"
        "Здесь находится секретный Telegram-канал.",

        reply_markup=keyboard
    )


# =========================================================
# ВОПРОС К CEKO
# =========================================================

question_users = {}


async def question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["QUESTION_WAIT"] = True

    await delete_old(query)

    await query.message.chat.send_message(

        "🔰 Вопрос к Ceko\n\n"
        "Отправьте свой вопрос.\n\n"
        "Можно отправить:\n"
        "• текст\n"
        "• фото\n"
        "• видео\n"
        "• документ\n"
        "• голосовое\n"
        "• стикер\n\n"
        "Администратор ответит вам.",

        reply_markup=back_button()
    )


# =========================================================
# ВОПРОС ПОЛЬЗОВАТЕЛЯ
# =========================================================

async def receive_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "QUESTION_WAIT"
    ):
        return False

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    info = await context.bot.send_message(

        ADMIN_ID,

        "🔰 НОВЫЙ ВОПРОС\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Ответьте реплаем на сообщение пользователя."
    )

    question_users[
        info.message_id
    ] = user.id

    try:

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_users[
            copied.message_id
        ] = user.id

    except Exception as e:

        logging.error(
            f"Question error: {e}"
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Сообщение отправлено администратору.",
        reply_markup=back_button()
    )

    return True


# =========================================================
# БАЛАНС
# =========================================================

async def show_balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer(
        f"💰 Баланс: "
        f"{balance(query.from_user.id)} Деф",
        show_alert=True
    )


# =========================================================
# АДМИН-ПАНЕЛЬ
# =========================================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.answer()

    context.user_data.clear()

    await delete_old(query)

    await query.message.chat.send_message(

        "🔐 Панель администратора\n\n"
        "Выберите действие:",

        reply_markup=admin_menu()
    )


# =========================================================
# СОЗДАНИЕ ПРОМО — ШАГ 1
# =========================================================

async def admin_promo_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.answer()

    context.user_data.clear()

    context.user_data[
        "ADMIN_STATE"
    ] = "AMOUNT"

    await delete_old(query)

    await query.message.chat.send_message(

        "➕ Создание промокода\n\n"
        "Шаг 1\n\n"
        "Сколько Деф очков будет давать промокод?\n\n"
        "Например: 50"
    )


# =========================================================
# СОЗДАНИЕ ПРОМО — ШАГ 2
# =========================================================

async def admin_promo_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "ADMIN_STATE"
    ) != "AMOUNT":
        return False

    try:

        amount = int(
            update.message.text
        )

        if amount <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите число больше 0."
        )

        return True

    context.user_data[
        "PROMO_AMOUNT"
    ] = amount

    context.user_data[
        "ADMIN_STATE"
    ] = "USES"

    await update.message.reply_text(

        "Шаг 2\n\n"
        "Сколько раз можно использовать промокод?\n\n"
        "Например: 10"
    )

    return True


# =========================================================
# СОЗДАНИЕ ПРОМО — ПОДТВЕРЖДЕНИЕ
# =========================================================

async def admin_promo_uses(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "ADMIN_STATE"
    ) != "USES":
        return False

    try:

        uses = int(
            update.message.text
        )

        if uses <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите число больше 0."
        )

        return True

    amount = context.user_data[
        "PROMO_AMOUNT"
    ]

    context.user_data[
        "PROMO_USES"
    ] = uses

    context.user_data[
        "ADMIN_STATE"
    ] = "CONFIRM"

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Создать",
                callback_data="CREATE_PROMO"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="ADMIN"
            )
        ]
    ])

    await update.message.reply_text(

        "📋 Проверьте:\n\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать промокод?",

        reply_markup=keyboard
    )

    return True


# =========================================================
# СОЗДАТЬ ПРОМО
# =========================================================

async def create_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.answer()

    amount = context.user_data.get(
        "PROMO_AMOUNT"
    )

    uses = context.user_data.get(
        "PROMO_USES"
    )

    if not amount or not uses:

        await query.message.edit_text(
            "❌ Ошибка создания.",
            reply_markup=admin_menu()
        )

        return

    code = new_promo()

    cur.execute(
        """
        INSERT INTO promos
        (code, amount, uses_left)
        VALUES (?, ?, ?)
        """,
        (
            code,
            amount,
            uses
        )
    )

    db.commit()

    context.user_data.clear()

    await query.message.edit_text(

        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 Код:\n`{code}`\n\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}",

        parse_mode="Markdown",
        reply_markup=admin_menu()
    )


# =========================================================
# СТАТИСТИКА
# =========================================================

async def admin_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.answer()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM promos"
    )

    promos = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM users"
    )

    total = cur.fetchone()[0]

    await query.message.edit_text(

        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {users}\n"
        f"🎟 Промокодов: {promos}\n"
        f"💰 Деф на балансах: {total}",

        reply_markup=admin_menu()
    )


# =========================================================
# ОТВЕТ АДМИНА
# =========================================================

async def admin_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not update.message.reply_to_message:
        return False

    replied = (
        update.message
        .reply_to_message
        .message_id
    )

    user_id = question_users.get(
        replied
    )

    if not user_id:
        return False

    try:

        await update.message.copy(
            chat_id=user_id
        )

        await update.message.reply_text(
            "✅ Ответ отправлен."
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Ошибка: {e}"
        )

    return True


# =========================================================
# ВСЕ СООБЩЕНИЯ
# =========================================================

async def messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # Ответ админа
    if update.effective_user.id == ADMIN_ID:

        if update.message.reply_to_message:

            handled = await admin_answer(
                update,
                context
            )

            if handled:
                return

    # Промокод
    if context.user_data.get(
        "PROMO_WAIT"
    ):

        if update.message.text:

            await process_promo(
                update,
                context
            )

            return

    # Админ создание промо
    if update.effective_user.id == ADMIN_ID:

        state = context.user_data.get(
            "ADMIN_STATE"
        )

        if state == "AMOUNT":

            await admin_promo_amount(
                update,
                context
            )

            return

        if state == "USES":

            await admin_promo_uses(
                update,
                context
            )

            return

    # Вопрос
    if context.user_data.get(
        "QUESTION_WAIT"
    ):

        await receive_question(
            update,
            context
        )

        return


# =========================================================
# CALLBACK
# =========================================================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = update.callback_query.data

    logging.info(
        f"BUTTON: {data}"
    )

    # Главное
    if data == "BACK":

        await back(update, context)

    # Каталог
    elif data == "CATALOG":

        await catalog(update, context)

    # Покупки
    elif data.startswith("BUY_"):

        await buy(update, context)

    # Оплата
    elif data == "PAYMENT_DONE":

        await payment_done(update, context)

    elif data.startswith("CONFIRM_PAYMENT:"):

        await confirm_payment(update, context)

    # Промокод
    elif data == "PROMO":

        await promo(update, context)

    # Заказ
    elif data == "ORDER":

        await order(update, context)

    elif data == "ORDER_1":

        await order_confirm(update, context)

    elif data == "ORDER_CONFIRM":

        await order_confirmed(update, context)

    # Канал
    elif data == "CHANNEL":

        await channel(update, context)

    # Вопрос
    elif data == "QUESTION":

        await question(update, context)

    # Баланс
    elif data == "BALANCE":

        await show_balance(update, context)

    # Админ
    elif data == "ADMIN":

        await admin_panel(update, context)

    elif data == "ADMIN_PROMO":

        await admin_promo_start(update, context)

    elif data == "CREATE_PROMO":

        await create_promo(update, context)

    elif data == "ADMIN_STATS":

        await admin_stats(update, context)

    else:

        await update.callback_query.answer(
            "❌ Неизвестная кнопка.",
            show_alert=True
        )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Все кнопки
    app.add_handler(
        CallbackQueryHandler(
            callback
        )
    )

    # Все сообщения
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            messages
        )
    )

    print(
        "===================================="
    )
    print(
        "       CEKO HUB ЗАПУЩЕН"
    )
    print(
        "===================================="
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
