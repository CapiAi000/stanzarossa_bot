import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

waiting_users = []
active_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto su Stanzarossa. Usa /search per iniziare una chat anonima!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user in active_chats:
        await update.message.reply_text("🔴 Sei già in una chat. Usa /stop per terminarla.")
        return
    if waiting_users:
        partner = waiting_users.pop(0)
        active_chats[user] = partner
        active_chats[partner] = user
        await context.bot.send_message(partner, "🎯 Partner trovato! Inizia a chattare.")
        await update.message.reply_text("🎯 Partner trovato! Inizia a chattare.")
    else:
        waiting_users.append(user)
        await update.message.reply_text("🕓 In attesa di un partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user in active_chats:
        partner = active_chats.pop(user)
        active_chats.pop(partner, None)
        await context.bot.send_message(partner, "🚫 Il tuo partner ha lasciato la chat.")
        await update.message.reply_text("🚫 Hai lasciato la chat.")
    elif user in waiting_users:
        waiting_users.remove(user)
        await update.message.reply_text("🔕 Hai interrotto la ricerca.")
    else:
        await update.message.reply_text("ℹ️ Non sei in una chat.")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user in active_chats:
        partner = active_chats[user]
        if update.message.text:
            await context.bot.send_message(partner, update.message.text)
        elif update.message.sticker:
            await context.bot.send_sticker(partner, update.message.sticker.file_id)
        elif update.message.photo:
            await context.bot.send_photo(partner, update.message.photo[-1].file_id)
    else:
        await update.message.reply_text("💬 Non sei in una chat. Usa /search per iniziare.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("search", search))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.ALL, message))

app.run_polling()
