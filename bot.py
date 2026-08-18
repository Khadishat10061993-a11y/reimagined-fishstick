import os
import re
import random
import string
import sqlite3
import time
import logging
import asyncio

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
    filters,
    ContextTypes,
)

# ============================================================
# CEKO HUB — FULL BOT
# ============================================================

TOKEN = "8905175157:AAEXGCH_Cx2On1uH0JMuBoEuxDB3I2F52N0"

# Список администраторов
ADMIN_IDS = [8161017993, 8961670797]  # Главный админ и второй админ
ADMIN_ID = ADMIN_IDS[0]  # Главный админ для уведомлений

ADMIN_USERNAME = "@netuzu"
CHANNEL_URL = "https://t.me/+lyHMe0599OtjYjEy"

START_PHOTO = "Start.jpg.PNG"
CATALOG_PHOTO = "Katalog.jpg.PNG"
JERRY_VIDEO = "Jerry.MOV"
USER_SEARCH_PHOTO = "Pro.jpg.PNG"

DB_FILE = "ceko.db"

PENSION_COOLDOWN = 120

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("CEKO")

# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
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

db.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

db.commit()

DEFAULT_RULES = """📜 ПРАВИЛА ЧАТА CEKO

1. Не пиарить чаты или каналы.
2. Не оскать родню.
3. Не писать «ыыы», «докс», «сват» и подобное.
4. Не нарушать спокойствие участников чата.
5. Уважайте других участников чата."""

db.execute(
    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
    ("rules", DEFAULT_RULES),
)
db.commit()

# ============================================================
# RUNTIME STATES
# ============================================================

user_states = {}
user_data = {}
admin_data = {}

question_users = {}

# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

# ============================================================
# USERS
# ============================================================

def ensure_user(user):
    if not user:
        return

    db.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, balance, pension, pension_until, broken)
        VALUES (?, ?, ?, 0, 0, 0, 0)
        """,
        (user.id, user.username or "", user.first_name or ""),
    )

    db.execute(
        """
        UPDATE users
        SET username=?, first_name=?
        WHERE user_id=?
        """,
        (user.username or "", user.first_name or "", user.id),
    )

    db.commit()


def get_balance(user_id):
    row = db.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()
    return int(row["balance"]) if row else 0


def add_balance(user_id, amount):
    db.execute(
        "UPDATE users SET balance=balance+? WHERE user_id=?",
        (amount, user_id),
    )
    db.commit()


def take_balance(user_id, amount):
    cur = db.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE user_id=? AND balance>=?
        """,
        (amount, user_id, amount),
    )
    db.commit()
    return cur.rowcount == 1


def find_user_by_username(username):
    username = username.strip().lstrip("@").lower()

    row = db.execute(
        """
        SELECT user_id, username, first_name
        FROM users
        WHERE lower(username)=?
        """,
        (username,),
    ).fetchone()

    return row


def user_label(user):
    if user.username:
        return "@" + user.username
    return user.first_name or f"ID {user.id}"


def mention(user):
    name = user.first_name or "Пользователь"
    if user.username:
        return "@" + user.username
    return f'<a href="tg://user?id={user.id}">{name}</a>'

# ============================================================
# RULES
# ============================================================

def get_rules():
    row = db.execute(
        "SELECT value FROM settings WHERE key='rules'"
    ).fetchone()
    return row["value"] if row else DEFAULT_RULES


def set_rules(text):
    db.execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES ('rules', ?)",
        (text,),
    )
    db.commit()

# ============================================================
# USERNAME GENERATOR
# ============================================================

def generate_username(length: int) -> str:
    """Генерация случайного username заданной длины"""
    # Используем буквы и цифры для генерации
    chars = string.ascii_lowercase + string.digits
    
    # Генерируем случайный username
    username = ''.join(random.choices(chars, k=length))
    
    # Первый символ должен быть буквой (по правилам Telegram)
    if username[0].isdigit():
        username = random.choice(string.ascii_lowercase) + username[1:]
    
    return username

# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard(user_id):
    rows = [
        [
            InlineKeyboardButton("🫀 Каталог", callback_data="CATALOG"),
            InlineKeyboardButton("🫆 Промокод", callback_data="PROMO"),
        ],
        [
            InlineKeyboardButton("👾 Заказать Деф", callback_data="ORDER"),
        ],
        [
            InlineKeyboardButton("🫆 Искатель Юзеров", callback_data="USER_SEARCH"),
        ],
        [
            InlineKeyboardButton("👤 Профиль", callback_data="PROFILE"),
        ],
        [
            InlineKeyboardButton("💬 Секрет Тгк", callback_data="CHANNEL"),
        ],
        [
            InlineKeyboardButton("🔰 Вопрос к Ceko", callback_data="QUESTION"),
        ],
        [
            InlineKeyboardButton(
                f"💰 Баланс: {get_balance(user_id)}",
                callback_data="BALANCE",
            ),
        ],
    ]

    if is_admin(user_id):
        rows.append([
            InlineKeyboardButton(
                "🔐 Панель администратора",
                callback_data="ADMIN",
            )
        ])

    return InlineKeyboardMarkup(rows)


def back_keyboard(target="BACK"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=target)]
    ])


async def safe_edit(query, text, keyboard=None):
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )
        return
    except Exception:
        pass

    try:
        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )
    except Exception:
        pass

# ============================================================
# START / MAIN MENU
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    ensure_user(user)
    user_states.pop(user.id, None)
    user_data.pop(user.id, None)

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    if os.path.isfile(START_PHOTO):
        with open(START_PHOTO, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id),
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(user.id),
        )


async def main_menu(query):
    user = query.from_user
    ensure_user(user)

    user_states.pop(user.id, None)
    user_data.pop(user.id, None)

    try:
        await query.message.delete()
    except Exception:
        pass

    text = (
        "🔰 Ceko Hub Приветствует\n\n"
        "для того чтобы продолжить нажмите на кнопки\n\n"
        f"Баланс: {get_balance(user.id)} Деф"
    )

    if os.path.isfile(START_PHOTO):
        with open(START_PHOTO, "rb") as photo:
            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=main_keyboard(user.id),
            )
    else:
        await query.message.chat.send_message(
            text=text,
            reply_markup=main_keyboard(user.id),
        )

# ============================================================
# PROFILE
# ============================================================

async def profile(query):
    user = query.from_user
    ensure_user(user)
    
    row = db.execute(
        """
        SELECT balance, pension, broken
        FROM users
        WHERE user_id=?
        """,
        (user.id,),
    ).fetchone()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="BACK")],
    ])
    
    text = (
        "👤 ВАШ ПРОФИЛЬ\n\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Имя: {user.first_name or 'Не указано'}\n"
        f"📝 Username: @{user.username or 'Не указан'}\n"
        f"💰 Баланс: {row['balance']} Деф\n"
        f"📊 Пенсия: {float(row['pension']):.1f}%\n"
        f"🔨 Статус: {'Сломана' if row['broken'] else 'Работает'}"
    )
    
    await safe_edit(query, text, keyboard)

# ============================================================
# USER SEARCH (Искатель Юзеров)
# ============================================================

async def user_search_menu(query):
    """Меню искателя юзеров"""
    try:
        await query.message.delete()
    except Exception:
        pass

    text = (
        "🫆Вкладка Искатель Юзеров\n\n"
        "• ищу имбовые юзы \n"
        "• для начала нажать на кнопку!\n\n"
        "Сколько букв должно быть в юзе?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5", callback_data="GEN|5"),
            InlineKeyboardButton("7", callback_data="GEN|7"),
            InlineKeyboardButton("9", callback_data="GEN|9"),
        ],
        [
            InlineKeyboardButton("🎲 РАНДОМ", callback_data="GEN|RANDOM"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="BACK"),
        ],
    ])

    if os.path.isfile(USER_SEARCH_PHOTO):
        with open(USER_SEARCH_PHOTO, "rb") as photo:
            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard,
            )
    else:
        await query.message.chat.send_message(
            text=text,
            reply_markup=keyboard,
        )


