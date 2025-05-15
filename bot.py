import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

waiting_users = []
active_chats = {}

from telegram.ext import Dispatcher

dispatcher = Dispatcher(bot, None, workers=0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto su Stanzarossa! Usa /search per iniziare una chat anonima.")

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
        await bot.send_message(chat_id=partner, text="🎯 Partner trovato! Inizia a chattare.")
        await update.message.reply_text("🎯 Partner trovato! Inizia a chattare.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("🕓 In attesa di un partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner = active_chats.pop(user_id)
        active_chats.pop(partner, None)
        await bot.send_message(chat_id=partner, text="🚫 Il tuo partner ha terminato la chat.")
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
            await bot.send_message(chat_id=partner, text=update.message.text)
        elif update.message.photo:
            await bot.send_photo(chat_id=partner, photo=update.message.photo[-1].file_id)
        elif update.message.sticker:
            await bot.send_sticker(chat_id=partner, sticker=update.message.sticker.file_id)
    else:
        await update.message.reply_text("ℹ️ Usa /search per iniziare una chat anonima.")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("search", search))
dispatcher.add_handler(CommandHandler("stop", stop))
dispatcher.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Stanzarossa Bot è attivo."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

