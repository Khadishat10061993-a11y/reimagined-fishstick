import os
import random
import sqlite3
import string
import time
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyParameters,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = "8905175157:AAEo3tBv5V1pJGbJwWRoRXojMyj5qaJAxfw"

ADMIN_ID = 8161017993

ADMIN_USERNAME = "@netuzu"

CHANNEL_URL = "https://t.me/+lyHMe0599OtjYjEy"

START_PHOTO = "Start.jpg.PNG"
CATALOG_PHOTO = "Katalog.jpg.PNG"
JERRY_VIDEO = "Jerry.MOV"

PENSION_COOLDOWN = 120

# Шанс отправки Jerry после обычного сообщения
JERRY_CHANCE = 0.01

# Шанс поломки базы после ППБ
BREAK_CHANCE = 0.03


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(
    "ceko_hub.db",
    check_same_thread=False
)

db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    balance INTEGER DEFAULT 0,
    pension REAL DEFAULT 0,
    pension_cooldown INTEGER DEFAULT 0,
    base_broken INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    amount INTEGER NOT NULL,
    uses_left INTEGER NOT NULL
)
""")

db.commit()


# ============================================================
# MEMORY
# ============================================================

# user_id -> состояние
states = {}

# message_id в админском чате -> user_id
question_targets = {}


# ============================================================
# USERS
# ============================================================

def register_user(user):

    db.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, balance, pension, pension_cooldown, base_broken)
        VALUES (?, ?, 0, 0, 0, 0)
        """,
        (
            user.id,
            user.username or ""
        )
    )

    db.execute(
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


def get_balance(user_id):

    row = db.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    if row is None:
        return 0

    return row["balance"]


def add_balance(user_id, amount):

    db.execute(
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


def remove_balance(user_id, amount):

    cursor = db.execute(
        """
        UPDATE users
        SET balance = balance - ?
        WHERE user_id = ?
        AND balance >= ?
        """,
        (
            amount,
            user_id,
            amount
        )
    )

    db.commit()

    return cursor.rowcount == 1


def username_of(user):

    if user.username:
        return "@" + user.username

    return user.first_name or "Пользователь"


def mention(user):

    if user.username:
        return "@" + user.username

    return f'<a href="tg://user?id={user.id}">{user.first_name or "Пользователь"}</a>'


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(user_id):

    buttons = [

        [
            InlineKeyboardButton(
                "🫀 Каталог",
                callback_data="catalog"
            ),

            InlineKeyboardButton(
                "🫆 Промокод",
                callback_data="promo"
            )
        ],

        [
            InlineKeyboardButton(
                "👾 Заказать Деф",
                callback_data="order"
            )
        ],

        [
            InlineKeyboardButton(
                "💬 Секрет Тгк",
                callback_data="channel"
            )
        ],

        [
            InlineKeyboardButton(
                "🔰 Вопрос к Ceko",
                callback_data="question"
            )
        ],

        [
            InlineKeyboardButton(
                f"💰 Баланс: {get_balance(user_id)}",
                callback_data="balance"
            )
        ]
    ]

    if user_id == ADMIN_ID:

        buttons.append([
            InlineKeyboardButton(
                "🔐 Панель администратора",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def back_button(callback="back"):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data=callback
            )
        ]
    ])


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    register_user(user)

    states.pop(user.id, None)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    if os.path.exists(START_PHOTO):

        with open(START_PHOTO, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id)
            )

    else:

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(user.id)
        )


# ============================================================
# SHOW MAIN MENU
# ============================================================

async def show_main(query):

    user = query.from_user

    register_user(user)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    try:
        await query.message.delete()
    except Exception:
        pass

    if os.path.exists(START_PHOTO):

        with open(START_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id)
            )

    else:

        await query.message.chat.send_message(
            text=text,
            reply_markup=main_keyboard(user.id)
        )


# ============================================================
# CATALOG
# ============================================================

