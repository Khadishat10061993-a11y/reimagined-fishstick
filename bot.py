import os
import re
import random
import string
import sqlite3
import time
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# CONFIG
# ============================================================

TOKEN = "8905175157:AAEo3tBv5V1pJGbJwWRoRXojMyj5qaJAxfw"

ADMIN_ID = 8161017993

ADMIN_USERNAME = "@netuzu"

CHANNEL_URL = "https://t.me/+lyHMe0599OtjYjEy"

START_PHOTO = "Start.jpg.PNG"
CATALOG_PHOTO = "Katalog.jpg.PNG"
JERRY_VIDEO = "Jerry.MOV"

DB_FILE = "ceko.db"

PENSION_COOLDOWN = 120


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("CEKO")


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(
    DB_FILE,
    check_same_thread=False
)

db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    balance INTEGER DEFAULT 0,
    pension REAL DEFAULT 0,
    pension_until INTEGER DEFAULT 0,
    broken INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    amount INTEGER NOT NULL,
    uses INTEGER NOT NULL
)
""")

db.commit()


# ============================================================
# TEMP DATA
# ============================================================

user_states = {}

admin_data = {}

question_users = {}


# ============================================================
# USER FUNCTIONS
# ============================================================

def ensure_user(user):

    db.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, balance, pension, pension_until, broken)
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


def balance(user_id):

    row = db.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    return row["balance"] if row else 0


def add_balance(user_id, amount):

    db.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    db.commit()


def take_balance(user_id, amount):

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


def uname(user):

    if user.username:
        return "@" + user.username

    return user.first_name or f"ID {user.id}"


def mention(user):

    if user.username:
        return "@" + user.username

    return (
        f'<a href="tg://user?id={user.id}">'
        f'{user.first_name or "Пользователь"}'
        f'</a>'
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_kb(user_id):

    rows = [
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
                f"💰 Баланс: {balance(user_id)}",
                callback_data="BALANCE"
            )
        ]
    ]

    if user_id == ADMIN_ID:

        rows.append([
            InlineKeyboardButton(
                "🔐 Панель",
                callback_data="ADMIN"
            )
        ])

    return InlineKeyboardMarkup(rows)


def back_kb(target="BACK"):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data=target
            )
        ]
    ])


# ============================================================
# SAFE EDIT
# ============================================================

async def edit(query, text, keyboard=None):

    try:

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )

        return True

    except Exception as e:

        logger.warning(
            "edit_message_text failed: %s",
            e
        )

        try:

            await query.message.reply_text(
                text=text,
                reply_markup=keyboard
            )

            return True

        except Exception as e2:

            logger.error(
                "reply_text failed: %s",
                e2
            )

            return False


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    ensure_user(user)

    user_states.pop(user.id, None)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {balance(user.id)} Деф"
    )

    if os.path.isfile(START_PHOTO):

        with open(START_PHOTO, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_kb(user.id)
            )

    else:

        await update.message.reply_text(
            text,
            reply_markup=main_kb(user.id)
        )


# ============================================================
# MAIN MENU
# ============================================================

async def main_menu(query):

    user = query.from_user

    ensure_user(user)

    user_states.pop(user.id, None)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {balance(user.id)} Деф"
    )

    # Если это фото — удаляем старое сообщение
    try:
        await query.message.delete()
    except Exception:
        pass

    if os.path.isfile(START_PHOTO):

        with open(START_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_kb(user.id)
            )

    else:

        await query.message.chat.send_message(
            text=text,
            reply_markup=main_kb(user.id)
        )


# ============================================================
# CATALOG
# ============================================================

async def catalog(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="PRODUCT|1|1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="PRODUCT|10|5"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="PRODUCT|25|10"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="PRODUCT|50|40"
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
        await query.message.delete()
    except Exception:
        pass

    if os.path.isfile(CATALOG_PHOTO):

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

async def product(query, amount, bears):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Готово",
                callback_data=f"PAY|{amount}|{bears}"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="CATALOG"
            )
        ]
    ])

    await edit(
        query,

        (
            f"Вы выбрали {amount} Деф очков.\n\n"
            f"Для того чтобы получить их перейдите в ЛС "
            f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
            "После этого нажмите кнопку «Готово»."
        ),

        keyboard
    )


# ============================================================
# PAYMENT
# ============================================================

async def payment(query, context, amount, bears):

    user = query.from_user

    ensure_user(user)

    await edit(
        query,
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    admin_keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"CONFIRM|{user.id}|{amount}"
            )
        ]
    ])

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "🆕 НОВАЯ ЗАЯВКА\n\n"
            f"👤 {uname(user)}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Деф: {amount}\n"
            f"🧸 Мишек: {bears}\n\n"
            "Проверь оплату."
        ),

        reply_markup=admin_keyboard
    )


async def confirm_payment(query, context, user_id, amount):

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

    await context.bot.send_message(

        chat_id=user_id,

        text=(
            "✅ Администратор проверил оплату "
            "и выдал вам Деф Очки.\n\n"
            f"➕ Получено: {amount} Деф\n"
            f"💰 Баланс: {balance(user_id)} Деф"
        )
    )

    await query.edit_message_text(
        query.message.text + "\n\n✅ ПОДТВЕРЖДЕНО"
    )


# ============================================================
# PROMOCODE
# ============================================================

async def promo(query):

    user_states[query.from_user.id] = "PROMO"

    await edit(
        query,

        "🫆 Промокод\n\n"
        "Отправьте промокод сообщением:",

        back_kb()
    )


async def check_promo(update, context):

    user = update.effective_user

    code = update.message.text.strip().upper()

    row = db.execute(
        """
        SELECT amount, uses
        FROM promos
        WHERE code=?
        """,
        (code,)
    ).fetchone()

    if not row:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_kb()
        )

        return

    if row["uses"] <= 0:

        await update.message.reply_text(
            "❌ Промокод больше недоступен.",
            reply_markup=back_kb()
        )

        return

    add_balance(
        user.id,
        row["amount"]
    )

    db.execute(
        """
        UPDATE promos
        SET uses = uses - 1
        WHERE code=?
        """,
        (code,)
    )

    db.commit()

    user_states.pop(
        user.id,
        None
    )

    await update.message.reply_text(

        "🎉 Промокод активирован!\n\n"
        f"➕ Получено: {row['amount']} Деф\n"
        f"💰 Баланс: {balance(user.id)} Деф",

        reply_markup=back_kb()
    )


# ============================================================
# ORDER
# ============================================================

async def order(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Деф Очка",
                callback_data="ORDER_ONE"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])

    await edit(
        query,

        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",

        keyboard
    )


async def order_one(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
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

    await edit(
        query,

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "⚠️ После подтверждения "
        "1 Деф будет списан с баланса.\n\n"
        "Подтвердить?",

        keyboard
    )


async def order_confirm(query, context):

    user = query.from_user

    ensure_user(user)

    # ВАЖНО:
    # атомарно снимаем именно 1 Деф
    success = take_balance(
        user.id,
        1
    )

    if not success:

        await edit(
            query,

            "❌ Недостаточно Деф Очков.\n\n"
            "Для заказа нужен минимум 1 Деф.",

            back_kb()
        )

        return

    await edit(
        query,

        "✅ Заказ принят!\n\n"
        "1 Деф списан с баланса.\n"
        "Администратор получил заявку.\n\n"
        f"💰 Осталось: {balance(user.id)} Деф"
    )

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(
            "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
            f"👤 {uname(user)}\n"
            f"🆔 {user.id}\n\n"
            "📦 Заказ: 1 Деф\n"
            "💸 Списано: 1 Деф\n\n"
            "Прошу перейти к пользователю."
        ),

        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Профиль",
                    url=f"tg://user?id={user.id}"
                )
            ]
        ])
    )


# ============================================================
# CHANNEL
# ============================================================

async def channel(query):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💬 Открыть канал",
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

    await edit(
        query,

        "💬 Секрет Тгк\n\n"
        "Нажмите кнопку ниже:",

        keyboard
    )


# ============================================================
# QUESTION
# ============================================================

async def question(query):

    user_states[query.from_user.id] = "QUESTION"

    await edit(
        query,

        "🔰 Вопрос к Ceko\n\n"
        "Отправьте сообщение любого типа.\n\n"
        "Администратор сможет ответить вам.",

        back_kb()
    )


async def receive_question(update, context):

    user = update.effective_user

    try:

        info = await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(
                "🔰 НОВЫЙ ВОПРОС\n\n"
                f"👤 {uname(user)}\n"
                f"🆔 {user.id}\n\n"
                "Ответьте реплаем на сообщение ниже."
            )
        )

        question_users[
            info.message_id
        ] = user.id

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_users[
            copied.message_id
        ] = user.id

        user_states.pop(
            user.id,
            None
        )

        await update.message.reply_text(
            "✅ Вопрос отправлен администратору.",
            reply_markup=back_kb()
        )

    except Exception as e:

        logger.exception(
            "QUESTION ERROR"
        )

        await update.message.reply_text(
            "❌ Ошибка отправки вопроса."
        )


# ============================================================
# ADMIN PANEL
# ============================================================

async def admin(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Нет доступа.",
            show_alert=True
        )

        return

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Создать промокод",
                callback_data="ADMIN_CREATE"
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
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])

    await edit(
        query,
        "🔐 Панель администратора\n\n"
        "Выберите действие:",
        keyboard
    )


async def admin_create(query):

    if query.from_user.id != ADMIN_ID:
        return

    admin_data.clear()

    user_states[ADMIN_ID] = "PROMO_AMOUNT"

    await edit(
        query,

        "➕ Создание промокода\n\n"
        "Напишите сколько Деф будет выдавать промокод.",

        back_kb("ADMIN")
    )


async def admin_amount(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        amount = int(update.message.text.strip())

        if amount <= 0:
            raise ValueError

    except:

        await update.message.reply_text(
            "❌ Нужно положительное число."
        )

        return

    admin_data["amount"] = amount

    user_states[ADMIN_ID] = "PROMO_USES"

    await update.message.reply_text(
        "Теперь напишите количество использований промокода.",
        reply_markup=back_kb("ADMIN")
    )


async def admin_uses(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uses = int(update.message.text.strip())

        if uses <= 0:
            raise ValueError

    except:

        await update.message.reply_text(
            "❌ Нужно положительное число."
        )

        return

    admin_data["uses"] = uses

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Создать",
                callback_data="ADMIN_CONFIRM"
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
        f"💰 Деф: {admin_data['amount']}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать?",

        reply_markup=keyboard
    )


def generate_code():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        exists = db.execute(
            "SELECT 1 FROM promos WHERE code=?",
            (code,)
        ).fetchone()

        if not exists:
            return code


async def admin_confirm(query):

    if query.from_user.id != ADMIN_ID:
        return

    if "amount" not in admin_data:
        return

    code = generate_code()

    db.execute(
        """
        INSERT INTO promos
        (code, amount, uses)
        VALUES (?, ?, ?)
        """,
        (
            code,
            admin_data["amount"],
            admin_data["uses"]
        )
    )

    db.commit()

    amount = admin_data["amount"]
    uses = admin_data["uses"]

    admin_data.clear()
    user_states.pop(ADMIN_ID, None)

    await edit(
        query,

        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 `{code}`\n"
        f"💰 {amount} Деф\n"
        f"👥 Использований: {uses}",

        admin_keyboard()
    )


def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Создать промокод",
                callback_data="ADMIN_CREATE"
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
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])


async def admin_stats(query):

    if query.from_user.id != ADMIN_ID:
        return

    users = db.execute(
        "SELECT COUNT(*) c FROM users"
    ).fetchone()["c"]

    total = db.execute(
        "SELECT COALESCE(SUM(balance),0) s FROM users"
    ).fetchone()["s"]

    promos = db.execute(
        "SELECT COUNT(*) c FROM promos"
    ).fetchone()["c"]

    await edit(
        query,

        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {users}\n"
        f"💰 Деф на балансах: {total}\n"
        f"🎟 Промокодов: {promos}",

        admin_keyboard()
    )


# ============================================================
# PENSION GAME
# ============================================================

async def pension(update, context):

    user = update.effective_user

    ensure_user(user)

    row = db.execute(
        """
        SELECT pension,
               pension_until,
               broken
        FROM users
        WHERE user_id=?
        """,
        (user.id,)
    ).fetchone()

    now = int(time.time())

    if row["broken"]:

        await update.message.reply_text(

            f"{mention(user)} бабки сломали вашу базу "
            "понижения пенсии",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"RESTORE|{user.id}"
                    )
                ]
            ])
        )

        return

    if row["pension_until"] > now:

        left = row["pension_until"] - now

        await update.message.reply_text(
            f"⏳ Подожди ещё {left} секунд."
        )

        return

    value = round(
        float(row["pension"]) + 0.1,
        1
    )

    db.execute(
        """
        UPDATE users
        SET pension=?,
            pension_until=?
        WHERE user_id=?
        """,
        (
            value,
            now + PENSION_COOLDOWN,
            user.id
        )
    )

    db.commit()

    if random.random() < 0.03:

        db.execute(
            """
            UPDATE users
            SET broken=1
            WHERE user_id=?
            """,
            (user.id,)
        )

        db.commit()

        await update.message.reply_text(

            f"{mention(user)} бабки сломали вашу базу "
            "понижения пенсии",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"RESTORE|{user.id}"
                    )
                ]
            ])
        )

    else:

        await update.message.reply_text(

            f"{mention(user)} понизил пенсию бабушкам\n\n"
            f"Понижено {value:.1f}%",

            parse_mode="HTML"
        )


async def restore(query, user_id):

    if query.from_user.id != user_id:

        await query.answer(
            "❌ Это не ваша база.",
            show_alert=True
        )

        return

    db.execute(
        """
        UPDATE users
        SET broken=0
        WHERE user_id=?
        """,
        (user_id,)
    )

    db.commit()

    await query.edit_message_text(
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

    text = "🏆 ТОП ПОНИЖЕНИЯ ПЕНСИИ\n\n"

    if not rows:

        text += "Пока никто не играл."

    else:

        for i, row in enumerate(rows, 1):

            name = (
                "@" + row["username"]
                if row["username"]
                else f"ID {row['user_id']}"
            )

            text += (
                f"{i}. {name} — "
                f"{float(row['pension']):.1f}%\n"
            )

    await update.message.reply_text(text)


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(update, context):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    logger.info(
        "BUTTON: user=%s data=%s",
        query.from_user.id,
        data
    )

    # Сразу убираем загрузку кнопки
    try:
        await query.answer()
    except Exception:
        pass

    try:

        # ----------------------------------------------------
        # MAIN
        # ----------------------------------------------------

        if data == "BACK":

            await main_menu(query)
            return

        if data == "CATALOG":

            await catalog(query)
            return

        if data == "PROMO":

            await promo(query)
            return

        if data == "ORDER":

            await order(query)
            return

        if data == "CHANNEL":

            await channel(query)
            return

        if data == "QUESTION":

            await question(query)
            return

        if data == "BALANCE":

            await query.answer(
                f"💰 Баланс: {balance(query.from_user.id)} Деф",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # PRODUCT
        # ----------------------------------------------------

        if data.startswith("PRODUCT|"):

            parts = data.split("|")

            if len(parts) != 3:
                return

            amount = int(parts[1])
            bears = int(parts[2])

            await product(
                query,
                amount,
                bears
            )

            return

        # ----------------------------------------------------
        # PAYMENT
        # ----------------------------------------------------

        if data.startswith("PAY|"):

            parts = data.split("|")

            if len(parts) != 3:
                return

            amount = int(parts[1])
            bears = int(parts[2])

            await payment(
                query,
                context,
                amount,
                bears
            )

            return

        if data.startswith("CONFIRM|"):

            parts = data.split("|")

            if len(parts) != 3:
                return

            user_id = int(parts[1])
            amount = int(parts[2])

            await confirm_payment(
                query,
                context,
                user_id,
                amount
            )

            return

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

        if data == "ORDER_ONE":

            await order_one(query)
            return

        if data == "ORDER_CONFIRM":

            await order_confirm(
                query,
                context
            )

            return

        # ----------------------------------------------------
        # RESTORE
        # ----------------------------------------------------

        if data.startswith("RESTORE|"):

            parts = data.split("|")

            if len(parts) != 2:
                return

            user_id = int(parts[1])

            await restore(
                query,
                user_id
            )

            return

        # ----------------------------------------------------
        # ADMIN
        # ----------------------------------------------------

        if data == "ADMIN":

            await admin(query)
            return

        if data == "ADMIN_CREATE":

            await admin_create(query)
            return

        if data == "ADMIN_CONFIRM":

            await admin_confirm(query)
            return

        if data == "ADMIN_STATS":

            await admin_stats(query)
            return

        # ----------------------------------------------------

        logger.warning(
            "UNKNOWN CALLBACK: %s",
            data
        )

    except Exception:

        logger.exception(
            "CALLBACK ERROR: %s",
            data
        )

        try:
            await query.answer(
                "❌ Ошибка обработки кнопки.",
                show_alert=True
            )
        except:
            pass


# ============================================================
# PRIVATE MESSAGES
# ============================================================

async def private_messages(update, context):

    user = update.effective_user

    if not user:
        return

    ensure_user(user)

    state = user_states.get(user.id)

    if state == "PROMO":

        if update.message.text:

            await check_promo(
                update,
                context
            )

        else:

            await update.message.reply_text(
                "❌ Отправьте промокод текстом.",
                reply_markup=back_kb()
            )

        return

    if state == "QUESTION":

        await receive_question(
            update,
            context
        )

        return

    if user.id == ADMIN_ID:

        if state == "PROMO_AMOUNT":

            await admin_amount(
                update,
                context
            )

            return

        if state == "PROMO_USES":

            await admin_uses(
                update,
                context
            )

            return


# ============================================================
# ADMIN REPLY
# ============================================================

async def admin_reply(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    message = update.message

    if not message.reply_to_message:
        return

    target = question_users.get(
        message.reply_to_message.message_id
    )

    if not target:
        return

    try:

        await message.copy(
            chat_id=target
        )

        await message.reply_text(
            "✅ Ответ отправлен."
        )

    except Exception as e:

        logger.error(
            "ADMIN REPLY ERROR: %s",
            e
        )


# ============================================================
# GROUP CHAT
# ============================================================

async def group_chat(update, context):

    message = update.message

    if not message:
        return

    if message.is_automatic_forward:
        return

    user = update.effective_user

    if not user or user.is_bot:
        return

    text = (
        message.text.strip().lower()
        if message.text
        else ""
    )

    # Русские игровые команды здесь НЕ обрабатываем,
    # потому что для них стоят отдельные handlers.
    if text in (
        "ппб",
        "понизить пенсию бабушкам",
        "топ"
    ):
        return

    # Ответ бота
    await message.reply_text(
        "Ceko на месте✅"
    )

    # Jerry
    if (
        random.random() < 0.01
        and os.path.isfile(JERRY_VIDEO)
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
                "JERRY ERROR: %s",
                e
            )


# ============================================================
# CHANNEL POST / DISCUSSION
# ============================================================

CHANNEL_RULES_TEXT = (
    "💬Здраствуйте Посетители этого чата\n"
    "Прошу вас не нарушать правила а именно\n"
    "Оск родни -\n"
    "Пиар чатов или тгк -\n"
    "Писать типо я тебя сватну или доксну -\n"
    "Общайтесь с матами приколами или чем то Ешё "
    "ну без всего этого что я перечислил 👆"
)


async def channel_auto_reply(update, context):

    message = update.message

    if not message:
        return

    if not message.is_automatic_forward:
        return

    # Только свежие сообщения
    if message.date:

        age = time.time() - message.date.timestamp()

        if age > 10:
            return

    try:

        await message.reply_text(
            CHANNEL_RULES_TEXT
        )

    except Exception as e:

        logger.error(
            "CHANNEL REPLY ERROR: %s",
            e
        )


# ============================================================
# COMMANDS
# ============================================================

async def lowerpension_command(update, context):
    await pension(update, context)


async def top_command(update, context):
    await top(update, context)


# ============================================================
# ERROR
# ============================================================

async def error_handler(update, context):

    logger.exception(
        "BOT ERROR:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN or TOKEN.startswith("ВСТАВЬ_"):

        print(
            "❌ Вставь новый токен в переменную TOKEN."
        )

        return

    app = (
        Application.builder()
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

    # ========================================================
    # ENGLISH COMMANDS
    # ========================================================

    app.add_handler(
        CommandHandler(
            "lowerpension",
            lowerpension_command
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_command
        )
    )

    # ========================================================
    # CALLBACKS
    #
    # ЭТО ГЛАВНЫЙ ОБРАБОТЧИК КНОПОК
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        ),
        group=0
    )

    # ========================================================
    # RUSSIAN GAME COMMANDS
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^ппб$"
            ),
            pension
        ),
        group=1
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^понизить пенсию бабушкам$"
            ),
            pension
        ),
        group=1
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"(?i)^топ$"
            ),
            top
        ),
        group=1
    )

    # ========================================================
    # PRIVATE
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & ~filters.COMMAND,
            private_messages
        ),
        group=2
    )

    # ========================================================
    # ADMIN REPLIES
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.REPLY,
            admin_reply
        ),
        group=3
    )

    # ========================================================
    # CHANNEL AUTO REPLY
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ALL,
            channel_auto_reply
        ),
        group=-10
    )

    # ========================================================
    # GROUP CHAT
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & ~filters.COMMAND,
            group_chat
        ),
        group=10
    )

    # ========================================================
    # ERROR
    # ========================================================

    app.add_error_handler(
        error_handler
    )

    print()
    print("======================================")
    print("        CEKO HUB STARTED")
    print("======================================")
    print("ADMIN:", ADMIN_ID)
    print("DATABASE:", DB_FILE)
    print("======================================")
    print()

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