async def generate_username_animated(query, length):
    """Анимированная генерация username"""
    user = query.from_user
    
    # Определяем длину
    if length == "RANDOM":
        actual_length = random.choice([5, 7, 9])
    else:
        actual_length = int(length)
    
    # Первое сообщение
    msg = await query.message.chat.send_message("🔰Генерирую…")
    
    # Ждем 4 секунды
    await asyncio.sleep(4)
    
    # Обновляем сообщение
    await msg.edit_text("🫆Подбираю буквы..")
    
    # Ждем 2 секунды
    await asyncio.sleep(2)
    
    # Генерируем username
    username = generate_username(actual_length)
    
    # Финальное сообщение
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🫆 Заново", callback_data="USER_SEARCH")],
        [InlineKeyboardButton("🔰 В главную", callback_data="BACK")],
    ])
    
    await msg.edit_text(
        f"🔰Готово сгенерированный юз\n\n"
        f"Юз: @{username}",
        reply_markup=keyboard
    )

# ============================================================
# CATALOG / DEF
# ============================================================

async def catalog(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Деф - 1 Мишка", callback_data="PRODUCT|1|1")],
        [InlineKeyboardButton("10 Деф - 5 Мишек", callback_data="PRODUCT|10|5")],
        [InlineKeyboardButton("25 Деф - 10 Мишек", callback_data="PRODUCT|25|10")],
        [InlineKeyboardButton("50 Деф - 40 Мишек", callback_data="PRODUCT|50|40")],
        [InlineKeyboardButton("◀️ Назад", callback_data="BACK")],
    ])

    text = "🤖 Каталог валюты\n\nДействуют скидки - навсегда"

    try:
        await query.message.delete()
    except Exception:
        pass

    if os.path.isfile(CATALOG_PHOTO):
        with open(CATALOG_PHOTO, "rb") as photo:
            await query.message.chat.send_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard,
            )
    else:
        await query.message.chat.send_message(
            text=text,
            reply_markup=keyboard,
        )


async def product(query, amount, bears):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Готово",
            callback_data=f"PAY|{amount}|{bears}",
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="CATALOG")],
    ])

    await safe_edit(
        query,
        (
            f"Вы выбрали {amount} Деф очков.\n\n"
            f"Для того чтобы получить их перейдите в ЛС "
            f"{ADMIN_USERNAME} и скиньте {bears} Мишек.\n\n"
            "После этого нажмите кнопку «Готово»."
        ),
        keyboard,
    )


async def payment(query, context, amount, bears):
    user = query.from_user
    ensure_user(user)

    await safe_edit(
        query,
        "✅ Ваш запрос принят и обрабатывается.\n\nПодождите несколько минут.",
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"CONFIRM|{user.id}|{amount}",
        )]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "🆕 НОВАЯ ЗАЯВКА\n\n"
            f"👤 {user_label(user)}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Деф: {amount}\n"
            f"🧸 Мишек: {bears}\n\n"
            "Проверь оплату."
        ),
        reply_markup=keyboard,
    )


async def confirm_payment(query, context, user_id, amount):
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Только администратор.", show_alert=True)
        return

    add_balance(user_id, amount)

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ Администратор проверил оплату и выдал вам Деф Очки.\n\n"
            f"➕ Получено: {amount} Деф\n"
            f"💰 Баланс: {get_balance(user_id)} Деф"
        ),
    )

    try:
        await query.edit_message_text(
            query.message.text + "\n\n✅ ПОДТВЕРЖДЕНО"
        )
    except Exception:
        pass

