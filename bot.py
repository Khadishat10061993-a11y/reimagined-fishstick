import sqlite3
import random
import string
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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

# Сюда поставь Telegram ID администратора
ADMIN_ID = 8161017993

ADMIN_USERNAME = "@netuzu"
CHANNEL_URL = "https://t.me/+lyHMe0599OtjYjEy"

# Названия фотографий
START_PHOTO = "Start.jpg.PNG"
CATALOG_PHOTO = "Katalog.jpg.PNG"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =========================================================
# БАЗА ДАННЫХ
# =========================================================

db = sqlite3.connect(
    "ceko_hub.db",
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    amount INTEGER,
    uses_left INTEGER
)
""")

db.commit()

# =========================================================
# ВРЕМЕННЫЕ ДАННЫЕ
# =========================================================

purchase_data = {}

question_messages = {}

# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

def register_user(user):
    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, balance)
        VALUES (?, ?, 0)
        """,
        (
            user.id,
            user.username or "без_username"
        )
    )

    cursor.execute(
        """
        UPDATE users
        SET username=?
        WHERE user_id=?
        """,
        (
            user.username or "без_username",
            user.id
        )
    )

    db.commit()


def get_balance(user_id):
    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


def add_balance(user_id, amount):
    cursor.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
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

def generate_promo():
    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        cursor.execute(
            """
            SELECT code
            FROM promos
            WHERE code=?
            """,
            (code,)
        )

        if not cursor.fetchone():
            return code


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def main_keyboard(user_id):

    balance = get_balance(user_id)

    return InlineKeyboardMarkup([
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
                callback_data="def_order"
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
                f"💰 Баланс: {balance} Деф",
                callback_data="balance"
            )
        ]
    ])


def back_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back"
            )
        ]
    ])


def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Добавить промо",
                callback_data="admin_add_promo"
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
                callback_data="admin_back"
            )
        ]
    ])


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register_user(user)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
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
            "❌ Не найден файл Start.jpg.PNG\n\n"
            + text,
            reply_markup=main_keyboard(user.id)
        )


# =========================================================
# КАТАЛОГ
# =========================================================

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Мишка",
                callback_data="buy_1"
            )
        ],

        [
            InlineKeyboardButton(
                "10 Деф - 5 Мишек",
                callback_data="buy_10"
            )
        ],

        [
            InlineKeyboardButton(
                "25 Деф - 10 Мишек",
                callback_data="buy_25"
            )
        ],

        [
            InlineKeyboardButton(
                "50 Деф - 40 Мишек",
                callback_data="buy_50"
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

        with open(CATALOG_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard
            )

    except FileNotFoundError:

        await query.message.edit_text(
            "❌ Не найден файл Katalog.jpg.PNG\n\n"
            + text,
            reply_markup=keyboard
        )

    except Exception:

        try:

            await query.message.edit_text(
                text,
                reply_markup=keyboard
            )

        except Exception:
            pass


# =========================================================
# ВЫБОР ТОВАРА
# =========================================================

async def select_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    amount = int(
        query.data.split("_")[1]
    )

    prices = {
        1: 1,
        10: 5,
        25: 10,
        50: 40
    }

    bears = prices[amount]

    purchase_data[query.from_user.id] = {
        "def": amount,
        "bears": bears
    }

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
                callback_data="catalog"
            )
        ]
    ])

    text = (
        f"Вы выбрали {amount} Деф очков.\n\n"
        f"Для того чтобы получить их, перейдите в ЛС "
        f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
        "После этого нажмите на нижнюю кнопку."
    )

    await query.message.edit_text(
        text,
        reply_markup=keyboard
    )


# =========================================================
# ГОТОВО / ОПЛАТА
# =========================================================

