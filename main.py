import os
import io
import logging
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
from rembg import remove, new_session
import fitz  # PyMuPDF
import pytesseract

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Global session - load once, fast
REMBG_SESSION = new_session("u2net_human_seg")  # small & fast for humans, good for all

# Lock for each user - puzzle fix
USER_LOCKS = {}

def resize_for_ai(image: Image.Image, max_size=1024):
    """Resize to max 1024 for speed, keep quality"""
    w, h = image.size
    if max(w, h) > max_size:
        if w > h:
            new_w = max_size
            new_h = int(h * (max_size / w))
        else:
            new_h = max_size
            new_w = int(w * (max_size / h))
        image = image.resize((new_w, new_h), Image.LANCZOS)
    return image

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("✂️ BG Remove", callback_data="bg_remove"),
         InlineKeyboardButton("🎨 BG Color", callback_data="bg_color_white")],
        [InlineKeyboardButton("💧 Watermark", callback_data="watermark"),
         InlineKeyboardButton("🔤 OCR", callback_data="ocr")],
        [InlineKeyboardButton("📐 Custom Resize", callback_data="custom_resize")],
        [InlineKeyboardButton("🚀 LEVEL 2 (Pro)", callback_data="level2")],
        [InlineKeyboardButton("🤖 LEVEL 3 (AI Viral)", callback_data="level3")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **All Photo Tools PRO MAX LIVE Hai!**\n\n"
        "LEVEL 1 (Basic)\n"
        "✂️ BG Remove | 💧 Watermark | 🔤 OCR | 📐 Custom Resize\n\n"
        "🚀 LEVEL 2 (Pro)\n"
        "📇 Passport Photo | 📄 PDF to Image | 📚 Merge PDF | ◼️ Insta Grid\n\n"
        "🤖 LEVEL 3 (AI Viral)\n"
        "✨ HD Upscale | 📝 AI Caption | 🎨 Background Color\n\n"
        "Bas ek Photo / PDF bhejo!",
        reply_markup=get_main_menu()
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if USER_LOCKS.get(user_id):
        await update.message.reply_text("⏳ Ek kaam chal raha hai... 10 sec ruko fir bhejo! 🙏")
        return

    photo_file = await update.message.photo[-1].get_file()
    bio = io.BytesIO()
    await photo_file.download_to_memory(out=bio)
    bio.seek(0)
    context.user_data['last_photo'] = bio.getvalue()
    
    await update.message.reply_text(
        "📸 Photo mil gaya! Feature select karo:",
        reply_markup=get_main_menu()
    )

async def handle_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    bio = io.BytesIO()
    file = await doc.get_file()
    await file.download_to_memory(out=bio)
    bio.seek(0)
    context.user_data['last_doc'] = bio.getvalue()
    context.user_data['last_doc_name'] = doc.file_name
    await update.message.reply_text("📄 File mil gaya! Feature select karo:", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if USER_LOCKS.get(user_id):
        await query.edit_message_text("⏳ Pehle wala kaam ho raha hai... 10 sec ruko!")
        return

    USER_LOCKS[user_id] = True
    data = query.data
    
    try:
        if 'last_photo' not in context.user_data and data not in ['level2','level3']:
            await query.edit_message_text("Pehle ek photo bhejo bhai!")
            USER_LOCKS[user_id] = False
            return

        if data == "level2":
            kb = [
                [InlineKeyboardButton("📇 Passport Photo", callback_data="passport"),
                 InlineKeyboardButton("📄 PDF to Image", callback_data="pdf_to_img")],
                [InlineKeyboardButton("📚 Merge PDF", callback_data="merge_pdf"),
                 InlineKeyboardButton("◼️ Insta Grid", callback_data="insta_grid")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")]
            ]
            await query.edit_message_text("🚀 LEVEL 2 (Pro) Features:", reply_markup=InlineKeyboardMarkup(kb))
            USER_LOCKS[user_id] = False
            return
            
        if data == "level3":
            kb = [
                [InlineKeyboardButton("✨ HD Upscale 2x", callback_data="upscale")],
                [InlineKeyboardButton("📝 AI Caption", callback_data="ai_caption")],
                [InlineKeyboardButton("🎨 BG Color - White", callback_data="bg_color_white"),
                 InlineKeyboardButton("🔵 Blue", callback_data="bg_color_blue"),
                 InlineKeyboardButton("🔴 Red", callback_data="bg_color_red")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")]
            ]
            await query.edit_message_text("🤖 LEVEL 3 (AI Viral):", reply_markup=InlineKeyboardMarkup(kb))
            USER_LOCKS[user_id] = False
            return
            
        if data == "back":
            await query.edit_message_text("Bas ek Photo / PDF bhejo!", reply_markup=get_main_menu())
            USER_LOCKS[user_id] = False
            return

        img_bytes = context.user_data.get('last_photo')
        if not img_bytes:
            await query.edit_message_text("Photo expire ho gaya, dubara bhejo!")
            USER_LOCKS[user_id] = False
            return

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        
        if data in ["bg_remove", "bg_color_white", "bg_color_blue", "bg_color_red", "passport"]:
            await query.edit_message_text(f"✂️ BG hata raha hu... 10-12 sec lagega (FAST MODE) ⏳")
            img_small = resize_for_ai(img, 1024)
            no_bg = remove(img_small, session=REMBG_SESSION)
            if img.size != img_small.size:
                no_bg = no_bg.resize(img.size, Image.LANCZOS)

            if data == "bg_remove":
                out_bio = io.BytesIO()
                no_bg.save(out_bio, format="PNG")
                out_bio.seek(0)
                await context.bot.send_document(chat_id=query.message.chat_id, document=out_bio, filename="no_bg.png", caption="✅ BG Remove Done - FAST!")
                await query.delete_message()

            elif data.startswith("bg_color"):
                color_map = {"bg_color_white": (255,255,255), "bg_color_blue": (0,120,255), "bg_color_red": (255,50,50)}
                bg_color = color_map.get(data, (255,255,255))
                bg = Image.new("RGBA", no_bg.size, bg_color + (255,))
                final = Image.alpha_composite(bg, no_bg).convert("RGB")
                out_bio = io.BytesIO()
                final.save(out_bio, format="JPEG", quality=92)
                out_bio.seek(0)
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=out_bio, caption=f"✅ BG Color Done!")
                await query.delete_message()

            elif data == "passport":
                bg = Image.new("RGBA", no_bg.size, (255,255,255,255))
                comp = Image.alpha_composite(bg, no_bg)
                final = comp.resize((350, 450))
                out_bio = io.BytesIO()
                final.convert("RGB").save(out_bio, format="JPEG", quality=95)
                out_bio.seek(0)
                await context.bot.send_document(chat_id=query.message.chat_id, document=out_bio, filename="passport.jpg", caption="✅ Passport Photo Ready!")
                await query.delete_message()

        elif data == "upscale":
            await query.edit_message_text("✨ HD kar raha hu... 5 sec ⏳")
            w, h = img.size
            upscaled = img.resize((w*2, h*2), Image.LANCZOS)
            enhancer = ImageEnhance.Sharpness(upscaled)
            upscaled = enhancer.enhance(1.5)
            out_bio = io.BytesIO()
            upscaled.convert("RGB").save(out_bio, format="JPEG", quality=92)
            out_bio.seek(0)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=out_bio, caption="✅ HD Upscale 2x Done!")
            await query.delete_message()

        elif data == "ocr":
            await query.edit_message_text("🔤 Text nikal raha hu... ⏳")
            text = pytesseract.image_to_string(img.convert("RGB"), lang="eng+hin")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"📝 OCR Result:\n\n{text[:4000] or 'Koi text nahi mila'}")

        else:
            await query.edit_message_text("Ye feature is fast version me jald aayega! BG Remove / BG Color / Upscale / OCR try karo.", reply_markup=get_main_menu())

    except Exception as e:
        logger.error(f"Error {data}: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Error aaya: {str(e)[:200]}\nDubara try karo, photo ka size chota karke bhejo.")
        try:
            await query.delete_message()
        except:
            pass
    finally:
        USER_LOCKS[user_id] = False

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_docs))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("FINAL BOT - FAST MODE Started")
    app.run_polling()

if __name__ == "__main__":
    main()
