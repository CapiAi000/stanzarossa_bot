import os
import asyncio
import nest_asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Applica patch per eseguire asyncio dentro Flask
nest_asyncio.apply()

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__)

# Stato chat anonima
waiting_users = []
active_chats = {}

# Handlers bot

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Benvenuto su Stanzarossa! Usa /search per trovare un partner per chat anonima."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        await update.message.reply_text("Sei già in chat anonima! Usa /stop per terminarla.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("Sei già in lista d'attesa, aspetta un partner...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
        await context.bot.send_message(chat_id=partner_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("In attesa di un partner... Usa /stop per annullare.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("Ricerca annullata.")
        return
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text("Chat terminata.")
        await context.bot.send_message(chat_id=partner_id, text="Il partner ha terminato la chat.")
        return
    await update.message.reply_text("Non sei in chat né in attesa.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        await update.message.reply_text("Non sei in chat anonima. Usa /search per iniziare.")
        return
    partner_id = active_chats[user_id]
    if update.message.text:
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await update.message.reply_text("Al momento supportiamo solo messaggi di testo.")

# Crea l'Application del bot
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Webhook route async
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

# Avvia Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)