# ============================================================
# DEF PROMO
# ============================================================

async def promo(query):
    user_states[query.from_user.id] = "PROMO"
    await safe_edit(
        query,
        "🫆 Промокод\n\nОтправьте промокод сообщением:",
        back_keyboard(),
    )


def generate_code():
    while True:
        code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10,
            )
        )
        exists1 = db.execute(
            "SELECT 1 FROM promos WHERE code=?",
            (code,),
        ).fetchone()
        if not exists1:
            return code


async def check_def_promo(update):
    user = update.effective_user
    code = update.message.text.strip().upper()

    row = db.execute(
        "SELECT amount, uses FROM promos WHERE code=?",
        (code,),
    ).fetchone()

    if not row:
        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=back_keyboard(),
        )
        return

    if row["uses"] <= 0:
        await update.message.reply_text(
            "❌ Промокод больше недоступен.",
            reply_markup=back_keyboard(),
        )
        return

    add_balance(user.id, row["amount"])

    db.execute(
        "UPDATE promos SET uses=uses-1 WHERE code=?",
        (code,),
    )
    db.commit()

    user_states.pop(user.id, None)

    await update.message.reply_text(
        (
            "🎉 Промокод активирован!\n\n"
            f"➕ Получено: {row['amount']} Деф\n"
            f"💰 Баланс: {get_balance(user.id)} Деф"
        ),
        reply_markup=back_keyboard(),
    )

# ============================================================
# ORDER DEF
# ============================================================

async def order(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "1 Деф - 1 Деф Очка",
            callback_data="ORDER_ONE",
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="BACK")],
    ])

    await safe_edit(
        query,
        "👾 Заказать Деф\n\nВыбирай пункт:",
        keyboard,
    )


async def order_one(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data="ORDER_CONFIRM",
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="ORDER")],
    ])

    await safe_edit(
        query,
        (
            "👾 Вы выбрали:\n\n"
            "1 Деф - 1 Деф Очка\n\n"
            "⚠️ После подтверждения 1 Деф будет списан с баланса.\n\n"
            "Подтвердить?"
        ),
        keyboard,
    )


async def order_confirm(query, context):
    user = query.from_user
    ensure_user(user)

    if not take_balance(user.id, 1):
        await safe_edit(
            query,
            "❌ Недостаточно Деф Очков.\n\nДля заказа нужен минимум 1 Деф.",
            back_keyboard(),
        )
        return

    await safe_edit(
        query,
        (
            "✅ Заказ принят!\n\n"
            "1 Деф списан с баланса.\n"
            "Администратор получил заявку.\n\n"
            f"💰 Осталось: {get_balance(user.id)} Деф"
        ),
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "👾 НОВЫЙ ЗАКАЗ ДЕФ\n\n"
            f"👤 {user_label(user)}\n"
            f"🆔 {user.id}\n\n"
            "📦 Заказ: 1 Деф\n"
            "💸 Списано: 1 Деф\n\n"
            "Прошу перейти к пользователю."
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💬 Профиль",
                url=f"tg://user?id={user.id}",
            )]
        ]),
    )

# ============================================================
# CHANNEL / QUESTION
# ============================================================

async def channel(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Открыть канал", url=CHANNEL_URL)],
        [InlineKeyboardButton("◀️ Назад", callback_data="BACK")],
    ])
    await safe_edit(
        query,
        "💬 Секрет Тгк\n\nНажмите кнопку ниже:",
        keyboard,
    )


async def question(query):
    user_states[query.from_user.id] = "QUESTION"
    await safe_edit(
        query,
        (
            "🔰 Вопрос к Ceko\n\n"
            "Отправьте сообщение любого типа.\n\n"
            "Администратор сможет ответить вам."
        ),
        back_keyboard(),
    )


