import sqlite3
import random
import string
import time
import os
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

# Вероятность Jerry на обычное сообщение.
# 0.01 = 1%
JERRY_CHANCE = 0.01

# Вероятность поломки базы после успешного ППБ.
# 0.03 = 3%
BASE_BREAK_CHANCE = 0.03

# ============================================================
# ЛОГИ
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
    pension REAL DEFAULT 0.0,
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
# ПОЛЬЗОВАТЕЛИ
# ============================================================

def register_user(user):

    cur.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, balance, pension,
         pension_cooldown, base_broken)
        VALUES (?, ?, 0, 0.0, 0, 0)
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

    if row:
        return row["balance"]

    return 0


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


def take_balance(user_id, amount):

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


# ============================================================
# ПРОМОКОДЫ
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
# ИМЯ ПОЛЬЗОВАТЕЛЯ
# ============================================================

def mention(user):

    if user.username:
        return f"@{user.username}"

    name = user.first_name or "Пользователь"

    return f'<a href="tg://user?id={user.id}">{name}</a>'


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_keyboard(user_id):

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
                f"💰 Баланс: {get_balance(user_id)} Деф",
                callback_data="BALANCE"
            )
        ]
    ]

    if user_id == ADMIN_ID:

        buttons.append([
            InlineKeyboardButton(
                "🔐 Панель администратора",
                callback_data="ADMIN"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def back_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="BACK"
            )
        ]
    ])


def admin_keyboard():

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


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

async def send_main_menu(chat_id, bot, user_id):

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user_id)} Деф"
    )

    try:

        with open(START_PHOTO, "rb") as photo:

            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user_id)
            )

    except FileNotFoundError:

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=main_keyboard(user_id)
        )


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register_user(user)

    context.user_data.clear()

    await send_main_menu(
        update.effective_chat.id,
        context.bot,
        user.id
    )


# ============================================================
# BACK
# ============================================================

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    try:
        await query.message.delete()
    except Exception:
        pass

    await send_main_menu(
        query.message.chat.id,
        context.bot,
        query.from_user.id
    )


# ============================================================
# КАТАЛОГ
# ============================================================

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    try:
        await query.message.delete()
    except Exception:
        pass

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="BUY:1:1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="BUY:10:5"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="BUY:25:10"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="BUY:50:40"
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


# ============================================================
# ВЫБОР ТОВАРА
# ============================================================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    _, amount, bears = query.data.split(":")

    amount = int(amount)
    bears = int(bears)

    context.user_data["buy_amount"] = amount
    context.user_data["buy_bears"] = bears

    try:
        await query.message.delete()
    except Exception:
        pass

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
        f"Для того чтобы получить их, перейдите в ЛС "
        f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
        "После этого нажмите кнопку «Готово».",

        reply_markup=keyboard
    )


# ============================================================
# ГОТОВО — ОПЛАТА
# ============================================================

async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    amount = context.user_data.get("buy_amount")
    bears = context.user_data.get("buy_bears")

    if not amount:

        await query.answer(
            "❌ Заявка потеряна. Откройте каталог заново.",
            show_alert=True
        )

        return

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    try:
        await query.message.delete()
    except Exception:
        pass

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
        "Прошу проверить оплату и подтвердить получение.",

        reply_markup=keyboard
    )

    context.user_data.clear()


# ============================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
# ============================================================

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

    _, user_id, amount = query.data.split(":")

    user_id = int(user_id)
    amount = int(amount)

    add_balance(
        user_id,
        amount
    )

    try:

        await context.bot.send_message(

            user_id,

            "✅ Администратор проверил оплату "
            "и выдал вам Деф Очки.\n\n"
            f"➕ Получено: {amount} Деф\n"
            f"💰 Баланс: {get_balance(user_id)} Деф"
        )

    except Exception as e:

        logger.error(
            f"Не удалось уведомить пользователя: {e}"
        )

    await query.message.edit_text(
        query.message.text
        + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )


# ============================================================
# ПРОМОКОД
# ============================================================

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["PROMO_WAIT"] = True

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(

        "🫆 Промокод\n\n"
        "Введите промокод:",

        reply_markup=back_keyboard()
    )


