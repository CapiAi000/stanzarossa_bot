import os
import asyncio
import nest_asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

# Configurazioni
BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

# Inizializza Flask
app = Flask(__name__)

# Stato utenti
waiting_users = []
active_chats = {}

# Handlers Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto su Stanzarossa! Usa /search per iniziare.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        await update.message.reply_text("Sei già in chat! Usa /stop per uscire.")
    elif user_id in waiting_users:
        await update.message.reply_text("Attendi... stiamo cercando un partner.")
    elif waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(user_id, "💬 Chat iniziata!")
        await context.bot.send_message(partner_id, "💬 Chat iniziata!")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("In attesa di un partner... Usa /stop per annullare.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("Hai annullato la ricerca.")
    elif user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text("Chat terminata.")
        await context.bot.send_message(partner_id, "Il partner ha lasciato la chat.")
    else:
        await update.message.reply_text("Non sei in chat né in attesa.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats and update.message.text:
        partner_id = active_chats[user_id]
        await context.bot.send_message(partner_id, update.message.text)

# Inizializza bot Telegram
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Imposta il webhook in Flask
@app.before_first_request
def setup_webhook():
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(application.initialize())
    asyncio.get_event_loop().run_until_complete(
        application.bot.set_webhook(f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}")
    )

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
