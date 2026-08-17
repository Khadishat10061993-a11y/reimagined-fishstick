import os
import time
import random
import string
import sqlite3
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

# Шанс появления Jerry
JERRY_CHANCE = 0.01

# Шанс поломки базы
BASE_BREAK_CHANCE = 0.03


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

cur = db.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    balance INTEGER DEFAULT 0,
    pension REAL DEFAULT 0,
    pension_cooldown INTEGER DEFAULT 0,
    base_broken INTEGER DEFAULT 0
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


# ============================================================
# MEMORY
# ============================================================

# Пользователь -> режим
user_states = {}

# message_id сообщения администратора -> ID пользователя
question_messages = {}


# ============================================================
# USER FUNCTIONS
# ============================================================

def register_user(user):

    cur.execute(
        """
        INSERT OR IGNORE INTO users
        (
            user_id,
            username,
            balance,
            pension,
            pension_cooldown,
            base_broken
        )
        VALUES (?, ?, 0, 0, 0, 0)
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


def get_balance(user_id):

    cur.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cur.fetchone()

    return row["balance"] if row else 0


def add_balance(user_id, amount):

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


def remove_balance(user_id, amount):

    cur.execute(
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

    return cur.rowcount == 1


def get_username(user):

    if user.username:
        return f"@{user.username}"

    return user.first_name or "Пользователь"


def mention(user):

    name = get_username(user)

    if user.username:
        return name

    return f'<a href="tg://user?id={user.id}">{name}</a>'


# ============================================================
# PROMO
# ============================================================

def generate_promo():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        cur.execute(
            """
            SELECT code
            FROM promos
            WHERE code = ?
            """,
            (code,)
        )

        if cur.fetchone() is None:
            return code


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(user_id):

    rows = [
        [
            InlineKeyboardButton(
                "🫀 Каталог",
                callback_data="menu_catalog"
            ),
            InlineKeyboardButton(
                "🫆 Промокод",
                callback_data="menu_promo"
            )
        ],

        [
            InlineKeyboardButton(
                "👾 Заказать Деф",
                callback_data="menu_order"
            )
        ],

        [
            InlineKeyboardButton(
                "💬 Секрет Тгк",
                callback_data="menu_channel"
            )
        ],

        [
            InlineKeyboardButton(
                "🔰 Вопрос к Ceko",
                callback_data="menu_question"
            )
        ],

        [
            InlineKeyboardButton(
                f"💰 Баланс: {get_balance(user_id)} Деф",
                callback_data="show_balance"
            )
        ]
    ]

    if user_id == ADMIN_ID:

        rows.append([
            InlineKeyboardButton(
                "🔐 Панель",
                callback_data="admin_panel"
            )
        ])

    return InlineKeyboardMarkup(rows)


def back_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back_main"
            )
        ]
    ])


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register_user(user)

    user_states.pop(user.id, None)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    try:

        with open(START_PHOTO, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id)
            )

    except FileNotFoundError:

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(user.id)
        )


# ============================================================
# MAIN MENU
# ============================================================

async def show_main(query, user_id):

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user_id)} Деф"
    )

    try:

        await query.message.delete()

    except Exception:
        pass

    try:

        with open(START_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user_id)
            )

    except FileNotFoundError:

        await query.message.chat.send_message(
            text=text,
            reply_markup=main_keyboard(user_id)
        )


# ============================================================
# BACK
# ============================================================

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_states.pop(query.from_user.id, None)

    await show_main(
        query,
        query.from_user.id
    )


# ============================================================
# BALANCE
# ============================================================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer(
        f"💰 Ваш баланс: {get_balance(query.from_user.id)} Деф",
        show_alert=True
    )


# ============================================================
# CATALOG
# ============================================================

async def menu_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="buy_1_1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="buy_10_5"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="buy_25_10"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="buy_50_40"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back_main"
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

    try:

        with open(CATALOG_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard
            )

    except FileNotFoundError:

        await query.message.chat.send_message(
            text=text,
            reply_markup=keyboard
        )


# ============================================================
# BUY
# ============================================================

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "buy_1_1":
        amount = 1
        bears = 1

    elif data == "buy_10_5":
        amount = 10
        bears = 5

    elif data == "buy_25_10":
        amount = 25
        bears = 10

    elif data == "buy_50_40":
        amount = 50
        bears = 40

    else:
        await query.answer("Ошибка товара", show_alert=True)
        return

    context.user_data["buy_amount"] = amount
    context.user_data["buy_bears"] = bears

    text = (
        f"Вы выбрали {amount} Деф очков.\n\n"
        f"Для того чтобы получить их перейдите в ЛС "
        f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
        "После этого нажмите кнопку ниже."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Готово",
                callback_data="payment_done"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="menu_catalog"
            )
        ]
    ])

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        text,
        reply_markup=keyboard
    )


# ============================================================
# PAYMENT DONE
# ============================================================

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    amount = context.user_data.get("buy_amount")
    bears = context.user_data.get("buy_bears")

    if not amount or not bears:

        await query.answer(
            "❌ Откройте каталог заново.",
            show_alert=True
        )

        return

    username = get_username(user)

    await query.message.edit_text(
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"confirm_payment_{user.id}_{amount}"
            )
        ]
    ])

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "🆕 НОВАЯ ЗАЯВКА\n\n"
            f"👤 Пользователь: {username}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Деф: {amount}\n"
            f"🧸 Мишек: {bears}\n\n"
            "Прошу проверить оплату."
        ),

        reply_markup=admin_keyboard
    )

    context.user_data.clear()


# ============================================================
# CONFIRM PAYMENT
# ============================================================

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    await query.answer()

    parts = query.data.split("_")

    user_id = int(parts[2])
    amount = int(parts[3])

    add_balance(
        user_id,
        amount
    )

    new_balance = get_balance(user_id)

    try:

        await context.bot.send_message(

            chat_id=user_id,

            text=(
                "✅ Администратор проверил оплату "
                "и выдал вам Деф Очки.\n\n"
                f"➕ Получено: {amount} Деф\n"
                f"💰 Баланс: {new_balance} Деф"
            )
        )

    except Exception as e:

        logger.error(
            f"Ошибка отправки пользователю: {e}"
        )

    await query.edit_message_text(
        query.message.text
        + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )


# ============================================================
# PROMO MENU
# ============================================================

async def menu_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_states[query.from_user.id] = "promo"

    await query.message.edit_text(

        "🫆 Промокод\n\n"
        "Введите промокод:",

        reply_markup=back_keyboard()
    )


# ============================================================
# PROMO PROCESS
# ============================================================

async def process_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    code = update.message.text.strip().upper()

    cur.execute(
        """
        SELECT amount, uses_left
        FROM promos
        WHERE code = ?
        """,
        (code,)
    )

    row = cur.fetchone()

    if not row:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_keyboard()
        )

        return

    if row["uses_left"] <= 0:

        await update.message.reply_text(
            "❌ Этот промокод больше недоступен.",
            reply_markup=back_keyboard()
        )

        return

    amount = row["amount"]

    add_balance(
        user.id,
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

    user_states.pop(user.id, None)

    await update.message.reply_text(

        "🎉 Промокод активирован!\n\n"
        f"➕ Получено: {amount} Деф\n"
        f"💰 Баланс: {get_balance(user.id)} Деф",

        reply_markup=back_keyboard()
    )


# ============================================================
# ORDER MENU
# ============================================================

async def menu_order(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

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
                callback_data="back_main"
            )
        ]
    ])

    await query.message.edit_text(

        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",

        reply_markup=keyboard
    )


# ============================================================
# ORDER ONE
# ============================================================

async def order_one(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

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
                callback_data="menu_order"
            )
        ]
    ])

    await query.message.edit_text(

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "⚠️ После подтверждения с вашего баланса "
        "будет списан 1 Деф.\n\n"
        "Подтвердить заказ?",

        reply_markup=keyboard
    )


# ============================================================
# ORDER CONFIRM
# ============================================================

async def order_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    register_user(user)

    # Реальное списание
    success = remove_balance(
        user.id,
        1
    )

    if not success:

        await query.message.edit_text(

            "❌ Недостаточно Деф Очков.\n\n"
            "Для заказа нужен минимум 1 Деф.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "◀️ Назад",
                        callback_data="back_main"
                    )
                ]
            ])
        )

        return

    username = get_username(user)

    await query.message.edit_text(

        "✅ Ваш заказ принят!\n\n"
        "1 Деф списан с баланса.\n"
        "Администратор получил заявку.\n\n"
        f"💰 Осталось: {get_balance(user.id)} Деф"
    )

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
            f"👤 Пользователь: {username}\n"
            f"🆔 ID: {user.id}\n"
            "📦 Заказ: 1 Деф\n"
            "💸 Списано: 1 Деф\n\n"
            "Прошу перейти к пользователю."
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

async def menu_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

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
                callback_data="back_main"
            )
        ]
    ])

    await query.message.edit_text(

        "💬 Секрет Тгк\n\n"
        "Нажмите кнопку ниже, чтобы перейти в канал.",

        reply_markup=keyboard
    )


# ============================================================
# QUESTION MENU
# ============================================================

async def menu_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_states[query.from_user.id] = "question"

    await query.message.edit_text(

        "🔰 Вопрос к Ceko\n\n"
        "Отправьте свой вопрос.\n\n"
        "Можно отправить текст, фото, видео, "
        "документ, голосовое, стикер и другие сообщения.\n\n"
        "Администратор ответит вам.",

        reply_markup=back_keyboard()
    )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Создать промокод",
                callback_data="admin_create_promo"
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
                callback_data="back_main"
            )
        ]
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await query.answer()

    await query.message.edit_text(

        "🔐 Панель администратора\n\n"
        "Выберите действие:",

        reply_markup=admin_keyboard()
    )


# ============================================================
# ADMIN CREATE PROMO
# ============================================================

async def admin_create_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    await query.answer()

    user_states[ADMIN_ID] = "promo_amount"

    await query.message.edit_text(

        "➕ Создание промокода\n\n"
        "Шаг 1\n\n"
        "Напишите, сколько Деф будет давать промокод.\n\n"
        "Например: 50",

        reply_markup=back_keyboard()
    )


async def admin_promo_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
            "❌ Нужно написать положительное число."
        )

        return

    context.user_data["promo_amount"] = amount

    user_states[ADMIN_ID] = "promo_uses"

    await update.message.reply_text(

        "Шаг 2\n\n"
        "Напишите, сколько раз можно использовать промокод.\n\n"
        "Например: 10",

        reply_markup=back_keyboard()
    )


async def admin_promo_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
            "❌ Нужно написать положительное число."
        )

        return

    context.user_data["promo_uses"] = uses

    user_states[ADMIN_ID] = "promo_confirm"

    amount = context.user_data["promo_amount"]

    await update.message.reply_text(

        "📋 Проверьте данные:\n\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать промокод?",

        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Создать",
                    callback_data="admin_promo_confirm"
                )
            ],

            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="admin_panel"
                )
            ]
        ])
    )


async def admin_promo_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    await query.answer()

    amount = context.user_data.get("promo_amount")
    uses = context.user_data.get("promo_uses")

    if not amount or not uses:

        await query.message.edit_text(
            "❌ Данные потеряны.",
            reply_markup=admin_keyboard()
        )

        return

    code = generate_promo()

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

    user_states.pop(ADMIN_ID, None)
    context.user_data.clear()

    await query.message.edit_text(

        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 Код: {code}\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}",

        reply_markup=admin_keyboard()
    )


# ============================================================
# ADMIN STATS
# ============================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Только администратор.",
            show_alert=True
        )

        return

    await query.answer()

    cur.execute(
        "SELECT COUNT(*) AS c FROM users"
    )

    users = cur.fetchone()["c"]

    cur.execute(
        "SELECT COUNT(*) AS c FROM promos"
    )

    promos = cur.fetchone()["c"]

    cur.execute(
        "SELECT COALESCE(SUM(balance), 0) AS s FROM users"
    )

    total = cur.fetchone()["s"]

    await query.message.edit_text(

        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {users}\n"
        f"🎟 Промокодов: {promos}\n"
        f"💰 Деф на балансах: {total}",

        reply_markup=admin_keyboard()
    )


# ============================================================
# PENSION GAME
# ============================================================

async def lower_pension(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register_user(user)

    cur.execute(
        """
        SELECT pension,
               pension_cooldown,
               base_broken
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cur.fetchone()

    now = int(time.time())

    # База сломана
    if row["base_broken"]:

        await update.message.reply_text(

            f"{mention(user)}, бабки сломали вашу "
            "базу понижения пенсии.\n\n"
            "Нажмите восстановить.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"restore_{user.id}"
                    )
                ]
            ]),

            parse_mode="HTML"
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

    old_value = float(row["pension"])

    if old_value <= 0:
        new_value = 0.1
    else:
        new_value = round(old_value + 0.1, 1)

    cur.execute(
        """
        UPDATE users
        SET pension = ?,
            pension_cooldown = ?
        WHERE user_id = ?
        """,
        (
            new_value,
            now + PENSION_COOLDOWN,
            user.id
        )
    )

    db.commit()

    await update.message.reply_text(

        f"{mention(user)} понизил пенсию бабушкам\n\n"
        f"Понижено {new_value:.1f}%",

        parse_mode="HTML"
    )

    # Случайная поломка
    if random.random() < BASE_BREAK_CHANCE:

        cur.execute(
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

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"restore_{user.id}"
                    )
                ]
            ]),

            parse_mode="HTML"
        )


