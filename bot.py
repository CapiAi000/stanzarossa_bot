from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request
import os
import asyncio

BOT_TOKEN = os.environ["BOT_TOKEN"]

app = Flask(__name__)

# Variabile globale per memorizzare utenti in attesa e le chat attive
waiting_users = []
active_chats = {}  # user_id -> partner_user_id

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Benvenuto su Stanzarossa! Usa /search per trovare un partner per chat anonima."
    )

# Comando /search per cercare un partner
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

        # Notifica entrambi
        await context.bot.send_message(chat_id=user_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
        await context.bot.send_message(chat_id=partner_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("In attesa di un partner... Usa /stop per annullare.")

# Comando /stop per terminare la chat o annullare la ricerca
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

# Gestione dei messaggi anonimi (inoltro al partner)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        await update.message.reply_text("Non sei in chat anonima. Usa /search per cercare un partner.")
        return

    partner_id = active_chats[user_id]
    # Inoltra solo testo, per semplicità
    if update.message.text:
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await update.message.reply_text("Solo messaggi di testo supportati al momento.")

# Crea l'Application (builder)
application = Application.builder().token(BOT_TOKEN).build()

# Aggiungi handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

if __name__ == "__main__":
    app.run(port=5000)