async def show_catalog(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="product:1:1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="product:10:5"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="product:25:10"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="product:50:40"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back"
            )
        ]
    ])

    text = (
        "🤖 Каталог валюты\n\n"
        "Действуют скидки - навсегда"
    )

    try:
        await query.message.delete()
    except Exception:
        pass

    if os.path.exists(CATALOG_PHOTO):

        with open(CATALOG_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard
            )

    else:

        await query.message.chat.send_message(
            text=text,
            reply_markup=keyboard
        )


# ============================================================
# PRODUCT
# ============================================================

async def show_product(query, amount, bears):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Готово",
                callback_data=f"payment:{amount}:{bears}"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="catalog"
            )
        ]
    ])

    text = (
        f"Вы выбрали {amount} Деф очков.\n\n"
        f"Для того чтобы получить их перейдите в ЛС "
        f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
        "После этого нажмите на нижнюю кнопку."
    )

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        text=text,
        reply_markup=keyboard
    )


# ============================================================
# PAYMENT
# ============================================================

async def payment_done(
    query,
    context,
    amount,
    bears
):

    user = query.from_user

    register_user(user)

    await query.message.edit_text(
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"confirm:{user.id}:{amount}"
            )
        ]
    ])

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "🆕 НОВАЯ ЗАЯВКА\n\n"
            f"👤 Пользователь: {username_of(user)}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Деф: {amount}\n"
            f"🧸 Мишек: {bears}\n\n"
            "Прошу проверить оплату и подтвердить получение."
        ),

        reply_markup=keyboard
    )


async def confirm_payment(
    query,
    context,
    user_id,
    amount
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    add_balance(
        user_id,
        amount
    )

    balance = get_balance(user_id)

    try:

        await context.bot.send_message(

            chat_id=user_id,

            text=(
                "✅ Администратор проверил оплату "
                "и выдал вам Деф Очки.\n\n"
                f"➕ Получено: {amount} Деф\n"
                f"💰 Баланс: {balance} Деф"
            )
        )

    except Exception as e:

        logger.error(
            f"Не удалось отправить подтверждение: {e}"
        )

    await query.message.edit_text(
        query.message.text +
        "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )


# ============================================================
# PROMO
# ============================================================

async def promo_menu(query):

    states[query.from_user.id] = "promo"

    await query.message.edit_text(

        "🫆 Промокод\n\n"
        "Введите промокод:",

        reply_markup=back_button()
    )


def generate_promo():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        exists = db.execute(
            "SELECT code FROM promos WHERE code = ?",
            (code,)
        ).fetchone()

        if not exists:
            return code


async def use_promo(update, context):

    user = update.effective_user

    code = update.message.text.strip().upper()

    row = db.execute(
        """
        SELECT amount, uses_left
        FROM promos
        WHERE code = ?
        """,
        (code,)
    ).fetchone()

    if not row:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_button()
        )

        return

    if row["uses_left"] <= 0:

        await update.message.reply_text(
            "❌ Этот промокод больше недоступен.",
            reply_markup=back_button()
        )

        return

    amount = row["amount"]

    add_balance(
        user.id,
        amount
    )

    db.execute(
        """
        UPDATE promos
        SET uses_left = uses_left - 1
        WHERE code = ?
        """,
        (code,)
    )

    db.commit()

    states.pop(user.id, None)

    await update.message.reply_text(

        "🎉 Промокод активирован!\n\n"
        f"➕ Получено: {amount} Деф\n"
        f"💰 Баланс: {get_balance(user.id)} Деф",

        reply_markup=back_button()
    )


# ============================================================
# ORDER
# ============================================================

async def order_menu(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Деф Очка",
                callback_data="order_one"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back"
            )
        ]
    ])

    await query.message.edit_text(
        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",
        reply_markup=keyboard
    )


async def order_one(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data="order_confirm"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="order"
            )
        ]
    ])

    await query.message.edit_text(

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "⚠️ После подтверждения с вашего "
        "баланса будет списан 1 Деф.\n\n"
        "Подтвердить заказ?",

        reply_markup=keyboard
    )


