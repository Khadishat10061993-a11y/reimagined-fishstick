# bot.py
# Ceko Hub
# Python 3.10+
# pip install python-telegram-bot

import sqlite3
import random
import string
import re
import time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ChatPermissions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = "8905175157:AAEXGCH_Cx2On1uH0JMuBoEuxDB3I2F52N0"
ADMIN_ID = 8161017993

CHANNEL_LINK = "https://t.me/+lyHMe0599OtjYjEy"

DB = "ceko.db"

# ============================================================
# ПОДАРКИ-ДЕФ
# ============================================================

GIFTS = {
    "gift_1": {
        "name": "🎁 1 Деф",
        "def": 1,
        "stars": 1,
    },
    "gift_10": {
        "name": "🎁 10 Деф",
        "def": 10,
        "stars": 5,
    },
    "gift_25": {
        "name": "🎁 25 Деф",
        "def": 25,
        "stars": 10,
    },
    "gift_50": {
        "name": "🎁 50 Деф",
        "def": 50,
        "stars": 40,
    },
    "gift_100": {
        "name": "🎁 100 Деф",
        "def": 100,
        "stars": 75,
    },
}

# ============================================================
# СОСТОЯНИЯ
# ============================================================

states = {}
cooldowns = {}
broken_bases = set()

# ============================================================
# DATABASE
# ============================================================


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()

    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0,
        pension REAL DEFAULT 0.1,
        started INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER,
        receiver_id INTEGER,
        receiver_username TEXT,
        item TEXT,
        def_amount INTEGER,
        stars INTEGER,
        status TEXT,
        payload TEXT,
        charge_id TEXT,
        created INTEGER
    );

    CREATE TABLE IF NOT EXISTS promos (
        code TEXT PRIMARY KEY,
        reward INTEGER,
        uses_left INTEGER,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS gift_promos (
        code TEXT PRIMARY KEY,
        gift_key TEXT,
        uses_left INTEGER,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    if not con.execute(
        "SELECT 1 FROM settings WHERE key='rules'"
    ).fetchone():

        con.execute(
            "INSERT INTO settings(key,value) VALUES(?,?)",
            (
                "rules",
                """📜 Правила Ceko

• Не пиарить чаты или каналы.
• Не оскать родню.
• Не писать «докс», «сват» и подобное.
• Не отправлять рекламу.
• Не нарушать правила чата.""",
            ),
        )

    con.commit()
    con.close()


init_db()

# ============================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================


def register(user):
    con = db()

    con.execute(
        """
        INSERT INTO users
        (user_id,username,first_name,balance,pension,started)
        VALUES (?,?,?,?,?,1)
        ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        started=1
        """,
        (
            user.id,
            user.username or "",
            user.first_name or "",
            0,
            0.1,
        ),
    )

    con.commit()
    con.close()


def get_balance(user_id):
    con = db()

    row = con.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()

    con.close()

    return row["balance"] if row else 0


def add_def(user_id, amount):
    con = db()

    con.execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE user_id=?
        """,
        (amount, user_id),
    )

    con.commit()
    con.close()


def remove_def(user_id, amount):
    con = db()

    row = con.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()

    if not row or row["balance"] < amount:
        con.close()
        return False

    con.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE user_id=?
        """,
        (amount, user_id),
    )

    con.commit()
    con.close()

    return True


def find_user_by_username(username):
    username = username.lower().replace("@", "")

    con = db()

    row = con.execute(
        """
        SELECT *
        FROM users
        WHERE lower(username)=?
        """,
        (username,),
    ).fetchone()

    con.close()

    return row


def display_name(user):
    if user.username:
        return f"@{user.username}"

    return user.first_name or str(user.id)


# ============================================================
# КЛАВИАТУРЫ
# ============================================================


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🫀 Каталог",
                callback_data="catalog"
            )
        ],
        [
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
                "🎁 Подарок",
                callback_data="gift"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Секрет ТГК",
                url=CHANNEL_LINK
            )
        ],
        [
            InlineKeyboardButton(
                "🔰 Вопрос к Ceko",
                callback_data="question"
            )
        ],
    ])


def back():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "↩️ Назад",
                callback_data="main"
            )
        ]
    ])


# ============================================================
# START
# ============================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    register(user)

    await update.message.reply_text(
        "🔰 Ceko Hub Приветствует\n\n"
        "Для того чтобы продолжить нажмите на кнопки.\n\n"
        f"Баланс: {get_balance(user.id)} Деф",
        reply_markup=main_menu()
    )