# ============================================================
# RESTORE
# ============================================================

async def restore_base(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    parts = query.data.split("_")

    user_id = int(parts[1])

    if query.from_user.id != user_id:

        await query.answer(
            "❌ Это не ваша база.",
            show_alert=True
        )

        return

    cur.execute(
        """
        UPDATE users
        SET base_broken = 0
        WHERE user_id = ?
        """,
        (user_id,)
    )

    db.commit()

    await query.message.edit_text(
        "✅ Вы восстановили свою базу!"
    )


# ============================================================
# TOP
# ============================================================

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cur.execute(
        """
        SELECT username, user_id, pension
        FROM users
        WHERE pension > 0
        ORDER BY pension DESC
        LIMIT 10
        """
    )

    rows = cur.fetchall()

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
# ENGLISH COMMANDS
# ============================================================

async def lower_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await lower_pension(
        update,
        context
    )


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await top(
        update,
        context
    )


# ============================================================
# CHANNEL POST AUTO REPLY
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


async def channel_auto_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Только автоматические пересылки постов канала
    if not message.is_automatic_forward:
        return

    # Старше 10 секунд игнорируем
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
            f"Ошибка автоответа: {e}"
        )


# ============================================================
# QUESTIONS + PROMO + ADMIN INPUT + CHAT
# ============================================================

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    register_user(user)

    state = user_states.get(user.id)

    # ========================================================
    # ВОПРОС К CEKO
    # ========================================================

    if state == "question":

        try:

            info = await context.bot.send_message(

                chat_id=ADMIN_ID,

                text=(
                    "🔰 НОВЫЙ ВОПРОС\n\n"
                    f"👤 {get_username(user)}\n"
                    f"🆔 {user.id}\n\n"
                    "Ответьте реплаем на сообщение ниже."
                )
            )

            question_messages[
                info.message_id
            ] = user.id

            copied = await message.copy(
                chat_id=ADMIN_ID
            )

            question_messages[
                copied.message_id
            ] = user.id

            user_states.pop(user.id, None)

            await message.reply_text(
                "✅ Ваш вопрос отправлен администратору.",
                reply_markup=back_keyboard()
            )

        except Exception as e:

            logger.error(
                f"Ошибка вопроса: {e}"
            )

            await message.reply_text(
                "❌ Не удалось отправить вопрос."
            )

        return

    # ========================================================
    # ПРОМО
    # ========================================================

    if state == "promo":

        if message.text:

            await process_promo(
                update,
                context
            )

        return

    # ========================================================
    # АДМИН СОЗДАЁТ ПРОМО
    # ========================================================

    if user.id == ADMIN_ID:

        if state == "promo_amount":

            await admin_promo_amount(
                update,
                context
            )

            return

        if state == "promo_uses":

            await admin_promo_uses(
                update,
                context
            )

            return

    # ========================================================
    # ОТВЕТ АДМИНА
    # ========================================================

    if user.id == ADMIN_ID:

        if message.reply_to_message:

            target = question_messages.get(
                message.reply_to_message.message_id
            )

            if target:

                try:

                    await message.copy(
                        chat_id=target
                    )

                    await message.reply_text(
                        "✅ Ответ отправлен пользователю."
                    )

                except Exception as e:

                    await message.reply_text(
                        f"❌ Ошибка: {e}"
                    )

                return

    # ========================================================
    # ЧАТ
    # ========================================================

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Не отвечаем ботам
    if user.is_bot:
        return

    # Не отвечаем на авто-посты здесь
    if message.is_automatic_forward:
        return

    # ========================================================
    # CEKO НА МЕСТЕ
    # ========================================================

    await message.reply_text(
        "Ceko на месте✅"
    )

    # ========================================================
    # JERRY
    # ========================================================

    if random.random() <= JERRY_CHANCE:

        if os.path.exists(JERRY_VIDEO):

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
                    f"Ошибка Jerry: {e}"
                )


