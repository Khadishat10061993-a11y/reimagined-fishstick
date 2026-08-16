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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# DATABASE
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
    amount INTEGER NOT NULL,
    uses_left INTEGER NOT NULL
)
""")

db.commit()


# =========================================================
# USERS
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
        SET username = ?
        WHERE user_id = ?
        """,
        (
            user.username or "без_username",
            user.id
        )
    )

    db.commit()


def get_balance(user_id):

    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?",
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
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    db.commit()


# =========================================================
# PROMO
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
            "SELECT code FROM promos WHERE code = ?",
            (code,)
        )

        if cursor.fetchone() is None:
            return code


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

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
                f"💰 Баланс: {get_balance(user_id)} Деф",
                callback_data="balance"
            )
        ]
    ]

    # Панель показывается ТОЛЬКО админу
    if user_id == ADMIN_ID:

        buttons.append([
            InlineKeyboardButton(
                "🔐 Панель администратора",
                callback_data="admin_panel"
            )
        ])

    return InlineKeyboardMarkup(buttons)


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
                "➕ Создать промокод",
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
                "◀️ Главное меню",
                callback_data="back"
            )
        ]
    ])


# =========================================================
# БЕЗОПАСНОЕ ОТКРЫТИЕ ЭКРАНА
# =========================================================

async def show_screen(
    query,
    text,
    keyboard=None
):
    """
    Универсальная функция.

    Если старое сообщение содержит фото,
    его нельзя нормально заменить edit_text.

    Поэтому сначала пробуем удалить старое сообщение,
    а потом отправляем обычный текст.
    """

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        text=text,
        reply_markup=keyboard
    )


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
# НАЗАД
# =========================================================

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    context.user_data.clear()

    try:
        await query.message.delete()
    except Exception:
        pass

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    try:

        with open(START_PHOTO, "rb") as photo:

            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id)
            )

    except FileNotFoundError:

        await query.message.chat.send_message(
            text=text,
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
            "❌ Не найден файл Katalog.jpg.PNG\n\n"
            + text,
            reply_markup=keyboard
        )


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
        query.data.replace("buy_", "")
    )

    prices = {
        1: 1,
        10: 5,
        25: 10,
        50: 40
    }

    bears = prices[amount]

    context.user_data["purchase"] = {
        "def": amount,
        "bears": bears
    }

    text = (
        f"Вы выбрали {amount} Деф очков.\n\n"
        f"Для того чтобы получить их, перейдите в ЛС "
        f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
        "После оплаты нажмите кнопку ниже."
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
                callback_data="catalog"
            )
        ]
    ])

    await show_screen(
        query,
        text,
        keyboard
    )


# =========================================================
# ГОТОВО
# =========================================================