async def process_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get("PROMO_WAIT"):
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

    row = cur.fetchone()

    if not row:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_keyboard()
        )

        return True

    amount = row["amount"]
    uses_left = row["uses_left"]

    if uses_left <= 0:

        await update.message.reply_text(
            "❌ Этот промокод больше недоступен.",
            reply_markup=back_keyboard()
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
        f"➕ Получено: {amount} Деф\n"
        f"💰 Баланс: {get_balance(update.effective_user.id)} Деф",

        reply_markup=back_keyboard()
    )

    return True


# ============================================================
# ЗАКАЗАТЬ ДЕФ
# ============================================================

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    try:
        await query.message.delete()
    except Exception:
        pass

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

    await query.message.chat.send_message(

        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",

        reply_markup=keyboard
    )


# ============================================================
# ВЫБРАЛ 1 ДЕФ
# ============================================================

async def order_one(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await query.message.edit_text(

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "⚠️ После подтверждения с вашего баланса "
        "будет списан 1 Деф.\n\n"
        "Подтвердить заказ?",

        reply_markup=InlineKeyboardMarkup([
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
    )


# ============================================================
# ПОДТВЕРЖДЕНИЕ ЗАКАЗА
# ============================================================

async def order_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    register_user(user)

    # ========================================================
    # ГЛАВНОЕ ИСПРАВЛЕНИЕ:
    # РЕАЛЬНО СПИСЫВАЕМ 1 ДЕФ
    # ========================================================

    success = take_balance(
        user.id,
        1
    )

    if not success:

        await query.message.edit_text(

            "❌ Недостаточно Деф Очков.\n\n"
            "Для заказа необходимо иметь минимум "
            "1 Деф на балансе.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "◀️ Назад",
                        callback_data="BACK"
                    )
                ]
            ])
        )

        return

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    await query.message.edit_text(

        "✅ Ваш заказ принят!\n\n"
        "1 Деф списан с баланса.\n"
        "Администратор скоро обработает заказ.\n\n"
        f"💰 Осталось: {get_balance(user.id)} Деф"
    )

    await context.bot.send_message(

        ADMIN_ID,

        "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n"
        "📦 Заказ: 1 Деф\n"
        "💸 Списано с баланса: 1 Деф\n\n"
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


# ============================================================
# СЕКРЕТ ТГК
# ============================================================

async def channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(

        "💬 Секрет Тгк\n\n"
        "Нажмите кнопку ниже, чтобы перейти в канал.",

        reply_markup=InlineKeyboardMarkup([
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
    )


# ============================================================
# ВОПРОС К CEKO
# ============================================================

question_users = {}


async def question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["QUESTION_WAIT"] = True

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(

        "🔰 Вопрос к Ceko\n\n"
        "Отправьте свой вопрос.\n\n"
        "Можно отправить текст, фото, видео, "
        "документ, голосовое, стикер и т.д.\n\n"
        "Администратор ответит вам.",

        reply_markup=back_keyboard()
    )


async def receive_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get("QUESTION_WAIT"):
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

    question_users[info.message_id] = user.id

    try:

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_users[copied.message_id] = user.id

    except Exception as e:

        logger.error(
            f"Ошибка копирования вопроса: {e}"
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Ваш вопрос отправлен администратору.",
        reply_markup=back_keyboard()
    )

    return True


# ============================================================
# ОТВЕТ АДМИНА НА ВОПРОС
# ============================================================

async def admin_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not update.message.reply_to_message:
        return False

    reply_id = (
        update.message
        .reply_to_message
        .message_id
    )

    user_id = question_users.get(
        reply_id
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
            f"❌ Не удалось отправить ответ: {e}"
        )

    return True


# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================

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

    await query.message.edit_text(

        "🔐 Панель администратора\n\n"
        "Выберите действие:",

        reply_markup=admin_keyboard()
    )


# ============================================================
# СОЗДАНИЕ ПРОМО — ШАГ 1
# ============================================================

async def admin_promo_start(
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

    context.user_data.clear()

    context.user_data["ADMIN_STATE"] = "PROMO_AMOUNT"

    await query.message.edit_text(

        "➕ Создание промокода\n\n"
        "Шаг 1/2\n\n"
        "Напишите, сколько Деф Очков "
        "будет давать промокод.\n\n"
        "Например: 50"
    )


# ============================================================
# ПРОМО — ШАГ 2
# ============================================================

async def admin_promo_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "ADMIN_STATE"
    ) != "PROMO_AMOUNT":
        return False

    try:

        amount = int(
            update.message.text.strip()
        )

        if amount <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите положительное число."
        )

        return True

    context.user_data[
        "PROMO_AMOUNT"
    ] = amount

    context.user_data[
        "ADMIN_STATE"
    ] = "PROMO_USES"

    await update.message.reply_text(

        "Шаг 2/2\n\n"
        "Сколько раз можно использовать "
        "этот промокод?\n\n"
        "Например: 10"
    )

    return True


async def admin_promo_uses(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "ADMIN_STATE"
    ) != "PROMO_USES":
        return False

    try:

        uses = int(
            update.message.text.strip()
        )

        if uses <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите положительное число."
        )

        return True

    amount = context.user_data["PROMO_AMOUNT"]

    context.user_data["PROMO_USES"] = uses

    context.user_data["ADMIN_STATE"] = "PROMO_CONFIRM"

    await update.message.reply_text(

        "📋 Данные промокода:\n\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать?",

        reply_markup=InlineKeyboardMarkup([
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
    )

    return True


# ============================================================
# СОЗДАНИЕ ПРОМО
# ============================================================

async def create_promo(
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

    amount = context.user_data.get(
        "PROMO_AMOUNT"
    )

    uses = context.user_data.get(
        "PROMO_USES"
    )

    if not amount or not uses:

        await query.message.edit_text(
            "❌ Данные промокода потеряны.",
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

    context.user_data.clear()

    await query.message.edit_text(

        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 Код: {code}\n"
        f"💰 Деф: {amount}\n"
        f"👥 Использований: {uses}",

        reply_markup=admin_keyboard()
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

async def admin_stats(
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

    cur.execute(
        "SELECT COUNT(*) AS c FROM users"
    )

    users = cur.fetchone()["c"]

    cur.execute(
        "SELECT COUNT(*) AS c FROM promos"
    )

    promos = cur.fetchone()["c"]

    cur.execute(
        """
        SELECT COALESCE(SUM(balance), 0) AS s
        FROM users
        """
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
# ИГРА — ПОЛОЖИТЕЛЬНОЕ ЗНАЧЕНИЕ
# ============================================================

def get_pension(user_id):

    cur.execute(
        """
        SELECT pension
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cur.fetchone()

    if row:
        return float(row["pension"])

    return 0.0


# ============================================================
# ИГРА — ПОНИЗИТЬ ПЕНСИЮ
# ============================================================

async def lower_pension(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    # --------------------------------------------------------
    # БАЗА СЛОМАНА
    # --------------------------------------------------------

    if row["base_broken"] == 1:

        await update.message.reply_text(

            f"{mention(user)}, бабки сломали вашу "
            "базу понижения пенсии.\n\n"
            "Сначала восстановите её.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"RESTORE:{user.id}"
                    )
                ]
            ]),

            parse_mode="HTML"
        )

        return

    # --------------------------------------------------------
    # КУЛДАУН
    # --------------------------------------------------------

    cooldown = row["pension_cooldown"]

    if cooldown > now:

        remaining = cooldown - now

        minutes = remaining // 60
        seconds = remaining % 60

        await update.message.reply_text(

            f"⏳ {mention(user)}, подожди "
            f"{minutes} мин. {seconds} сек.",

            parse_mode="HTML"
        )

        return

    # --------------------------------------------------------
    # УВЕЛИЧИВАЕМ НА 0.1
    # --------------------------------------------------------

    old_value = float(row["pension"])

    new_value = round(
        old_value + 0.1,
        1
    )

    # Первый раз = 0.1
    if old_value <= 0:
        new_value = 0.1

    new_cooldown = now + PENSION_COOLDOWN

    cur.execute(
        """
        UPDATE users
        SET pension = ?,
            pension_cooldown = ?
        WHERE user_id = ?
        """,
        (
            new_value,
            new_cooldown,
            user.id
        )
    )

    db.commit()

    await update.message.reply_text(

        f"{mention(user)} понизил пенсию бабушкам\n\n"
        f"Понижено {new_value:.1f}%",

        parse_mode="HTML"
    )

    # --------------------------------------------------------
    # СЛУЧАЙНАЯ ПОЛОМКА БАЗЫ
    # --------------------------------------------------------

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

            f"{mention(user)}, бабки сломали вашу "
            "базу понижения пенсии\n\n"
            "Теперь её нужно восстановить.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"RESTORE:{user.id}"
                    )
                ]
            ]),

            parse_mode="HTML"
        )


# ============================================================
# ВОССТАНОВИТЬ БАЗУ
# ============================================================

async def restore_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user = query.from_user

    _, target_id = query.data.split(":")

    target_id = int(target_id)

    if target_id != user.id:

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
        (user.id,)
    )

    db.commit()

    await query.answer(
        "🔨 База восстановлена!"
    )

    await query.message.edit_text(
        "✅ Вы восстановили свою базу!"
    )


# ============================================================
# ТОП
# ============================================================

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cur.execute(
        """
        SELECT user_id, username, pension
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

    for index, row in enumerate(rows, 1):

        username = row["username"]

        if username:
            name = f"@{username}"
        else:
            name = f"ID {row['user_id']}"

        text += (
            f"{index}. {name} — "
            f"{float(row['pension']):.1f}%\n"
        )

    await update.message.reply_text(text)


# ============================================================
# ОТВЕТ CEKO НА ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

async def normal_chat_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    # Не отвечаем ботам
    if user.is_bot:
        return

    # --------------------------------------------------------
    # Если это команда /lowerpension или /top,
    # их обработают отдельные handlers
    # --------------------------------------------------------

    if message.text:

        text = message.text.strip().lower()

        russian_pension = (
            text == "ппб"
            or text == "понизить пенсию бабушкам"
        )

        russian_top = (
            text == "топ"
        )

        if russian_pension or russian_top:
            return

    # --------------------------------------------------------
    # Не отвечаем на автоматический пост канала
    # здесь, он обрабатывается отдельно.
    # --------------------------------------------------------

    if message.is_automatic_forward:
        return

    # --------------------------------------------------------
    # ВОПРОС К CEKO
    # --------------------------------------------------------

    if context.user_data.get("QUESTION_WAIT"):

        handled = await receive_question(
            update,
            context
        )

        if handled:
            return

    # --------------------------------------------------------
    # АДМИН СОЗДАЁТ ПРОМО
    # --------------------------------------------------------

    if user.id == ADMIN_ID:

        state = context.user_data.get(
            "ADMIN_STATE"
        )

        if state == "PROMO_AMOUNT":

            await admin_promo_amount(
                update,
                context
            )

            return

        if state == "PROMO_USES":

            await admin_promo_uses(
                update,
                context
            )

            return

    # --------------------------------------------------------
    # ПРОМОКОД
    # --------------------------------------------------------

    if context.user_data.get("PROMO_WAIT"):

        if message.text:

            await process_promo(
                update,
                context
            )

            return

    # --------------------------------------------------------
    # ОТВЕТ АДМИНА
    # --------------------------------------------------------

    if user.id == ADMIN_ID:

        if message.reply_to_message:

            handled = await admin_answer(
                update,
                context
            )

            if handled:
                return

    # --------------------------------------------------------
    # ТОЛЬКО ГРУППЫ
    # --------------------------------------------------------

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # --------------------------------------------------------
    # Ceko на месте
    # --------------------------------------------------------

    await message.reply_text(
        "Ceko на месте✅"
    )

    # --------------------------------------------------------
    # RANDOM JERRY
    # --------------------------------------------------------

    if random.random() < JERRY_CHANCE:

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
                    f"Ошибка Jerry.MOV как video: {e}"
                )

                try:

                    with open(
                        JERRY_VIDEO,
                        "rb"
                    ) as document:

                        await message.reply_document(
                            document=document
                        )

                except Exception as e2:

                    logger.error(
                        f"Ошибка отправки Jerry: {e2}"
                    )


# ============================================================
# АВТОМАТИЧЕСКИЙ ОТВЕТ НА ПОСТ КАНАЛА
# ============================================================

CHANNEL_AUTO_REPLY = (
    "💬Здраствуйте Посетители этого чата\n"
    "Прошу вас не нарушать правила а именно\n"
    "Оск родни -\n"
    "Пиар чатов или тгк -\n"
    "Писать типо я тебя сватну или доксну -\n"
    "Общайтесь с матами приколами или чем то Ешё "
    "ну без всего этого что я перечислил 👆"
)


async def channel_discussion_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    # Только группы/супергруппы
    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Telegram помечает автоматически пересланный
    # пост канала как automatic forward.
    if not message.is_automatic_forward:
        return

    # --------------------------------------------------------
    # ИГНОРИРУЕМ СТАРЫЕ ПОСТЫ
    # --------------------------------------------------------

    if message.date:

        age = time.time() - message.date.timestamp()

        if age > 10:
            logger.info(
                f"Старый пост пропущен: {age:.2f} сек."
            )

            return

    # --------------------------------------------------------
    # ОТВЕЧАЕМ ИМЕННО НА ЭТОТ ПОСТ
    # --------------------------------------------------------

    try:

        await context.bot.send_message(

            chat_id=message.chat.id,

            text=CHANNEL_AUTO_REPLY,

            reply_parameters=ReplyParameters(
                message_id=message.message_id
            )
        )

        logger.info(
            "Автоответ на пост канала отправлен."
        )

    except Exception as e:

        logger.error(
            f"Ошибка автоответа канала: {e}"
        )


# ============================================================
# ENGLISH COMMANDS
# ============================================================

async def lower_pension_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await lower_pension(
        update,
        context
    )


async def top_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await top(
        update,
        context
    )


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    data = query.data

    logger.info(
        f"CALLBACK: {data}"
    )

    if data == "BACK":

        await back(
            update,
            context
        )

    elif data == "CATALOG":

        await catalog(
            update,
            context
        )

    elif data.startswith("BUY:"):

        await buy(
            update,
            context
        )

    elif data == "PAYMENT_DONE":

        await payment_done(
            update,
            context
        )

    elif data.startswith("CONFIRM_PAYMENT:"):

        await confirm_payment(
            update,
            context
        )

    elif data == "PROMO":

        await promo(
            update,
            context
        )

    elif data == "ORDER":

        await order(
            update,
            context
        )

    elif data == "ORDER_ONE":

        await order_one(
            update,
            context
        )

    elif data == "ORDER_CONFIRM":

        await order_confirm(
            update,
            context
        )

    elif data == "CHANNEL":

        await channel(
            update,
            context
        )

    elif data == "QUESTION":

        await question(
            update,
            context
        )

    elif data == "BALANCE":

        await query.answer(
            f"💰 Баланс: "
            f"{get_balance(query.from_user.id)} Деф",
            show_alert=True
        )

    elif data == "ADMIN":

        await admin_panel(
            update,
            context
        )

    elif data == "ADMIN_PROMO":

        await admin_promo_start(
            update,
            context
        )

    elif data == "CREATE_PROMO":

        await create_promo(
            update,
            context
        )

    elif data == "ADMIN_STATS":

        await admin_stats(
            update,
            context
        )

    elif data.startswith("RESTORE:"):

        await restore_base(
            update,
            context
        )

    else:

        await query.answer(
            "❌ Неизвестная кнопка.",
            show_alert=True
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Ошибка бота:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН":

        print(
            "❌ Сначала вставь токен в переменную TOKEN."
        )

        return

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # /start
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # --------------------------------------------------------
    # Английские команды
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "lowerpension",
            lower_pension_command
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_command
        )
    )

    # --------------------------------------------------------
    # КНОПКИ
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            callbacks
        )
    )

    # --------------------------------------------------------
    # Русские игровые команды
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # АВТОПОСТЫ КАНАЛА
    # Ставим раньше обычного обработчика сообщений.
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE
            & filters.ALL,
            channel_discussion_reply
        ),
        group=0
    )

    # --------------------------------------------------------
    # ВСЕ ОСТАЛЬНЫЕ СООБЩЕНИЯ
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            normal_chat_message
        ),
        group=1
    )

    # --------------------------------------------------------
    # ОШИБКИ
    # --------------------------------------------------------

    app.add_error_handler(
        error_handler
    )

    print(
        "============================================"
    )

    print(
        "          CEKO HUB BOT ЗАПУЩЕН"
    )

    print(
        "============================================"
    )

    print(
        f"ADMIN ID: {ADMIN_ID}"
    )

    print(
        "PENSION COOLDOWN: 120 sec"
    )

    print(
        "JERRY CHANCE: 1%"
    )

    print(
        "============================================"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
