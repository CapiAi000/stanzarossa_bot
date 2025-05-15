import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__)
waiting_users = []
active_chats = {}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto su Stanzarossa! Usa /search per iniziare.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        await update.message.reply_text("Sei già in chat! Usa /stop per uscire.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("Sei già in attesa di un partner...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="💬 Chat iniziata! Scrivi pure.")
        await context.bot.send_message(chat_id=partner_id, text="💬 Chat iniziata! Scrivi pure.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("In attesa di un partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("Hai annullato la ricerca.")
    elif user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text("Hai lasciato la chat.")
        await context.bot.send_message(chat_id=partner_id, text="Il partner ha lasciato la chat.")
    else:
        await update.message.reply_text("Non sei in chat o in attesa.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await update.message.reply_text("Non sei in chat anonima. Usa /search per iniziare.")

# Telegram bot setup
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    app.run(host="0.0.0.0", port=PORT)