async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    data = context.user_data.get(
        "purchase"
    )

    if not data:

        await show_screen(
            query,
            "❌ Заявка не найдена.",
            back_keyboard()
        )

        return

    amount = data["def"]
    bears = data["bears"]

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    await show_screen(
        query,
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
                callback_data=f"payment_confirm_{user.id}_{amount}"
            )
        ]
    ])

    await context.bot.send_message(
        ADMIN_ID,
        admin_text,
        reply_markup=keyboard
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
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

    parts = query.data.split("_")

    user_id = int(parts[2])
    amount = int(parts[3])

    add_balance(
        user_id,
        amount
    )

    try:

        await context.bot.send_message(
            user_id,

            "✅ Администратор проверил оплату.\n\n"
            f"Вам выдано {amount} Деф очков.\n\n"
            f"💰 Новый баланс: "
            f"{get_balance(user_id)} Деф"
        )

    except Exception as e:

        logging.error(e)

    await query.message.edit_text(
        query.message.text
        + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
    )


# =========================================================
# ПРОМОКОД
# =========================================================

async def promo_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data[
        "waiting_promo"
    ] = True

    await show_screen(
        query,

        "🫆 Промокод\n\n"
        "Введите промокод:",

        back_keyboard()
    )


async def use_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "waiting_promo"
    ):
        return False

    code = update.message.text.strip().upper()

    cursor.execute(
        """
        SELECT amount, uses_left
        FROM promos
        WHERE code = ?
        """,
        (code,)
    )

    promo = cursor.fetchone()

    if not promo:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_keyboard()
        )

        return True

    amount, uses_left = promo

    if uses_left <= 0:

        await update.message.reply_text(
            "❌ Этот промокод больше недоступен.",
            reply_markup=back_keyboard()
        )

        return True

    add_balance(
        update.effective_user.id,
        amount
    )

    cursor.execute(
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

        "🎉 Промокод успешно активирован!\n\n"
        f"💰 Вы получили: {amount} Деф очков.\n\n"
        f"Баланс: {get_balance(update.effective_user.id)} Деф",

        reply_markup=back_keyboard()
    )

    return True


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

    await show_screen(
        query,

        "👾 Заказать Деф\n\n"
        "Выбирай пункт:",

        keyboard
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

    await show_screen(
        query,

        "👾 Вы выбрали:\n\n"
        "1 Деф - 1 Деф Очка\n\n"
        "Подтвердить заказ?",

        keyboard
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

    await show_screen(
        query,

        "✅ Ваш заказ принят!\n\n"
        "Администратор скоро свяжется с вами."
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

    await show_screen(
        query,

        "💬 Секрет Тгк\n\n"
        "Нажми кнопку ниже, чтобы зайти "
        "в Telegram-канал.",

        keyboard
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

    context.user_data.clear()

    context.user_data[
        "question_mode"
    ] = True

    await show_screen(
        query,

        "🔰 Вопрос к Ceko\n\n"
        "Напишите свой вопрос.\n\n"
        "Можно отправить текст, фото, видео, "
        "документ, голосовое или другое сообщение.\n\n"
        "Администратор ответит вам.",

        back_keyboard()
    )


# =========================================================
# ПОЛУЧЕНИЕ ВОПРОСА
# =========================================================

question_messages = {}


async def receive_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "question_mode"
    ):
        return False

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else f"ID: {user.id}"
    )

    # Сначала отправляем админу информацию
    info = await context.bot.send_message(

        ADMIN_ID,

        "🔰 НОВЫЙ ВОПРОС\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Ответьте реплаем на сообщение ниже."
    )

    question_messages[
        info.message_id
    ] = user.id

    # Копируем настоящее сообщение
    try:

        copied = await update.message.copy(
            chat_id=ADMIN_ID
        )

        question_messages[
            copied.message_id
        ] = user.id

    except Exception as e:

        logging.error(
            f"Ошибка отправки вопроса: {e}"
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Ваш вопрос отправлен администратору.",
        reply_markup=back_keyboard()
    )

    return True


# =========================================================
# ПАНЕЛЬ АДМИНА
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

    await show_screen(
        query,

        "🔐 Панель администратора\n\n"
        "Выберите действие:",

        admin_keyboard()
    )


# =========================================================
# СОЗДАНИЕ ПРОМО
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

    context.user_data.clear()

    context.user_data[
        "admin_state"
    ] = "promo_amount"

    await show_screen(
        query,

        "➕ Создание промокода\n\n"
        "Шаг 1/2\n\n"
        "Напишите, сколько Деф очков "
        "будет давать промокод.",

        back_keyboard()
    )


async def admin_promo_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "admin_state"
    ) != "promo_amount":
        return False

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

        return True

    context.user_data[
        "promo_amount"
    ] = amount

    context.user_data[
        "admin_state"
    ] = "promo_uses"

    await update.message.reply_text(
        "Шаг 2/2\n\n"
        "Напишите, сколько раз "
        "можно использовать этот промокод."
    )

    return True


async def admin_promo_uses(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if context.user_data.get(
        "admin_state"
    ) != "promo_uses":
        return False

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

        return True

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

    return True


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

        await show_screen(
            query,
            "❌ Данные промокода потеряны.",
            admin_keyboard()
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

    await show_screen(

        query,

        "✅ Промокод создан!\n\n"
        f"🎟 Промокод: {code}\n"
        f"💰 Деф очков: {amount}\n"
        f"👥 Использований: {uses}",

        admin_keyboard()
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

    await show_screen(

        query,

        "📊 Статистика\n\n"
        f"👥 Пользователей: {users}\n"
        f"🎟 Промокодов: {promos}\n"
        f"💰 Деф на балансах: {total_balance}",

        admin_keyboard()
    )


# =========================================================
# ОТВЕТ АДМИНА НА ВОПРОС
# =========================================================

async def admin_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not update.message.reply_to_message:
        return False

    replied_id = (
        update.message
        .reply_to_message
        .message_id
    )

    user_id = question_messages.get(
        replied_id
    )

    if not user_id:
        return False

    try:

        await update.message.copy(
            chat_id=user_id
        )

        await update.message.reply_text(
            "✅ Ответ отправлен пользователю."
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Ошибка отправки: {e}"
        )

    return True


# =========================================================
# ОБРАБОТКА СООБЩЕНИЙ
# =========================================================

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # Ответ администратора
    if (
        user_id == ADMIN_ID
        and update.message.reply_to_message
    ):

        handled = await admin_reply(
            update,
            context
        )

        if handled:
            return

    # Промокод
    if (
        context.user_data.get("waiting_promo")
        and update.message.text
    ):

        await use_promo(
            update,
            context
        )

        return

    # Создание промокода админом
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

        return


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    data = query.data

    logging.info(
        f"CALLBACK: {data} | USER: {query.from_user.id}"
    )

    # Главное
    if data == "back":

        await back(
            update,
            context
        )

    # Каталог
    elif data == "catalog":

        await catalog(
            update,
            context
        )

    # Покупка
    elif data.startswith("buy_"):

        await select_product(
            update,
            context
        )

    # Готово
    elif data == "payment_done":

        await payment_done(
            update,
            context
        )

    # Подтверждение оплаты
    elif data.startswith("payment_confirm_"):

        await confirm_payment(
            update,
            context
        )

    # Промокод
    elif data == "promo":

        await promo_menu(
            update,
            context
        )

    # Заказать Деф
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

    # Канал
    elif data == "channel":

        await channel(
            update,
            context
        )

    # Вопрос
    elif data == "question":

        await question(
            update,
            context
        )

    # Баланс
    elif data == "balance":

        await query.answer(
            f"💰 Ваш баланс: "
            f"{get_balance(query.from_user.id)} Деф",
            show_alert=True
        )

    # Админ-панель
    elif data == "admin_panel":

        await admin_panel(
            update,
            context
        )

    # Добавить промо
    elif data == "admin_add_promo":

        await admin_add_promo(
            update,
            context
        )

    # Создать промо
    elif data == "create_promo":

        await create_promo(
            update,
            context
        )

    # Статистика
    elif data == "admin_stats":

        await admin_stats(
            update,
            context
        )

    else:

        await query.answer(
            "❌ Неизвестная кнопка.",
            show_alert=True
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

    # Все inline-кнопки
    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # Сообщения
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_handler
        )
    )

    print("")
    print("======================================")
    print("        CEKO HUB BOT ЗАПУЩЕН")
    print("======================================")
    print(f"ADMIN ID: {ADMIN_ID}")
    print("======================================")
    print("")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
