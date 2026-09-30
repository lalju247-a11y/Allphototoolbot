import os
import io
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import threading

BOT_TOKEN = os.environ.get("BOT_TOKEN")
app = Flask(__name__)
@app.route('/')
def home():
    return "All Photo Tools LIVE - Level 1 Pack"

user_photos = {}
user_state = {}  # For custom resize

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 All Photo Tools LIVE!\n\n"
        "LEVEL 1 PACK 🔥\n"
        "✂️ BG Remove\n"
        "💧 Watermark\n"
        "🔤 Image to Text\n"
        "📏 Custom Resize\n"
        "📄 PDF / Compress / JPG / Rotate\n\n"
        "Bas ek Photo bhejo!"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    file_bytes = await file.download_as_bytearray()
    user_id = update.effective_user.id
    user_photos[user_id] = file_bytes
    user_state[user_id] = None

    keyboard = [
        [InlineKeyboardButton("✂️ BG Remove 🔥", callback_data="bg_remove")],
        [InlineKeyboardButton("💧 Watermark Lagao", callback_data="watermark"),
         InlineKeyboardButton("🔤 Text Nikalo (OCR)", callback_data="ocr")],
        [InlineKeyboardButton("📏 Custom Size", callback_data="custom_resize"),
         InlineKeyboardButton("📏 Quick Resize", callback_data="resize_menu")],
        [InlineKeyboardButton("📄 PDF", callback_data="pdf"),
         InlineKeyboardButton("🗜️ Compress", callback_data="compress")],
        [InlineKeyboardButton("🔄 JPG", callback_data="to_jpg"),
         InlineKeyboardButton("↩️ Rotate", callback_data="rotate")]
    ]
    await update.message.reply_text("📸 Photo mil gaya! Feature choose karo:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) == "awaiting_size" and user_id in user_photos:
        text = update.message.text.strip().lower().replace(" ", "")
        try:
            if "x" in text:
                w, h = map(int, text.split("x"))
                file_bytes = user_photos[user_id]
                image = Image.open(io.BytesIO(file_bytes))
                resized = image.resize((w, h))
                buf = io.BytesIO()
                resized.save(buf, "PNG")
                buf.seek(0)
                await update.message.reply_photo(photo=buf, caption=f"✅ Custom Resized: {w}x{h}")
                user_state[user_id] = None
                return
            else:
                await update.message.reply_text("❌ Format galat hai. Aise bhejo: 800x600")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\nSahi format: 800x600")
            return
    
    # Agar normal text hai
    if update.message.text.lower() in ["resize", "rezige", "compress", "pdf"]:
        await update.message.reply_text("Bhai photo ke saath bhejo, ya pehle photo bhejo fir button dabao 😉")

def remove_bg_func(image_bytes):
    try:
        from rembg import remove
        input_image = Image.open(io.BytesIO(image_bytes))
        output_image = remove(input_image)
        return output_image
    except Exception as e:
        print(f"rembg error: {e}")
        return None

def add_watermark_func(image_bytes, text="PiciBaba.Org"):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        
        # Font size image ke hisab se
        font_size = max(20, image.size[0] // 20)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Bottom Right me watermark
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2]-bbox[0]
        text_h = bbox[3]-bbox[1]
        x = image.size[0] - text_w - 20
        y = image.size[1] - text_h - 20
        
        # Semi-transparent background for watermark
        draw.rectangle([x-10, y-5, x+text_w+10, y+text_h+5], fill=(0,0,0,100))
        draw.text((x, y), text, font=font, fill=(255,255,255,200))
        
        combined = Image.alpha_composite(image, overlay)
        return combined.convert("RGB")
    except Exception as e:
        print(f"watermark error: {e}")
        return Image.open(io.BytesIO(image_bytes))

def ocr_func(image_bytes):
    try:
        import pytesseract
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='eng+hin')
        return text if text.strip() else "Koi text nahi mila photo me."
    except Exception as e:
        # Fallback if tesseract not installed
        return f"OCR ke liye Render me Tesseract install karna padega. Error: {e}\n\nTip: Render > Settings > Dockerfile use karo ya phir easyocr use karenge next version me."

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in user_photos:
        await query.edit_message_text("Pehle ek photo bhejo.")
        return

    file_bytes = user_photos[user_id]
    image = Image.open(io.BytesIO(file_bytes))
    
    try:
        buf = io.BytesIO()
        
        if query.data == "bg_remove":
            await query.edit_message_text("✂️ BG hata raha hu... 10 sec lagega AI ko")
            result = remove_bg_func(file_bytes)
            if result:
                result.save(buf, "PNG")
                buf.seek(0)
                await context.bot.send_document(chat_id=query.message.chat_id, document=buf, filename="no_bg.png", caption="✅ BG Removed - Transparent PNG")
                await query.edit_message_text("✅ Done!")
            else:
                await query.edit_message_text("❌ rembg install nahi hai. requirements.txt check karo.")
            return

        elif query.data == "watermark":
            await query.edit_message_text("💧 Watermark laga raha hu...")
            watermarked = add_watermark_func(file_bytes, "PiciBaba.Org")
            watermarked.save(buf, "JPEG")
            buf.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption="✅ Watermark lag gaya - PiciBaba.Org")
            await query.message.delete()

        elif query.data == "ocr":
            await query.edit_message_text("🔤 Photo se text nikal raha hu...")
            text = ocr_func(file_bytes)
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"📝 Photo ka Text:\n\n{text}\n\n---\n✅ OCR Done")
            await query.edit_message_text("✅ Text upar bhej diya!")

        elif query.data == "custom_resize":
            user_state[user_id] = "awaiting_size"
            await query.edit_message_text("📏 Custom Resize\n\nAapko kaunsa size chahiye? Aise type karo:\n\n`800x600`\n`1080x1080` - Instagram ke liye\n`1280x720` - YouTube ke liye\n\nNeeche message me bhejo:", parse_mode="Markdown")

        elif query.data == "resize_menu":
            kb = [[InlineKeyboardButton("50% Chota", callback_data="resize_50"), InlineKeyboardButton("25% Chota", callback_data="resize_25")],
                  [InlineKeyboardButton("2x Bada", callback_data="resize_200")]]
            await query.edit_message_text("Quick Resize:", reply_markup=InlineKeyboardMarkup(kb))
            return

        elif query.data.startswith("resize_"):
            percent = int(query.data.split("_")[1])
            w,h = image.size
            new_size = (w*percent//100, h*percent//100)
            resized = image.resize(new_size)
            resized.save(buf, "PNG")
            buf.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption=f"✅ Resized {percent}%")
            await query.message.delete()

        elif query.data == "pdf":
            if image.mode == 'RGBA': image = image.convert('RGB')
            image.save(buf, "PDF")
            buf.seek(0)
            await context.bot.send_document(chat_id=query.message.chat_id, document=buf, filename="converted.pdf")
            await query.edit_message_text("✅ PDF ready!")

        elif query.data == "compress":
            image.save(buf, "JPEG", quality=40, optimize=True)
            buf.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption="✅ Compressed 60%")
            await query.message.delete()

        elif query.data == "to_jpg":
            if image.mode in ("RGBA","P"): image = image.convert("RGB")
            image.save(buf, "JPEG")
            buf.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption="✅ JPG")
            await query.message.delete()

        elif query.data == "rotate":
            rotated = image.rotate(90, expand=True)
            rotated.save(buf, "PNG")
            buf.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=buf, caption="✅ Rotated 90°")
            await query.message.delete()

    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Error: {e}")

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_click))
    print("Bot Level 1 Pack Started")
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    if BOT_TOKEN:
        run_bot()
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