async def receive_question(update, context):
    user = update.effective_user

    try:
        info = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔰 НОВЫЙ ВОПРОС\n\n"
                f"👤 {user_label(user)}\n"
                f"🆔 {user.id}\n\n"
                "Ответьте реплаем на сообщение."
            ),
        )

        question_users[info.message_id] = user.id

        copied = await update.message.copy(chat_id=ADMIN_ID)
        question_users[copied.message_id] = user.id

        user_states.pop(user.id, None)

        await update.message.reply_text(
            "✅ Вопрос отправлен администратору.",
            reply_markup=back_keyboard(),
        )

    except Exception as error:
        logger.exception("QUESTION ERROR: %s", error)
        await update.message.reply_text("❌ Ошибка отправки вопроса.")

# ============================================================
# PENSION GAME
# ============================================================

async def pension(update, context):
    user = update.effective_user
    if not user:
        return

    ensure_user(user)

    row = db.execute(
        """
        SELECT pension, pension_until, broken
        FROM users
        WHERE user_id=?
        """,
        (user.id,),
    ).fetchone()

    now = int(time.time())

    if row["broken"]:
        await update.message.reply_text(
            f"{mention(user)} бабки сломали вашу базу понижения пенсии",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔨 Восстановить",
                    callback_data=f"RESTORE|{user.id}",
                )]
            ]),
        )
        return

    if row["pension_until"] > now:
        await update.message.reply_text(
            f"⏳ Подожди ещё {row['pension_until'] - now} секунд."
        )
        return

    value = round(float(row["pension"]) + 0.1, 1)

    db.execute(
        """
        UPDATE users
        SET pension=?, pension_until=?
        WHERE user_id=?
        """,
        (value, now + PENSION_COOLDOWN, user.id),
    )
    db.commit()

    if random.random() < 0.03:
        db.execute(
            "UPDATE users SET broken=1 WHERE user_id=?",
            (user.id,),
        )
        db.commit()

        await update.message.reply_text(
            f"{mention(user)} бабки сломали вашу базу понижения пенсии",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔨 Восстановить",
                    callback_data=f"RESTORE|{user.id}",
                )]
            ]),
        )
    else:
        await update.message.reply_text(
            (
                f"{mention(user)} понизил пенсию бабушкам\n\n"
                f"Понижено {value:.1f}%"
            ),
            parse_mode="HTML",
        )


async def restore(query, user_id):
    if query.from_user.id != user_id:
        await query.answer("❌ Это не ваша база.", show_alert=True)
        return

    db.execute(
        "UPDATE users SET broken=0 WHERE user_id=?",
        (user_id,),
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
        WHERE pension>0
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
            text += f"{i}. {name} — {float(row['pension']):.1f}%\n"

    await update.message.reply_text(text)

# ============================================================
# RULES / NEW MEMBERS
# ============================================================

async def rules_command(update, context):
    await update.message.reply_text(get_rules())


async def update_rules_command(update, context):
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text or ""

    new_rules = re.sub(
        r"(?is)^\s*обн\s+правила\s*",
        "",
        text,
    ).strip()

    if not new_rules:
        await update.message.reply_text(
            "❌ Напишите новый текст после «Обн правила»."
        )
        return

    set_rules(new_rules)
    await update.message.reply_text("✅ Правила успешно обновлены!")


async def new_member(update, context):
    message = update.message
    if not message or not message.new_chat_members:
        return

    for user in message.new_chat_members:
        if user.is_bot:
            continue

        await message.reply_text(
            (
                f"{mention(user)} приветствую тебя в наш чат Ceko 👋\n\n"
                "Чтобы посмотреть правила напиши:\n"
                "правила"
            ),
            parse_mode="HTML",
        )

# ============================================================
# GROUP MODERATION / BOT WORD
# ============================================================

LINK_PATTERN = (
    r"(https?://\S+)"
    r"|"
    r"(www\.\S+)"
    r"|"
    r"(t\.me/\S+)"
    r"|"
    r"(telegram\.me/\S+)"
    r"|"
    r"(discord\.gg/\S+)"
)


async def group_chat(update, context):
    message = update.message
    if not message:
        return

    user = update.effective_user
    if not user or user.is_bot:
        return

    text = message.text or ""

    if re.fullmatch(r"\s*правила\s*", text, flags=re.IGNORECASE):
        await rules_command(update, context)
        return

    if re.search(LINK_PATTERN, text, flags=re.IGNORECASE):
        if is_admin(user.id):
            return

        try:
            await message.delete()
        except Exception:
            pass

        try:
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
                until_date=int(time.time()) + 3600,
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"{mention(user)} был замучен на 1 час\n"
                    "Причина: реклама"
                ),
                parse_mode="HTML",
            )
        except Exception as error:
            logger.exception("MUTE ERROR: %s", error)

        return

    # Только отдельное слово "бот".
    if re.search(
        r"(?<![а-яёa-z0-9])бот(?![а-яёa-z0-9])",
        text,
        flags=re.IGNORECASE,
    ):
        await message.reply_text("Ceko на месте✅")