async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    data = purchase_data.get(user.id)

    if not data:

        await query.message.edit_text(
            "❌ Заявка не найдена.",
            reply_markup=back_keyboard()
        )

        return

    amount = data["def"]
    bears = data["bears"]

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    await query.message.edit_text(
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    admin_text = (
        "🆕 НОВАЯ ЗАЯВКА\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Деф: {amount}\n"
        f"🧸 Мишек: {bears}\n\n"
        "Оплата заявлена.\n"
        "Прошу проверить оплату и подтвердить получение."
    )

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"confirm_{user.id}_{amount}"
            )
        ]
    ])

    await context.bot.send_message(
        ADMIN_ID,
        admin_text,
        reply_markup=keyboard
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ АДМИНОМ
# =========================================================

async def confirm_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ У вас нет доступа.",
            show_alert=True
        )

        return

    await query.answer()

    parts = query.data.split("_")

    user_id = int(parts[1])
    amount = int(parts[2])

    add_balance(
        user_id,
        amount
    )

    try:

        await context.bot.send_message(
            user_id,

            f"✅ Администратор проверил оплату.\n\n"
            f"Вам выдано {amount} Деф очков.\n\n"
            f"💰 Новый баланс: "
            f"{get_balance(user_id)} Деф"
        )

    except Exception:
        pass

    await query.message.edit_text(
        query.message.text
        + "\n\n"
        "✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )

    purchase_data.pop(
        user_id,
        None
    )


# =========================================================
# ПРОМОКОД - МЕНЮ
# =========================================================

async def promo_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data["waiting_promo"] = True

    await query.message.edit_text(
        "🫆 Промокод\n\n"
        "Введите промокод:",
        reply_markup=back_keyboard()
    )


# =========================================================
# ИСПОЛЬЗОВАНИЕ ПРОМО
# =========================================================

async def use_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "waiting_promo"
    ):
        return

    context.user_data[
        "waiting_promo"
    ] = False

    code = update.message.text.strip().upper()

    cursor.execute(
        """
        SELECT amount, uses_left
        FROM promos
        WHERE code=?
        """,
        (code,)
    )

    promo = cursor.fetchone()

    if not promo:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_keyboard()
        )

        return

    amount, uses_left = promo

    if uses_left <= 0:

        await update.message.reply_text(
            "❌ Этот промокод больше недоступен.",
            reply_markup=back_keyboard()
        )

        return

    add_balance(
        update.effective_user.id,
        amount
    )

    cursor.execute(
        """
        UPDATE promos
        SET uses_left = uses_left - 1
        WHERE code=?
        """,
        (code,)
    )

    db.commit()

    await update.message.reply_text(
        "🎉 Промокод успешно активирован!\n\n"
        f"💰 Вы получили: {amount} Деф очков.\n\n"
        f"Ваш баланс: "
        f"{get_balance(update.effective_user.id)} Деф",

        reply_markup=back_keyboard()
    )


# =========================================================
# ЗАКАЗАТЬ ДЕФ
# =========================================================

async def def_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "1 Деф - 1 Деф Очка",
                callback_data="order_def_1"
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


async def order_def(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Подтвердить заказ",
                callback_data="confirm_def_order"
            )
        ],

        [
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="def_order"
            )
        ]
    ])

    await query.message.edit_text(
        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "Подтвердить заказ?",

        reply_markup=keyboard
    )


async def confirm_def_order(
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

    await query.message.edit_text(
        "✅ Ваш заказ принят!\n\n"
        "Администратор скоро свяжется "
        "с вами в личных сообщениях."
    )

    await context.bot.send_message(

        ADMIN_ID,

        "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Прошу перейти к нему в личку.",

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
        "Нажми кнопку ниже, чтобы зайти "
        "в Telegram-канал.",

        reply_markup=keyboard
    )


# =========================================================
# ВОПРОС К CEKO
# =========================================================

async def question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data[
        "question_mode"
    ] = True

    await query.message.edit_text(

        "🔰 Вопрос к Ceko\n\n"
        "Напишите свой вопрос.\n\n"
        "Можно отправить текст, фото, видео, "
        "документ, голосовое или другое сообщение.\n\n"
        "Администратор ответит вам.",

        reply_markup=back_keyboard()
    )


# =========================================================
# ПОЛУЧЕНИЕ ВОПРОСА
# =========================================================

async def receive_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "question_mode"
    ):
        return

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else f"ID: {user.id}"
    )

    context.user_data[
        "question_mode"
    ] = False

    info = await context.bot.send_message(

        ADMIN_ID,

        "🔰 НОВЫЙ ВОПРОС\n\n"
        f"👤 От: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Чтобы ответить пользователю — "
        "ответьте реплаем на сообщение ниже."
    )

    question_messages[
        info.message_id
    ] = user.id

    try:

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_messages[
            copied.message_id
        ] = user.id

    except Exception as e:

        logging.error(
            f"Ошибка копирования сообщения: {e}"
        )

    await update.message.reply_text(

        "✅ Ваш вопрос отправлен администратору.",

        reply_markup=back_keyboard()
    )


# =========================================================
# ПАНЕЛЬ АДМИНА
# =========================================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Доступ запрещён."
        )

        return

    await update.message.reply_text(

        "🔐 Панель администратора",

        reply_markup=admin_keyboard()
    )


# =========================================================
# ДОБАВИТЬ ПРОМО
# =========================================================

async def admin_add_promo(
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

    context.user_data[
        "admin_state"
    ] = "promo_amount"

    await query.message.edit_text(

        "➕ Создание промокода\n\n"
        "Шаг 1/2\n\n"
        "Напишите, сколько Деф очков "
        "будет давать промокод."
    )


async def admin_promo_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get(
        "admin_state"
    ) != "promo_amount":
        return

    try:

        amount = int(
            update.message.text
        )

        if amount <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите положительное число."
        )

        return

    context.user_data[
        "promo_amount"
    ] = amount

    context.user_data[
        "admin_state"
    ] = "promo_uses"

    await update.message.reply_text(

        "Шаг 2/2\n\n"
        "Напишите, сколько раз можно "
        "использовать этот промокод."
    )