# ============================================================
# КАТАЛОГ
# ============================================================


async def catalog(update, context):

    q = update.callback_query
    await q.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "1 Деф — 1 ⭐",
                callback_data="catalog_1"
            )
        ],
        [
            InlineKeyboardButton(
                "10 Деф — 5 ⭐",
                callback_data="catalog_10"
            )
        ],
        [
            InlineKeyboardButton(
                "25 Деф — 10 ⭐",
                callback_data="catalog_25"
            )
        ],
        [
            InlineKeyboardButton(
                "50 Деф — 40 ⭐",
                callback_data="catalog_50"
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ Назад",
                callback_data="main"
            )
        ],
    ]

    await q.edit_message_text(
        "🤖 Каталог валюты\n\n"
        "Действуют скидки — навсегда.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# ПОКУПКА ДЕФ
# ============================================================


async def catalog_product(update, context):

    q = update.callback_query
    await q.answer()

    amount = int(q.data.split("_")[1])

    prices = {
        1: 1,
        10: 5,
        25: 10,
        50: 40,
    }

    stars = prices[amount]

    payload = f"self:{amount}:{q.from_user.id}:{int(time.time())}"

    await context.bot.send_invoice(
        chat_id=q.from_user.id,
        title=f"{amount} Деф",
        description=f"Пополнение баланса на {amount} Деф",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                f"{amount} Деф",
                stars
            )
        ],
        start_parameter="ceko-def"
    )


# ============================================================
# ПОДАРОК
# ============================================================


async def gift_menu(update, context):

    q = update.callback_query
    await q.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "👤 Подарить себе",
                callback_data="gift_self"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Подарить другу",
                callback_data="gift_friend"
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ Назад",
                callback_data="main"
            )
        ],
    ]

    await q.edit_message_text(
        "🎁 Подарок\n\n"
        "Выберите, кому подарить Деф:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def gift_self(update, context):

    q = update.callback_query
    await q.answer()

    keyboard = []

    for key, item in GIFTS.items():

        keyboard.append([
            InlineKeyboardButton(
                f"{item['name']} — {item['stars']} ⭐",
                callback_data=f"giftself:{key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "↩️ Назад",
            callback_data="gift"
        )
    ])

    await q.edit_message_text(
        "🎁 Выберите подарок:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def gift_friend(update, context):

    q = update.callback_query
    await q.answer()

    states[q.from_user.id] = "gift_friend_username"

    await q.edit_message_text(
        "👥 Введите username друга.\n\n"
        "Например:\n"
        "@username\n\n"
        "Друг должен хотя бы один раз "
        "запустить этого бота."
    )


async def gift_self_selected(update, context):

    q = update.callback_query
    await q.answer()

    key = q.data.split(":", 1)[1]

    item = GIFTS[key]

    payload = (
        f"giftself:"
        f"{key}:"
        f"{q.from_user.id}:"
        f"{int(time.time())}"
    )

    await context.bot.send_invoice(
        chat_id=q.from_user.id,
        title=item["name"],
        description=(
            f"Подарок: {item['def']} Деф "
            f"на собственный баланс"
        ),
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                item["name"],
                item["stars"]
            )
        ],
        start_parameter="ceko-gift-self"
    )


# ============================================================
# ПОДАРОК ДРУГУ — ВВОД USERNAME
# ============================================================