# ============================================================
# JERRY
# ============================================================

async def random_jerry(update, context):
    if not update.message:
        return

    user = update.effective_user
    if not user or user.is_bot:
        return

    if random.random() > 0.01:
        return

    if not os.path.isfile(JERRY_VIDEO):
        return

    try:
        with open(JERRY_VIDEO, "rb") as video:
            await update.message.reply_video(video=video)
    except Exception:
        pass

# ============================================================
# CHANNEL AUTO REPLY
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

    if message.date:
        age = time.time() - message.date.timestamp()
        if age > 10:
            return

    try:
        await message.reply_text(CHANNEL_RULES_TEXT)
    except Exception:
        pass

# ============================================================
# PRIVATE MESSAGE ROUTER
# ============================================================

async def private_message_router(update, context):
    user = update.effective_user
    if not user:
        return

    ensure_user(user)

    state = user_states.get(user.id)

    if state == "PROMO":
        if update.message.text:
            await check_def_promo(update)
        return

    if state == "QUESTION":
        await receive_question(update, context)
        return

    if is_admin(user.id):
        if state == "PROMO_AMOUNT":
            await admin_amount(update)
            return

        if state == "PROMO_USES":
            await admin_uses(update)
            return

# ============================================================
# ADMIN REPLY
# ============================================================

async def admin_reply(update, context):
    if not is_admin(update.effective_user.id):
        return

    message = update.message

    if not message or not message.reply_to_message:
        return

    target_user = question_users.get(
        message.reply_to_message.message_id
    )

    if not target_user:
        return

    try:
        await message.copy(chat_id=target_user)
        await message.reply_text("✅ Ответ отправлен.")
    except Exception:
        await message.reply_text("❌ Не удалось отправить ответ.")

# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Создать промокод Деф",
            callback_data="ADMIN_CREATE_DEF",
        )],
        [InlineKeyboardButton(
            "📊 Статистика",
            callback_data="ADMIN_STATS",
        )],
        [InlineKeyboardButton(
            "👥 Пользователи",
            callback_data="ADMIN_USERS",
        )],
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data="BACK",
        )],
    ])


async def admin(query):
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Нет доступа.", show_alert=True)
        return

    await safe_edit(
        query,
        "🔐 Панель администратора\n\nВыберите действие:",
        admin_keyboard(),
    )

# ============================================================
# ADMIN DEF PROMO
# ============================================================

async def admin_create_def(query):
    if not is_admin(query.from_user.id):
        return

    admin_data.clear()
    user_states[query.from_user.id] = "PROMO_AMOUNT"

    await safe_edit(
        query,
        "➕ Создание промокода Деф\n\nНапишите сколько Деф будет выдавать промокод.",
        back_keyboard("ADMIN"),
    )