async def admin_promo_uses(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get(
        "admin_state"
    ) != "promo_uses":
        return

    try:

        uses = int(
            update.message.text
        )

        if uses <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите положительное число."
        )

        return

    amount = context.user_data[
        "promo_amount"
    ]

    context.user_data[
        "promo_uses"
    ] = uses

    context.user_data[
        "admin_state"
    ] = "promo_confirm"

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ Создать",
                callback_data="create_promo"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="admin_panel"
            )
        ]
    ])

    await update.message.reply_text(

        "📋 Проверьте данные:\n\n"
        f"💰 Деф очков: {amount}\n"
        f"👥 Использований: {uses}\n\n"
        "Создать промокод?",

        reply_markup=keyboard
    )


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
        "promo_amount"
    )

    uses = context.user_data.get(
        "promo_uses"
    )

    if not amount or not uses:

        await query.message.edit_text(
            "❌ Данные промокода потеряны."
        )

        return

    code = generate_promo()

    cursor.execute(

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

        "✅ Промокод создан!\n\n"
        f"🎟 Промокод: {code}\n"
        f"💰 Деф очков: {amount}\n"
        f"👥 Использований: {uses}",

        reply_markup=admin_keyboard()
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

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM promos"
    )

    promos = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM users"
    )

    total_balance = cursor.fetchone()[0]

    await query.message.edit_text(

        "📊 Статистика\n\n"
        f"👥 Пользователей: {users}\n"
        f"🎟 Промокодов: {promos}\n"
        f"💰 Деф на балансах: {total_balance}",

        reply_markup=admin_keyboard()
    )


# =========================================================
# ОТВЕТ АДМИНА
# =========================================================

async def admin_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_id = (
        update.message
        .reply_to_message
        .message_id
    )

    user_id = question_messages.get(
        replied_id
    )

    if not user_id:
        return

    try:

        await update.message.copy(
            chat_id=user_id
        )

        await update.message.reply_text(
            "✅ Ответ отправлен пользователю."
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Не удалось отправить ответ: {e}"
        )


# =========================================================
# НАЗАД
# =========================================================

async def back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    context.user_data.clear()

    await query.message.edit_text(

        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф",

        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# ОБРАБОТКА КНОПОК
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    data = query.data

    if data == "catalog":

        await catalog(
            update,
            context
        )

    elif data.startswith("buy_"):

        await select_product(
            update,
            context
        )

    elif data == "payment_done":

        await payment_done(
            update,
            context
        )

    elif data.startswith("confirm_"):

        await confirm_payment(
            update,
            context
        )

    elif data == "promo":

        await promo_menu(
            update,
            context
        )

    elif data == "def_order":

        await def_order(
            update,
            context
        )

    elif data == "order_def_1":

        await order_def(
            update,
            context
        )

    elif data == "confirm_def_order":

        await confirm_def_order(
            update,
            context
        )

    elif data == "channel":

        await channel(
            update,
            context
        )

    elif data == "question":

        await question(
            update,
            context
        )

    elif data == "back":

        await back(
            update,
            context
        )

    elif data == "balance":

        await query.answer(
            f"Ваш баланс: "
            f"{get_balance(query.from_user.id)} Деф",
            show_alert=True
        )

    elif data == "admin_add_promo":

        await admin_add_promo(
            update,
            context
        )

    elif data == "create_promo":

        await create_promo(
            update,
            context
        )

    elif data == "admin_stats":

        await admin_stats(
            update,
            context
        )

    elif data == "admin_panel":

        if query.from_user.id == ADMIN_ID:

            await query.message.edit_text(
                "🔐 Панель администратора",
                reply_markup=admin_keyboard()
            )

    elif data == "admin_back":

        await back(
            update,
            context
        )


# =========================================================
# ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # Пользователь вводит промокод
    if context.user_data.get(
        "waiting_promo"
    ):

        await use_promo(
            update,
            context
        )

        return

    # Админ создаёт промокод
    if user_id == ADMIN_ID:

        state = context.user_data.get(
            "admin_state"
        )

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

    # Вопрос пользователя
    if context.user_data.get(
        "question_mode"
    ):

        await receive_question(
            update,
            context
        )


# =========================================================
# MAIN
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

    # /panel
    app.add_handler(
        CommandHandler(
            "panel",
            admin_panel
        )
    )

    # Кнопки
    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    # Ответ администратора реплаем
    app.add_handler(
        MessageHandler(
            filters.REPLY & filters.ALL,
            admin_reply
        ),
        group=1
    )

    # Любые сообщения
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            text_handler
        ),
        group=2
    )

    print("================================")
    print("       CEKO HUB ЗАПУЩЕН")
    print("================================")

    app.run_polling()


# =========================================================
# ЗАПУСК
# =========================================================

if __name__ == "__main__":
    main()