async def process_friend_username(update, context):

    user = update.effective_user

    if states.get(user.id) != "gift_friend_username":
        return False

    text = update.message.text.strip()

    if not re.fullmatch(
        r"@?[A-Za-z0-9_]{5,32}",
        text
    ):
        await update.message.reply_text(
            "❌ Неверный username.\n\n"
            "Пример: @username"
        )
        return True

    username = text.replace("@", "").lower()

    receiver = find_user_by_username(username)

    if not receiver:

        await update.message.reply_text(
            "❌ Этот пользователь ещё не запускал бота.\n\n"
            "Попросите его открыть бота и нажать /start."
        )

        return True

    states.pop(user.id, None)

    context.user_data["gift_receiver_id"] = receiver["user_id"]
    context.user_data["gift_receiver_username"] = username

    keyboard = []

    for key, item in GIFTS.items():

        keyboard.append([
            InlineKeyboardButton(
                f"{item['name']} — {item['stars']} ⭐",
                callback_data=f"giftfriend:{key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "↩️ Назад",
            callback_data="gift"
        )
    ])

    await update.message.reply_text(
        f"👤 Получатель: @{username}\n\n"
        "🎁 Выберите подарок:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return True


async def gift_friend_selected(update, context):

    q = update.callback_query
    await q.answer()

    key = q.data.split(":", 1)[1]

    receiver_id = context.user_data.get(
        "gift_receiver_id"
    )

    receiver_username = context.user_data.get(
        "gift_receiver_username"
    )

    if not receiver_id:

        await q.edit_message_text(
            "❌ Получатель не выбран."
        )

        return

    item = GIFTS[key]

    payload = (
        f"giftfriend:"
        f"{key}:"
        f"{q.from_user.id}:"
        f"{receiver_id}:"
        f"{int(time.time())}"
    )

    await context.bot.send_invoice(
        chat_id=q.from_user.id,
        title=item["name"],
        description=(
            f"Подарок @{receiver_username}: "
            f"{item['def']} Деф"
        ),
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                item["name"],
                item["stars"]
            )
        ],
        start_parameter="ceko-gift-friend"
    )


# ============================================================
# ПЛАТЕЖИ
# ============================================================


async def pre_checkout(update, context):

    query = update.pre_checkout_query

    payload = query.invoice_payload

    if not payload:
        await query.answer(
            ok=False,
            error_message="Ошибка заказа."
        )
        return

    await query.answer(ok=True)


async def successful_payment(update, context):

    payment = update.message.successful_payment

    payload = payment.invoice_payload

    parts = payload.split(":")

    # --------------------------------------------------------
    # ПОКУПКА СЕБЕ
    # --------------------------------------------------------

    if parts[0] == "self":

        amount = int(parts[1])
        buyer_id = int(parts[2])

        if buyer_id != update.effective_user.id:
            return

        add_def(
            buyer_id,
            amount
        )

        await update.message.reply_text(
            "✅ Оплата успешно получена!\n\n"
            f"🎁 Вам начислено {amount} Деф\n"
            f"💰 Баланс: {get_balance(buyer_id)} Деф",
            reply_markup=main_menu()
        )

        save_order(
            buyer_id=buyer_id,
            receiver_id=buyer_id,
            receiver_username=(
                update.effective_user.username or ""
            ),
            item=f"{amount} Деф",
            def_amount=amount,
            stars=payment.total_amount,
            status="paid",
            payload=payload,
            charge_id=(
                payment.telegram_payment_charge_id
            )
        )

        return

    # --------------------------------------------------------
    # ПОДАРОК СЕБЕ
    # --------------------------------------------------------

    if parts[0] == "giftself":

        key = parts[1]
        buyer_id = int(parts[2])

        if buyer_id != update.effective_user.id:
            return

        item = GIFTS[key]

        add_def(
            buyer_id,
            item["def"]
        )

        save_order(
            buyer_id=buyer_id,
            receiver_id=buyer_id,
            receiver_username=(
                update.effective_user.username or ""
            ),
            item=item["name"],
            def_amount=item["def"],
            stars=payment.total_amount,
            status="paid",
            payload=payload,
            charge_id=(
                payment.telegram_payment_charge_id
            )
        )

        await update.message.reply_text(
            "🎁 Подарок получен!\n\n"
            f"{item['name']}\n"
            f"+{item['def']} Деф\n\n"
            f"💰 Баланс: {get_balance(buyer_id)} Деф",
            reply_markup=main_menu()
        )

        return

    # --------------------------------------------------------
    # ПОДАРОК ДРУГУ
    # --------------------------------------------------------

    if parts[0] == "giftfriend":

        key = parts[1]
        buyer_id = int(parts[2])
        receiver_id = int(parts[3])

        if buyer_id != update.effective_user.id:
            return

        item = GIFTS[key]

        # Начисляем Деф получателю
        add_def(
            receiver_id,
            item["def"]
        )

        receiver = db().execute(
            "SELECT username FROM users WHERE user_id=?",
            (receiver_id,)
        ).fetchone()

        receiver_username = (
            receiver["username"]
            if receiver else ""
        )

        save_order(
            buyer_id=buyer_id,
            receiver_id=receiver_id,
            receiver_username=receiver_username,
            item=item["name"],
            def_amount=item["def"],
            stars=payment.total_amount,
            status="paid",
            payload=payload,
            charge_id=(
                payment.telegram_payment_charge_id
            )
        )

        await update.message.reply_text(
            "✅ Подарок успешно отправлен!\n\n"
            f"🎁 {item['name']}\n"
            f"👤 Получатель: "
            f"@{receiver_username or receiver_id}\n"
            f"💎 {item['def']} Деф",
            reply_markup=main_menu()
        )

        try:

            await context.bot.send_message(
                receiver_id,
                "🎁 Вам пришёл подарок!\n\n"
                f"{item['name']}\n"
                f"+{item['def']} Деф\n\n"
                f"💰 Ваш баланс: "
                f"{get_balance(receiver_id)} Деф"
            )

        except Exception as e:

            print(
                "Не удалось отправить уведомление:",
                e
            )

        return