async def admin_amount(update):
    if not is_admin(update.effective_user.id):
        return

    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text("❌ Нужно положительное число.")
        return

    admin_data["amount"] = amount
    user_states[update.effective_user.id] = "PROMO_USES"

    await update.message.reply_text(
        "Теперь напишите количество использований промокода."
    )


async def admin_uses(update):
    if not is_admin(update.effective_user.id):
        return

    try:
        uses = int(update.message.text.strip())
        if uses <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text("❌ Нужно положительное число.")
        return

    admin_data["uses"] = uses

    await update.message.reply_text(
        (
            "📋 Проверьте:\n\n"
            f"💰 Деф: {admin_data['amount']}\n"
            f"👥 Использований: {uses}\n\n"
            "Нажмите «Создать» в панели."
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✅ Создать",
                callback_data="ADMIN_CONFIRM_DEF",
            )],
            [InlineKeyboardButton(
                "❌ Отмена",
                callback_data="ADMIN",
            )],
        ]),
    )


async def admin_confirm_def(query):
    if not is_admin(query.from_user.id):
        return

    if "amount" not in admin_data or "uses" not in admin_data:
        await safe_edit(query, "❌ Данные создания промокода потеряны.", admin_keyboard())
        return

    code = generate_code()

    db.execute(
        """
        INSERT INTO promos(code, amount, uses)
        VALUES (?, ?, ?)
        """,
        (code, admin_data["amount"], admin_data["uses"]),
    )
    db.commit()

    amount = admin_data["amount"]
    uses = admin_data["uses"]

    admin_data.clear()
    user_states.pop(query.from_user.id, None)

    await safe_edit(
        query,
        (
            "✅ ПРОМОКОД СОЗДАН\n\n"
            f"🎟 {code}\n"
            f"💰 {amount} Деф\n"
            f"👥 Использований: {uses}"
        ),
        admin_keyboard(),
    )

# ============================================================
# ADMIN STATS / USERS
# ============================================================

async def admin_stats(query):
    if not is_admin(query.from_user.id):
        return

    users = db.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    total = db.execute(
        "SELECT COALESCE(SUM(balance),0) AS s FROM users"
    ).fetchone()["s"]

    promos = db.execute(
        "SELECT COUNT(*) AS c FROM promos"
    ).fetchone()["c"]

    await safe_edit(
        query,
        (
            "📊 СТАТИСТИКА\n\n"
            f"👥 Пользователей: {users}\n"
            f"💰 Деф на балансах: {total}\n"
            f"🎟 Промокодов Деф: {promos}"
        ),
        admin_keyboard(),
    )


async def admin_users(query):
    if not is_admin(query.from_user.id):
        return

    users = db.execute(
        """
        SELECT user_id, username, first_name, balance
        FROM users
        ORDER BY balance DESC
        LIMIT 20
        """
    ).fetchall()

    text = "👥 ТОП 20 ПОЛЬЗОВАТЕЛЕЙ\n\n"

    for i, user in enumerate(users, 1):
        name = user["username"] or user["first_name"] or f"ID {user['user_id']}"
        text += f"{i}. @{name} - {user['balance']} Деф\n"

    await safe_edit(
        query,
        text,
        admin_keyboard(),
    )

# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(update, context):
    query = update.callback_query
    if not query:
        return

    data = query.data or ""

    try:
        await query.answer()
    except Exception:
        pass

    try:
        # Main
        if data == "BACK":
            await main_menu(query)
            return

        # Profile
        if data == "PROFILE":
            await profile(query)
            return

        # User Search
        if data == "USER_SEARCH":
            await user_search_menu(query)
            return

        if data.startswith("GEN|"):
            length = data.split("|")[1]
            await generate_username_animated(query, length)
            return

        # Catalog
        if data == "CATALOG":
            await catalog(query)
            return

        if data.startswith("PRODUCT|"):
            parts = data.split("|")
            await product(
                query,
                int(parts[1]),
                int(parts[2]),
            )
            return

        if data.startswith("PAY|"):
            parts = data.split("|")
            await payment(
                query,
                context,
                int(parts[1]),
                int(parts[2]),
            )
            return

        if data.startswith("CONFIRM|"):
            parts = data.split("|")
            await confirm_payment(
                query,
                context,
                int(parts[1]),
                int(parts[2]),
            )
            return

        # Def promo
        if data == "PROMO":
            await promo(query)
            return

        # Order
        if data == "ORDER":
            await order(query)
            return

        if data == "ORDER_ONE":
            await order_one(query)
            return

        if data == "ORDER_CONFIRM":
            await order_confirm(query, context)
            return

        # Channel
        if data == "CHANNEL":
            await channel(query)
            return

        # Question
        if data == "QUESTION":
            await question(query)
            return

        # Balance
        if data == "BALANCE":
            await query.answer(
                f"💰 Баланс: {get_balance(query.from_user.id)} Деф",
                show_alert=True,
            )
            return

        # Restore
        if data.startswith("RESTORE|"):
            await restore(
                query,
                int(data.split("|")[1]),
            )
            return

        # Admin
        if data == "ADMIN":
            await admin(query)
            return

        if data == "ADMIN_CREATE_DEF":
            await admin_create_def(query)
            return

        if data == "ADMIN_CONFIRM_DEF":
            await admin_confirm_def(query)
            return

        if data == "ADMIN_STATS":
            await admin_stats(query)
            return

        if data == "ADMIN_USERS":
            await admin_users(query)
            return

        logger.warning("UNKNOWN CALLBACK: %s", data)

    except Exception as error:
        logger.exception("CALLBACK ERROR: %s", error)
        try:
            await query.answer(
                "❌ Ошибка обработки кнопки.",
                show_alert=True,
            )
        except Exception:
            pass

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
        "BOT ERROR",
        exc_info=context.error,
    )

# ============================================================
# MAIN
# ============================================================

def main():
    if TOKEN.startswith("ВСТАВЬ_"):
        print("❌ Вставьте новый токен в переменную TOKEN.")
        return

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler("start", start),
        group=0,
    )

    # English commands
    application.add_handler(
        CommandHandler("lowerpension", lowerpension_command),
        group=0,
    )

    application.add_handler(
        CommandHandler("top", top_command),
        group=0,
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(callback_handler),
        group=0,
    )

    # New members
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_member,
        ),
        group=1,
    )

    # Admin replies must be before generic private handler.
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.REPLY
            & filters.ALL,
            admin_reply,
        ),
        group=2,
    )

    # Private text / media routing.
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & ~filters.COMMAND,
            private_message_router,
        ),
        group=5,
    )

    # Rules / game / moderation.
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & filters.Regex(
                r"(?is)^\s*обн\s+правила\b"
            ),
            update_rules_command,
        ),
        group=6,
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & filters.Regex(
                r"(?i)^\s*ппб\s*$"
            ),
            pension,
        ),
        group=7,
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & filters.Regex(
                r"(?i)^\s*понизить пенсию бабушкам\s*$"
            ),
            pension,
        ),
        group=7,
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & filters.Regex(
                r"(?i)^\s*топ\s*$"
            ),
            top,
        ),
        group=7,
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            group_chat,
        ),
        group=10,
    )

    # Random Jerry.
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            random_jerry,
        ),
        group=11,
    )

    # Channel discussion automatic replies.
    application.add_handler(
        MessageHandler(
            filters.ALL,
            channel_auto_reply,
        ),
        group=12,
    )

    application.add_error_handler(error_handler)

    print("========================================")
    print("       CEKO HUB ЗАПУЩЕН")
    print("========================================")
    print("ADMINS:", ADMIN_IDS)
    print("DATABASE:", DB_FILE)
    print("========================================")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
