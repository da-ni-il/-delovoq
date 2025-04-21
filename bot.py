
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import os

logging.basicConfig(level=logging.INFO)

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "друг"
    users[str(user.id)] = name
    save_users(users)
    await update.message.reply_text(
        f"Здравствуйте, {name}! Вас приветствует «Деловой инструмент». Мы продаём буровой инструмент."
        "\n\nВы можете открыть каталог или оставить заявку:",
        reply_markup=main_menu()
    )

def main_menu():
    keyboard = [
        [InlineKeyboardButton("Каталог инструмента", callback_data="catalog")],
        [InlineKeyboardButton("Оставить заявку", callback_data="request_tool")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Каталог:\n\n— Буровые коронки\n— Буровые штанги\n— Насадки и адаптеры\n— Расходники\n\nДля заказа нажмите «Оставить заявку».",
        reply_markup=main_menu()
    )

ASK_REQUEST = 1

async def ask_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, напишите, что вам нужно. Мы с вами свяжемся.")
    return ASK_REQUEST

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "пользователь"
    request_text = update.message.text
    await update.message.reply_text(
        f"Спасибо, {name}! Ваша заявка принята:\n\n{request_text}"
    )
    return ConversationHandler.END

async def monthly_reminder(app):
    for user_id, name in users.items():
        try:
            await app.bot.send_message(
                chat_id=int(user_id),
                text=f"Здравствуйте, {name}, это «Деловой инструмент». Хотели бы уточнить, требуется ли вам какой-нибудь инструмент?"
            )
        except Exception as e:
            logging.warning(f"Ошибка при отправке пользователю {user_id}: {e}")

async def main():
    app = ApplicationBuilder().token("ТВОЙ_ТОКЕН").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_catalog, pattern="catalog"))
    app.add_handler(CallbackQueryHandler(ask_request, pattern="request_tool"))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_request, pattern="request_tool")],
        states={ASK_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request)]},
        fallbacks=[],
    )
    app.add_handler(conv_handler)

    scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(lambda: app.create_task(monthly_reminder(app)), 'cron', day=1, hour=10, minute=0)
    scheduler.start()

    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