def save_order(
    buyer_id,
    receiver_id,
    receiver_username,
    item,
    def_amount,
    stars,
    status,
    payload,
    charge_id
):

    con = db()

    con.execute(
        """
        INSERT INTO orders(
            buyer_id,
            receiver_id,
            receiver_username,
            item,
            def_amount,
            stars,
            status,
            payload,
            charge_id,
            created
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            buyer_id,
            receiver_id,
            receiver_username,
            item,
            def_amount,
            stars,
            status,
            payload,
            charge_id,
            int(time.time())
        )
    )

    con.commit()
    con.close()


# ============================================================
# ПРОМОКОД
# ============================================================


async def promo(update, context):

    q = update.callback_query
    await q.answer()

    states[q.from_user.id] = "promo"

    await q.edit_message_text(
        "🫆 Введите промокод:",
        reply_markup=back()
    )


async def process_promo(update, context):

    user = update.effective_user

    code = update.message.text.strip().upper()

    con = db()

    row = con.execute(
        """
        SELECT *
        FROM promos
        WHERE code=?
        AND active=1
        AND uses_left>0
        """,
        (code,)
    ).fetchone()

    if not row:

        con.close()

        await update.message.reply_text(
            "❌ Промокод недоступен."
        )

        return True

    add_def(
        user.id,
        row["reward"]
    )

    con.execute(
        """
        UPDATE promos
        SET uses_left=uses_left-1
        WHERE code=?
        """,
        (code,)
    )

    con.execute(
        """
        UPDATE promos
        SET active=0
        WHERE code=?
        AND uses_left<=0
        """,
        (code,)
    )

    con.commit()
    con.close()

    states.pop(user.id, None)

    await update.message.reply_text(
        "✅ Промокод активирован!\n\n"
        f"🎁 +{row['reward']} Деф\n"
        f"💰 Баланс: {get_balance(user.id)} Деф",
        reply_markup=main_menu()
    )

    return True


# ============================================================
# ВОПРОС
# ============================================================


async def question(update, context):

    q = update.callback_query
    await q.answer()

    states[q.from_user.id] = "question"

    await q.edit_message_text(
        "🔰 Напишите свой вопрос Ceko.\n\n"
        "Можно отправить текст."
    )


async def process_question(update, context):

    user = update.effective_user

    await context.bot.send_message(
        ADMIN_ID,
        "🔰 Новый вопрос\n\n"
        f"👤 {display_name(user)}\n"
        f"🆔 {user.id}\n\n"
        f"{update.message.text}"
    )

    states.pop(user.id, None)

    await update.message.reply_text(
        "✅ Вопрос отправлен администратору.",
        reply_markup=main_menu()
    )

    return True


# ============================================================
# ЗАКАЗ ДЕФ
# ============================================================


async def def_order(update, context):

    q = update.callback_query
    await q.answer()

    await q.edit_message_text(
        "👾 Выбирай пункт:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "1 Деф — 1 Деф очка",
                    callback_data="def_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ Назад",
                    callback_data="main"
                )
            ]
        ])
    )


async def def_confirm(update, context):

    q = update.callback_query
    await q.answer()

    if get_balance(q.from_user.id) < 1:

        await q.edit_message_text(
            "❌ Недостаточно Деф.",
            reply_markup=back()
        )

        return

    await q.edit_message_text(
        "Подтвердить заказ?\n\n"
        "Стоимость: 1 Деф",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data="def_yes"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="main"
                )
            ]
        ])
    )


async def def_yes(update, context):

    q = update.callback_query
    await q.answer()

    if not remove_def(q.from_user.id, 1):

        await q.edit_message_text(
            "❌ Недостаточно Деф."
        )

        return

    await q.edit_message_text(
        "✅ Ваш запрос принят и обрабатывается.\n\n"
        "Подождите несколько минут."
    )

    await context.bot.send_message(
        ADMIN_ID,
        "👾 Новая заявка\n\n"
        f"👤 {display_name(q.from_user)}\n"
        f"🆔 {q.from_user.id}\n"
        "📦 Заказ: 1 Деф\n"
        "💸 Списано: 1 Деф"
    )


# ============================================================
# ПРАВИЛА
# ============================================================


async def rules(update, context):

    con = db()

    row = con.execute(
        "SELECT value FROM settings WHERE key='rules'"
    ).fetchone()

    con.close()

    await update.message.reply_text(
        row["value"]
        if row
        else "Правила не установлены."
    )


# ============================================================
# ИГРОВАЯ КОМАНДА
# ============================================================


async def pension(update, context):

    user = update.effective_user

    now = time.time()

    last = cooldowns.get(user.id, 0)

    if now - last < 120:

        remaining = int(
            120 - (now - last)
        )

        await update.message.reply_text(
            f"⏳ Подожди {remaining} сек."
        )

        return

    cooldowns[user.id] = now

    con = db()

    row = con.execute(
        "SELECT pension FROM users WHERE user_id=?",
        (user.id,)
    ).fetchone()

    value = float(
        row["pension"]
        if row
        else 0.1
    )

    value = round(
        value + 0.1,
        1
    )

    con.execute(
        """
        UPDATE users
        SET pension=?
        WHERE user_id=?
        """,
        (value, user.id)
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        f"{display_name(user)} "
        "понизил пенсию бабушкам\n\n"
        f"Понижено {value}%"
    )

    if random.random() < 0.15:

        broken_bases.add(user.id)

        await update.message.reply_text(
            "💥 Бабки сломали вашу базу "
            "понижения пенсии!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔨 Восстановить",
                        callback_data=f"restore:{user.id}"
                    )
                ]
            ])
        )


async def restore(update, context):

    q = update.callback_query

    await q.answer()

    user_id = int(
        q.data.split(":")[1]
    )

    if q.from_user.id != user_id:

        await q.answer(
            "Это не ваша база.",
            show_alert=True
        )

        return

    broken_bases.discard(user_id)

    await q.edit_message_text(
        "✅ Вы восстановили свою базу!"
    )


async def top(update, context):

    con = db()

    rows = con.execute(
        """
        SELECT username,pension
        FROM users
        ORDER BY pension DESC
        LIMIT 10
        """
    ).fetchall()

    con.close()

    text = "🏆 ТОП\n\n"

    for i, row in enumerate(rows, 1):

        name = row["username"] or "unknown"

        text += (
            f"{i}. @{name} — "
            f"{row['pension']}%\n"
        )

    await update.message.reply_text(
        text
    )


# ============================================================
# АДМИН
# ============================================================


def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Создать промо Деф",
                callback_data="admin_promo"
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
                "↩️ Главное меню",
                callback_data="main"
            )
        ]
    ])


async def admin(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Нет доступа."
        )

        return

    await update.message.reply_text(
        "🔐 Панель администратора",
        reply_markup=admin_keyboard()
    )


async def admin_promo(update, context):

    q = update.callback_query

    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    states[q.from_user.id] = "admin_reward"

    await q.edit_message_text(
        "Введите сколько Деф будет давать промокод:"
    )


async def admin_text(update, context):

    user = update.effective_user

    if user.id != ADMIN_ID:
        return False

    state = states.get(user.id)

    if state == "admin_reward":

        try:
            reward = int(
                update.message.text
            )
        except:
            await update.message.reply_text(
                "Введите число."
            )
            return True

        context.user_data["promo_reward"] = reward

        states[user.id] = "admin_uses"

        await update.message.reply_text(
            "Теперь введите количество активаций:"
        )

        return True

    if state == "admin_uses":

        try:
            uses = int(
                update.message.text
            )
        except:
            await update.message.reply_text(
                "Введите число."
            )
            return True

        reward = context.user_data.pop(
            "promo_reward"
        )

        code = "".join(
            random.choice(
                string.ascii_uppercase
                + string.digits
            )
            for _ in range(10)
        )

        con = db()

        con.execute(
            """
            INSERT INTO promos
            (code,reward,uses_left,active)
            VALUES(?,?,?,1)
            """,
            (
                code,
                reward,
                uses
            )
        )

        con.commit()
        con.close()

        states.pop(user.id, None)

        await update.message.reply_text(
            "✅ Промокод создан!\n\n"
            f"🎟 {code}\n"
            f"🎁 {reward} Деф\n"
            f"🔢 Активаций: {uses}"
        )

        return True

    return False


# ============================================================
# КНОПКА НАЗАД
# ============================================================


async def main_callback(update, context):

    q = update.callback_query

    await q.answer()

    states.pop(
        q.from_user.id,
        None
    )

    await q.edit_message_text(
        "🔰 Ceko Hub\n\n"
        f"Баланс: {get_balance(q.from_user.id)} Деф",
        reply_markup=main_menu()
    )


# ============================================================
# ТЕКСТ
# ============================================================


async def text_handler(update, context):

    user = update.effective_user

    register(user)

    # Админские состояния
    if user.id == ADMIN_ID:

        if await admin_text(
            update,
            context
        ):
            return

    # Подарок другу
    if states.get(user.id) == "gift_friend_username":

        if await process_friend_username(
            update,
            context
        ):
            return

    # Промокод
    if states.get(user.id) == "promo":

        if await process_promo(
            update,
            context
        ):
            return

    # Вопрос
    if states.get(user.id) == "question":

        if await process_question(
            update,
            context
        ):
            return

    text = (
        update.message.text
        or ""
    ).strip()

    low = text.lower()

    # Только точное слово "бот"
    if low == "бот":

        await update.message.reply_text(
            "Ceko на месте✅"
        )

        return

    if low == "правила":

        con = db()

        row = con.execute(
            "SELECT value FROM settings WHERE key='rules'"
        ).fetchone()

        con.close()

        await update.message.reply_text(
            row["value"]
            if row
            else "Правила не установлены."
        )

        return

    if low in (
        "понизить пенсию бабушкам",
        "ппб"
    ):

        await pension(
            update,
            context
        )

        return

    if low == "топ":

        await top(
            update,
            context
        )

        return


# ============================================================
# НОВЫЙ УЧАСТНИК
# ============================================================


async def welcome(update, context):

    for member in update.message.new_chat_members:

        name = (
            f"@{member.username}"
            if member.username
            else member.first_name
        )

        await update.message.reply_text(
            f"{name} приветствую тебя "
            "в наш чат Ceko\n\n"
            "Чтобы посмотреть правила "
            "напиши правила"
        )


# ============================================================
# ССЫЛКИ В ЧАТЕ
# ============================================================


async def link_moderation(update, context):

    message = update.message

    if not message:
        return

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    text = (
        message.text
        or message.caption
        or ""
    )

    if not re.search(
        r"(https?://|t\.me/|www\.)",
        text,
        re.I
    ):
        return

    try:

        await message.delete()

        until = int(
            time.time() + 3600
        )

        await context.bot.restrict_chat_member(
            message.chat.id,
            message.from_user.id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            until_date=until
        )

        await context.bot.send_message(
            message.chat.id,
            f"{display_name(message.from_user)} "
            "был замучен на 1 час\n\n"
            "Причина:реклама"
        )

    except Exception as e:

        print(
            "Ошибка модерации:",
            e
        )


# ============================================================
# ЗАПУСК
# ============================================================


def main():

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Команды
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top
        )
    )

    app.add_handler(
        CommandHandler(
            "rules",
            rules
        )
    )

    # Оплата
    app.add_handler(
        PreCheckoutQueryHandler(
            pre_checkout
        )
    )

    app.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment
        )
    )

    # Кнопки
    app.add_handler(
        CallbackQueryHandler(
            catalog,
            pattern="^catalog$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            catalog_product,
            pattern="^catalog_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            gift_menu,
            pattern="^gift$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            gift_self,
            pattern="^gift_self$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            gift_friend,
            pattern="^gift_friend$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            gift_self_selected,
            pattern="^giftself:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            gift_friend_selected,
            pattern="^giftfriend:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            promo,
            pattern="^promo$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            def_order,
            pattern="^def_order$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            def_confirm,
            pattern="^def_confirm$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            def_yes,
            pattern="^def_yes$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            question,
            pattern="^question$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            restore,
            pattern="^restore:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_promo,
            pattern="^admin_promo$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            main_callback,
            pattern="^main$"
        )
    )

    # Новые участники
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome
        )
    )

    # Модерация ссылок
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & (
                filters.TEXT
                | filters.CAPTION
            ),
            link_moderation
        ),
        group=0
    )

    # Обычный текст
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        ),
        group=1
    )

    print("Ceko Hub запущен.")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
