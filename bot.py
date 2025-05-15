from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from flask import Flask, request
import os
import asyncio

# Carica token e porta
BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

# Flask app
app = Flask(__name__)

# Variabili globali
waiting_users = []
active_chats = {}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Cerca un partner", callback_data="search")],
        [InlineKeyboardButton("❌ Termina chat", callback_data="stop")],
        [InlineKeyboardButton("ℹ️ Aiuto", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Benvenuto su *Stanzarossa!*\n\nChatta in modo anonimo con altri utenti.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Guida*\n\n"
        "- Usa /search per iniziare una chat anonima.\n"
        "- Usa /stop per terminare la chat.\n"
        "- Tutti i messaggi sono privati e anonimi.",
        parse_mode="Markdown"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text="Sei già in chat anonima! Usa /stop per terminarla.")
        return
    if user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text="Sei già in lista d'attesa, aspetta un partner...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
        await context.bot.send_message(chat_id=partner_id, text="💬 Chat anonima iniziata! Scrivi per parlare.")
    else:
        waiting_users.append(user_id)
        await context.bot.send_message(chat_id=user_id, text="In attesa di un partner... Usa /stop per annullare.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await context.bot.send_message(chat_id=user_id, text="Ricerca annullata.")
        return
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=user_id, text="Chat terminata.")
        await context.bot.send_message(chat_id=partner_id, text="❌ Il partner ha terminato la chat.")
        return
    await context.bot.send_message(chat_id=user_id, text="Non sei in chat né in attesa.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_chats:
        await context.bot.send_message(chat_id=user_id, text="Non sei in chat anonima. Usa /search per iniziare.")
        return
    partner_id = active_chats[user_id]
    if update.message.text:
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await context.bot.send_message(chat_id=user_id, text="Al momento supportiamo solo messaggi di testo.")

# --- Bottoni Inline ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "search":
        await search(update, context)
    elif data == "stop":
        await stop(update, context)
    elif data == "help":
        await query.edit_message_text(
            "ℹ️ *Guida*\n\n"
            "- 🔍 Cerca un partner per iniziare una chat anonima.\n"
            "- ❌ Termina la chat quando vuoi.\n"
            "- 🔒 Nessuno vedrà il tuo username.",
            parse_mode="Markdown"
        )

# --- Application Setup ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# --- Webhook ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

# --- Avvio su Render ---
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    app.run(host="0.0.0.0", port=PORT)