# ============================================================
# CALLBACKS
# ============================================================

# Здесь КАЖДАЯ кнопка имеет отдельный handler.
# Именно это исправляет проблему прошлой версии.


# Главное меню
# menu_catalog
# menu_promo
# menu_order
# menu_channel
# menu_question
# show_balance
# back_main

# ============================================================
# MAIN
# ============================================================

def main():

    if TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН":

        print(
            "❌ Вставь токен в переменную TOKEN."
        )

        return

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # ========================================================
    # COMMANDS
    # ========================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "lowerpension",
            lower_command
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_command
        )
    )

    # ========================================================
    # MAIN MENU BUTTONS
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            menu_catalog,
            pattern=r"^menu_catalog$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            menu_promo,
            pattern=r"^menu_promo$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            menu_order,
            pattern=r"^menu_order$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            menu_channel,
            pattern=r"^menu_channel$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            menu_question,
            pattern=r"^menu_question$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            show_balance,
            pattern=r"^show_balance$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            back_main,
            pattern=r"^back_main$"
        )
    )

    # ========================================================
    # CATALOG BUTTONS
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            buy_product,
            pattern=r"^buy_(1_1|10_5|25_10|50_40)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            payment_done,
            pattern=r"^payment_done$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            confirm_payment,
            pattern=r"^confirm_payment_[0-9]+_[0-9]+$"
        )
    )

    # ========================================================
    # ORDER
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            order_one,
            pattern=r"^order_one$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            order_confirm,
            pattern=r"^order_confirm$"
        )
    )

    # ========================================================
    # ADMIN
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            admin_panel,
            pattern=r"^admin_panel$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_create_promo,
            pattern=r"^admin_create_promo$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_promo_confirm,
            pattern=r"^admin_promo_confirm$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_stats,
            pattern=r"^admin_stats$"
        )
    )

    # ========================================================
    # RESTORE
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            restore_base,
            pattern=r"^restore_[0-9]+$"
        )
    )

    # ========================================================
    # RUSSIAN GAME COMMANDS
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^(ппб|понизить пенсию бабушкам)$"
            ),
            lower_pension
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
    # CHANNEL POSTS
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL,
            channel_auto_reply
        ),
        group=-1
    )

    # ========================================================
    # EVERYTHING ELSE
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_router
        ),
        group=1
    )

    # ========================================================
    # ERROR
    # ========================================================

    async def error_handler(update, context):

        logger.error(
            "Ошибка:",
            exc_info=context.error
        )

    app.add_error_handler(
        error_handler
    )

    print()
    print("========================================")
    print("       CEKO HUB BOT ЗАПУЩЕН")
    print("========================================")
    print("ADMIN:", ADMIN_ID)
    print("PENSION COOLDOWN:", PENSION_COOLDOWN)
    print("JERRY:", JERRY_CHANCE)
    print("========================================")
    print()

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
