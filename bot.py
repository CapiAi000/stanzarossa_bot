import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask app
flask_app = Flask(__name__)

# Bot Application PTB 20+
application = Application.builder().token(BOT_TOKEN).build()

waiting_users = []
active_chats = {}

# Comandi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto su Stanzarossa! Usa /search per iniziare.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await update.message.reply_text("🔴 Sei già in chat. Usa /stop per terminare.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("🕓 Sei già in attesa di un partner.")
        return
    if waiting_users:
        partner = waiting_users.pop(0)
        active_chats[user_id] = partner
        active_chats[partner] = user_id
        await context.bot.send_message(chat_id=partner, text="🎯 Partner trovato! Inizia a chattare.")
        await update.message.reply_text("🎯 Partner trovato! Inizia a chattare.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("🕓 In attesa di un partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner = active_chats.pop(user_id)
        active_chats.pop(partner, None)
        await context.bot.send_message(chat_id=partner, text="🚫 Il tuo partner ha terminato la chat.")
        await update.message.reply_text("🚫 Chat terminata.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("🔕 Ricerca annullata.")
    else:
        await update.message.reply_text("ℹ️ Non sei in una chat.")

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner = active_chats[user_id]
        if update.message.text:
            await context.bot.send_message(chat_id=partner, text=update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=partner, photo=update.message.photo[-1].file_id)
        elif update.message.sticker:
            await context.bot.send_sticker(chat_id=partner, sticker=update.message.sticker.file_id)
    else:
        await update.message.reply_text("ℹ️ Usa /search per iniziare una chat anonima.")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay))

# Route per Telegram webhook
@flask_app.post(f"/{BOT_TOKEN}")
async def webhook() -> str:
    update = Update.de_json(data=request.get_json(force=True), bot=application.bot)
    await application.process_update(update)
    return "ok"

# Route base
@flask_app.get("/")
def index():
    return "✅ Stanzarossa Bot è attivo su webhook!"

# Avvio per render
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

