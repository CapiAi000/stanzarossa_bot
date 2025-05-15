from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request
import os
import asyncio
import nest_asyncio

nest_asyncio.apply()  # Per compatibilità con asyncio in Flask

# --- Config ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

# --- Flask ---
app = Flask(__name__)

# --- Stato ---
waiting_users = []
active_chats = {}

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/search")],
        [KeyboardButton("/stop")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Benvenuto su Stanzarossa!\nUsa /search per avviare una chat anonima.",
        reply_markup=reply_markup
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        await update.message.reply_text("Sei già in chat. Usa /stop per uscire.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("Sei già in attesa di un partner...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(user_id, "💬 Chat iniziata! Scrivi per parlare.")
        await context.bot.send_message(partner_id, "💬 Chat iniziata! Scrivi per parlare.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ In attesa di un partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("⛔ Ricerca annullata.")
    elif user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text("Chat terminata.")
        await context.bot.send_message(partner_id, "❌ Il partner ha lasciato la chat.")
    else:
        await update.message.reply_text("Non sei in chat né in attesa.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        await update.message.reply_text("❗ Non sei in una chat anonima. Usa /search.")
        return
    partner_id = active_chats[user_id]
    if update.message.text:
        await context.bot.send_message(partner_id, update.message.text)
    else:
        await update.message.reply_text("Solo messaggi di testo al momento.")

# --- Bot App ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# --- Webhook route ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    if not application.is_initialized:
        await application.initialize()
    await application.process_update(update)
    return "ok"

# --- Flask run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT))