async def order_confirm(query, context):

    user = query.from_user

    register_user(user)

    # СНАЧАЛА проверяем и реально списываем
    if not remove_balance(user.id, 1):

        await query.message.edit_text(

            "❌ Недостаточно Деф Очков.\n\n"
            "Для заказа нужен минимум 1 Деф.",

            reply_markup=back_button()
        )

        return

    balance = get_balance(user.id)

    await query.message.edit_text(

        "✅ Ваш заказ принят!\n\n"
        "1 Деф списан с вашего баланса.\n"
        "Администратор получил заявку.\n\n"
        f"💰 Осталось: {balance} Деф"
    )

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
            f"👤 Пользователь: {username_of(user)}\n"
            f"🆔 ID: {user.id}\n"
            "📦 Заказ: 1 Деф\n"
            "💸 Списано: 1 Деф\n\n"
            "Прошу перейти к нему в личку."
        ),

        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Открыть профиль",
                    url=f"tg://user?id={user.id}"
                )
            ]
        ])
    )


# ============================================================
# CHANNEL
# ============================================================

async def channel_menu(query):

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
                callback_data="back"
            )
        ]
    ])

    await query.message.edit_text(

        "💬 Секрет Тгк\n\n"
        "Нажмите кнопку ниже, чтобы перейти в канал.",

        reply_markup=keyboard
    )


# ============================================================
# QUESTION
# ============================================================

async def question_menu(query):

    states[query.from_user.id] = "question"

    await query.message.edit_text(

        "🔰 Вопрос к Ceko\n\n"
        "Отправьте свой вопрос.\n\n"
        "Можно отправить текст, фото, видео, "
        "документ, голосовое, стикер и другое сообщение.\n\n"
        "Администратор ответит вам.",

        reply_markup=back_button()
    )


async def send_question(update, context):

    user = update.effective_user

    try:

        header = await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(
                "🔰 НОВЫЙ ВОПРОС\n\n"
                f"👤 {username_of(user)}\n"
                f"🆔 {user.id}\n\n"
                "Ответьте реплаем на сообщение ниже."
            )
        )

        question_targets[header.message_id] = user.id

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_targets[copied.message_id] = user.id

        states.pop(user.id, None)

        await update.message.reply_text(
            "✅ Ваш вопрос отправлен администратору.",
            reply_markup=back_button()
        )

    except Exception as e:

        logger.error(
            f"Question error: {e}"
        )

        await update.message.reply_text(
            "❌ Не удалось отправить вопрос."
        )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Создать промокод",
                callback_data="admin_create"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 Статистика",
                callback_data="admin_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back"
            )
        ]
    ])


async def admin_panel(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.message.edit_text(
        "🔐 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=admin_keyboard()
    )


async def admin_create(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    states[ADMIN_ID] = "promo_amount"

    await query.message.edit_text(

        "➕ Создание промокода\n\n"
        "Шаг 1.\n"
        "Напишите количество Деф, которое будет давать промокод.\n\n"
        "Например: 50",

        reply_markup=back_button("admin")
    )


async def admin_amount(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    try:

        amount = int(
            update.message.text.strip()
        )

        if amount <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Напиши положительное число."
        )

        return

    context.user_data["promo_amount"] = amount

    states[ADMIN_ID] = "promo_uses"

    await update.message.reply_text(

        "Шаг 2.\n\n"
        "На сколько использований создать промокод?\n\n"
        "Например: 10",

        reply_markup=back_button("admin")
    )


async def admin_uses(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    try:

        uses = int(
            update.message.text.strip()
        )

        if uses <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Напиши положительное число."
        )

        return

    context.user_data["promo_uses"] = uses

    amount = context.user_data["promo_amount"]

    states[ADMIN_ID] = "promo_confirm"

    await update.message.reply_text(

        "📋 Проверь данные:\n\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать промокод?",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "✅ Создать",
                    callback_data="admin_confirm"
                )
            ],

            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="admin"
                )
            ]

        ])
    )


