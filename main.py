import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8948498198:AAFr_K6rFhN5G6XqP9vK3zY-EXAMPLE")

# Flask server to keep Render Web Service Live
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot is LIVE - All Photo Tools Working!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot LIVE Hai! Photo bhejo - PDF, Compress, Resize sab kar dunga!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("📸 Photo mil gaya! Processing...")
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        img = Image.open(io.BytesIO(photo_bytes))
        pdf_buffer = io.BytesIO()
        img.convert("RGB").save(pdf_buffer, "PDF")
        pdf_buffer.seek(0)
        await update.message.reply_document(document=pdf_buffer, filename="converted.pdf")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

if __name__ == "__main__":
    # Start Flask in background thread
    threading.Thread(target=run_flask, daemon=True).start()
    print("V4 Bot ON - Starting...")
    
    # Start Telegram Bot with drop_pending_updates to fix Conflict error
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