async def admin_confirm(query, context):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    amount = context.user_data.get("promo_amount")
    uses = context.user_data.get("promo_uses")

    if not amount or not uses:

        await query.message.edit_text(
            "❌ Данные потеряны.",
            reply_markup=admin_keyboard()
        )

        return

    code = generate_promo()

    db.execute(
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

    states.pop(ADMIN_ID, None)
    context.user_data.clear()

    await query.message.edit_text(

        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 Промокод: `{code}`\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}",

        parse_mode="Markdown",

        reply_markup=admin_keyboard()
    )


async def admin_stats(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    users = db.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    promos = db.execute(
        "SELECT COUNT(*) AS c FROM promos"
    ).fetchone()["c"]

    balance = db.execute(
        "SELECT COALESCE(SUM(balance), 0) AS s FROM users"
    ).fetchone()["s"]

    await query.message.edit_text(

        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {users}\n"
        f"🎟 Промокодов: {promos}\n"
        f"💰 Деф на балансах: {balance}",

        reply_markup=admin_keyboard()
    )


# ============================================================
# PENSION GAME
# ============================================================

async def pension(update, context):

    user = update.effective_user

    if not user:
        return

    register_user(user)

    row = db.execute(
        """
        SELECT pension,
               pension_cooldown,
               base_broken
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    ).fetchone()

    now = int(time.time())

    # База сломана
    if row["base_broken"]:

        await update.message.reply_text(

            f"{mention(user)} бабки сломали вашу "
            "базу понижения пенсии",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"restore:{user.id}"
                    )
                ]
            ])
        )

        return

    # Кулдаун
    if row["pension_cooldown"] > now:

        remaining = row["pension_cooldown"] - now

        minutes = remaining // 60
        seconds = remaining % 60

        await update.message.reply_text(

            f"⏳ {mention(user)}, подожди "
            f"{minutes} мин. {seconds} сек.",

            parse_mode="HTML"
        )

        return

    old = float(row["pension"])

    if old <= 0:
        value = 0.1
    else:
        value = round(old + 0.1, 1)

    db.execute(
        """
        UPDATE users
        SET pension = ?,
            pension_cooldown = ?
        WHERE user_id = ?
        """,
        (
            value,
            now + PENSION_COOLDOWN,
            user.id
        )
    )

    db.commit()

    await update.message.reply_text(

        f"{mention(user)} понизил пенсию бабушкам\n\n"
        f"Понижено {value:.1f}%",

        parse_mode="HTML"
    )

    # Случайная поломка
    if random.random() < BREAK_CHANCE:

        db.execute(
            """
            UPDATE users
            SET base_broken = 1
            WHERE user_id = ?
            """,
            (user.id,)
        )

        db.commit()

        await update.message.reply_text(

            f"{mention(user)} бабки сломали вашу "
            "базу понижения пенсии",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"restore:{user.id}"
                    )
                ]
            ])
        )


async def restore(query):

    parts = query.data.split(":")

    if len(parts) != 2:
        return

    target_id = int(parts[1])

    if query.from_user.id != target_id:

        await query.answer(
            "❌ Это не ваша база.",
            show_alert=True
        )

        return

    db.execute(
        """
        UPDATE users
        SET base_broken = 0
        WHERE user_id = ?
        """,
        (target_id,)
    )

    db.commit()

    await query.message.edit_text(
        "✅ Вы восстановили свою базу!"
    )


async def top(update, context):

    rows = db.execute(
        """
        SELECT username, user_id, pension
        FROM users
        WHERE pension > 0
        ORDER BY pension DESC
        LIMIT 10
        """
    ).fetchall()

    if not rows:

        await update.message.reply_text(
            "🏆 Топ пока пуст."
        )

        return

    text = "🏆 ТОП ПОНИЖЕНИЯ ПЕНСИИ\n\n"

    for i, row in enumerate(rows, 1):

        if row["username"]:
            name = "@" + row["username"]
        else:
            name = f"ID {row['user_id']}"

        text += (
            f"{i}. {name} — "
            f"{float(row['pension']):.1f}%\n"
        )

    await update.message.reply_text(text)


# ============================================================
# CHANNEL AUTO REPLY
# ============================================================

CHANNEL_REPLY = (
    "💬Здраствуйте Посетители этого чата\n"
    "Прошу вас не нарушать правила а именно\n"
    "Оск родни -\n"
    "Пиар чатов или тгк -\n"
    "Писать типо я тебя сватну или доксну -\n"
    "Общайтесь с матами приколами или чем то Ешё "
    "ну без всего этого что я перечислил 👆"
)


async def automatic_channel_post(update, context):

    message = update.message

    if not message:
        return

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Telegram помечает автоматически пересланный
    # пост канала этим флагом.
    if not message.is_automatic_forward:
        return

    # Игнорируем старые посты.
    if message.date:

        age = time.time() - message.date.timestamp()

        if age > 10:
            return

    try:

        await context.bot.send_message(

            chat_id=message.chat.id,

            text=CHANNEL_REPLY,

            reply_parameters=ReplyParameters(
                message_id=message.message_id
            )
        )

    except Exception as e:

        logger.error(
            f"Channel reply error: {e}"
        )


# ============================================================
# ADMIN ANSWER
# ============================================================

async def admin_answer(update, context):

    message = update.message

    if not message:
        return

    if update.effective_user.id != ADMIN_ID:
        return

    if not message.reply_to_message:
        return False

    target_id = question_targets.get(
        message.reply_to_message.message_id
    )

    if not target_id:
        return False

    try:

        await message.copy(
            chat_id=target_id
        )

        await message.reply_text(
            "✅ Ответ отправлен."
        )

        return True

    except Exception as e:

        logger.error(
            f"Admin answer error: {e}"
        )

        return True


# ============================================================
# GENERAL CHAT
# ============================================================

async def general_chat(update, context):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    # Только группы
    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Не отвечаем ботам
    if user.is_bot:
        return

    # Пост канала уже обработал отдельный handler.
    if message.is_automatic_forward:
        return

    # Не отвечаем на команды.
    if message.text and message.text.startswith("/"):
        return

    # Игровые русские команды обработаются отдельно.
    if message.text:

        normalized = message.text.strip().lower()

        if normalized in (
            "ппб",
            "понизить пенсию бабушкам",
            "топ"
        ):
            return

    # Если пользователь находится в вопросе/промокоде,
    # обработка идёт через личные сообщения.
    if states.get(user.id) in (
        "question",
        "promo",
        "promo_amount",
        "promo_uses",
        "promo_confirm"
    ):
        return

    # Основной ответ
    await message.reply_text(
        "Ceko на месте✅"
    )

    # Случайный Jerry
    if (
        random.random() <= JERRY_CHANCE
        and os.path.exists(JERRY_VIDEO)
    ):

        try:

            with open(
                JERRY_VIDEO,
                "rb"
            ) as video:

                await message.reply_video(
                    video=video
                )

        except Exception as e:

            logger.error(
                f"Jerry error: {e}"
            )


# ============================================================
# PRIVATE MESSAGE ROUTER
# ============================================================

async def private_router(update, context):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    register_user(user)

    state = states.get(user.id)

    # Вопрос
    if state == "question":

        await send_question(
            update,
            context
        )

        return

    # Промокод
    if state == "promo":

        # Промокод должен быть текстом
        if message.text:

            await use_promo(
                update,
                context
            )

        else:

            await message.reply_text(
                "❌ Отправьте промокод текстом.",
                reply_markup=back_button()
            )

        return

    # Создание промокода админом
    if user.id == ADMIN_ID:

        if state == "promo_amount":

            await admin_amount(
                update,
                context
            )

            return

        if state == "promo_uses":

            await admin_uses(
                update,
                context
            )

            return

        # Ответ админа
        if await admin_answer(
            update,
            context
        ):

            return


# ============================================================
# ONE CALLBACK ROUTER
# ============================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    # ВСЕГДА закрываем "часики" кнопки
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""

    try:

        # ====================================================
        # НАЗАД
        # ====================================================

        if data == "back":

            states.pop(
                query.from_user.id,
                None
            )

            context.user_data.clear()

            await show_main(query)

            return

        # ====================================================
        # ГЛАВНОЕ МЕНЮ
        # ====================================================

        if data == "catalog":

            await show_catalog(query)

            return

        if data == "promo":

            await promo_menu(query)

            return

        if data == "order":

            await order_menu(query)

            return

        if data == "channel":

            await channel_menu(query)

            return

        if data == "question":

            await question_menu(query)

            return

        if data == "balance":

            await query.answer(
                f"💰 Баланс: {get_balance(query.from_user.id)} Деф",
                show_alert=True
            )

            return

        # ====================================================
        # ТОВАР
        # ====================================================

        if data.startswith("product:"):

            parts = data.split(":")

            amount = int(parts[1])
            bears = int(parts[2])

            await show_product(
                query,
                amount,
                bears
            )

            return

        # ====================================================
        # ОПЛАТА
        # ====================================================

        if data.startswith("payment:"):

            parts = data.split(":")

            amount = int(parts[1])
            bears = int(parts[2])

            await payment_done(
                query,
                context,
                amount,
                bears
            )

            return

        if data.startswith("confirm:"):

            parts = data.split(":")

            user_id = int(parts[1])
            amount = int(parts[2])

            await confirm_payment(
                query,
                context,
                user_id,
                amount
            )

            return

        # ====================================================
        # ЗАКАЗ ДЕФ
        # ====================================================

        if data == "order_one":

            await order_one(query)

            return

        if data == "order_confirm":

            await order_confirm(
                query,
                context
            )

            return

        # ====================================================
        # ВОССТАНОВЛЕНИЕ БАЗЫ
        # ====================================================

        if data.startswith("restore:"):

            await restore(query)

            return

        # ====================================================
        # АДМИНКА
        # ====================================================

        if data == "admin":

            await admin_panel(query)

            return

        if data == "admin_create":

            await admin_create(query)

            return

        if data == "admin_confirm":

            await admin_confirm(
                query,
                context
            )

            return

        if data == "admin_stats":

            await admin_stats(query)

            return

    except Exception as e:

        logger.exception(
            f"Callback error: {data}"
        )

        try:

            await query.answer(
                "❌ Произошла ошибка.",
                show_alert=True
            )

        except Exception:
            pass


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update, context):

    logger.error(
        "Ошибка бота:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if TOKEN == "ВСТАВЬ_НОВЫЙ_ТОКЕН_СЮДА":

        print(
            "❌ Сначала вставь токен в TOKEN."
        )

        return

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # ========================================================
    # START
    # ========================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Английские команды
    app.add_handler(
        CommandHandler(
            "lowerpension",
            pension
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top
        )
    )

    # ========================================================
    # ОДИН CALLBACK HANDLER
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # ========================================================
    # РУССКИЕ ИГРОВЫЕ КОМАНДЫ
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^(ппб|понизить пенсию бабушкам)$"
            ),
            pension
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^топ$"
            ),
            top
        )
    )

    # ========================================================
    # АВТООТВЕТ НА ПОСТЫ КАНАЛА
    #
    # СТАВИМ РАНЬШЕ ОБЫЧНОГО ЧАТА
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL,
            automatic_channel_post
        ),
        group=-10
    )

    # ========================================================
    # ЛИЧНЫЕ СООБЩЕНИЯ
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND
            & filters.ChatType.PRIVATE,
            private_router
        ),
        group=0
    )

    # ========================================================
    # ОБЫЧНЫЙ ГРУППОВОЙ ЧАТ
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND
            & filters.ChatType.GROUPS,
            general_chat
        ),
        group=1
    )

    # ========================================================
    # ERRORS
    # ========================================================

    app.add_error_handler(
        error_handler
    )

    print("===================================")
    print("       CEKO HUB ЗАПУЩЕН")
    print("===================================")
    print("Admin:", ADMIN_ID)
    print("Cooldown:", PENSION_COOLDOWN)
    print("===================================")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
