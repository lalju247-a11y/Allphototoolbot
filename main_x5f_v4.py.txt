import os, io
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "8948498198:AAF_K6r_cUEPTRn0FsBXe6rlrESIKrzbvBA")
user_photos = {}
user_data = {}

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤍 BG White", callback_data="bg_white"), InlineKeyboardButton("🖼️ BG Blur", callback_data="bg_blur")],
        [InlineKeyboardButton("📸 PASSPORT SIZE MAKER", callback_data="passport_menu")],
        [InlineKeyboardButton("🗜️ Low Compress", callback_data="compress_low"), InlineKeyboardButton("🗜️ Med Compress", callback_data="compress_med")],
        [InlineKeyboardButton("📏 512x512", callback_data="resize_512"), InlineKeyboardButton("📏 1024", callback_data="resize_1024"), InlineKeyboardButton("📏 1080 Insta", callback_data="resize_1080")],
        [InlineKeyboardButton("🔄 JPG", callback_data="to_jpg"), InlineKeyboardButton("🔄 PNG", callback_data="to_png"), InlineKeyboardButton("🔄 WEBP", callback_data="to_webp"), InlineKeyboardButton("📄 PDF", callback_data="to_pdf")],
        [InlineKeyboardButton("🎨 Gray", callback_data="gray"), InlineKeyboardButton("✨ Enhance", callback_data="enhance"), InlineKeyboardButton("🌫️ Blur", callback_data="blur")],
        [InlineKeyboardButton("↩️ Rotate", callback_data="rotate"), InlineKeyboardButton("↔️ Flip", callback_data="flip"), InlineKeyboardButton("⬜ Square", callback_data="square")],
        [InlineKeyboardButton("⭕ Circle DP", callback_data="circle"), InlineKeyboardButton("🔳 Border", callback_data="border"), InlineKeyboardButton("💧 Text WM", callback_data="watermark")],
    ])

def passport_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇳 Indian Passport 35x45mm", callback_data="pp_35x45")],
        [InlineKeyboardButton("🇺🇸 US Passport 2x2 inch (51x51mm)", callback_data="pp_2x2")],
        [InlineKeyboardButton("🪪 1 inch - 25x35mm", callback_data="pp_25x35")],
        [InlineKeyboardButton("🖨️ 4x6 Sheet - 8 Photos", callback_data="pp_sheet_8")],
        [InlineKeyboardButton("🖨️ 4x6 Sheet - 6 Photos US", callback_data="pp_sheet_6")],
        [InlineKeyboardButton("🔙 Back to Main Tools", callback_data="back_main")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **All Photo Tool Bot V4** 🔥\n\n"
        "✅ 2-Photo wale 10 features hata diye\n"
        "✅ **NEW: Passport Size Maker Added**\n\n"
        "**Tools:**\n"
        "• Passport Photo Maker (35x45, 2x2, 25x35, 4x6 Sheet)\n"
        "• BG White/Blur, Compress, Resize, Convert, Gray, Enhance, Blur, Rotate, Flip, Square, Circle, Border, Watermark\n\n"
        "Photo bhejo 👇"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_photos[uid] = update.message.photo[-1].file_id
    await update.message.reply_text("Photo mil gayi ✅ Kya karna hai?", reply_markup=main_keyboard())

async def get_img(context, fid):
    f = await context.bot.get_file(fid)
    bio = io.BytesIO()
    await f.download_to_memory(bio)
    bio.seek(0)
    return Image.open(bio).convert("RGBA")

def create_passport(img, mm_w, mm_h, dpi=300):
    # mm to pixels: px = mm * dpi / 25.4
    px_w = int(mm_w * dpi / 25.4)
    px_h = int(mm_h * dpi / 25.4)
    # smart crop - center face area (crop to aspect ratio)
    target_ratio = px_w / px_h
    w, h = img.size
    current_ratio = w / h
    if current_ratio > target_ratio:
        # crop width
        new_w = int(h * target_ratio)
        left = (w - new_w)//2
        img = img.crop((left, 0, left+new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h)//3  # face slightly up
        img = img.crop((0, top, w, top+new_h))
    # resize to passport size
    img = img.resize((px_w, px_h), Image.LANCZOS)
    # add white BG if needed
    bg = Image.new("RGB", (px_w, px_h), (255,255,255))
    bg.paste(img, mask=img.split()[3] if img.mode=='RGBA' else None)
    return bg, px_w, px_h

def create_sheet(passport_img, sheet_w_mm=152, sheet_h_mm=102, dpi=300): # 6x4 inch = 152x102 mm
    sheet_px_w = int(sheet_w_mm * dpi / 25.4)
    sheet_px_h = int(sheet_h_mm * dpi / 25.4)
    sheet = Image.new("RGB", (sheet_px_w, sheet_px_h), (255,255,255))
    # layout
    gap = 10
    x, y = gap, gap
    count=0
    while y + passport_img.height + gap <= sheet_px_h:
        x = gap
        while x + passport_img.width + gap <= sheet_px_w:
            sheet.paste(passport_img, (x,y))
            x += passport_img.width + gap
            count+=1
        y += passport_img.height + gap
    return sheet, count

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    action = q.data

    if uid not in user_photos:
        await q.edit_message_text("Pehle photo bhejo 🙏")
        return

    if action == "passport_menu":
        await q.edit_message_text("📸 **Passport Size Maker** - Size choose karo:", reply_markup=passport_keyboard())
        return
    if action == "back_main":
        await q.edit_message_text("Main tools:", reply_markup=main_keyboard())
        return

    await q.edit_message_text(f"⏳ {action} processing...")

    img = await get_img(context, user_photos[uid])
    out = io.BytesIO()
    name = "output.jpg"

    try:
        if action == "bg_white":
            bg = Image.new("RGBA", img.size, (255,255,255,255))
            bg.paste(img, (0,0), img)
            bg.convert("RGB").save(out, "JPEG"); name="bg_white.jpg"
        elif action == "bg_blur":
            bg = img.copy().filter(ImageFilter.GaussianBlur(20))
            bg.paste(img, (0,0), img)
            bg.convert("RGB").save(out, "JPEG"); name="bg_blur.jpg"
        elif action == "compress_low":
            img.convert("RGB").save(out, "JPEG", quality=15, optimize=True); name="low.jpg"
        elif action == "compress_med":
            img.convert("RGB").save(out, "JPEG", quality=60, optimize=True); name="med.jpg"
        elif action.startswith("resize_"):
            s=int(action.split("_")[1]); img.resize((s,s), Image.LANCZOS).convert("RGB").save(out, "JPEG"); name=f"{s}.jpg"
        elif action == "to_jpg":
            img.convert("RGB").save(out, "JPEG"); name="to.jpg"
        elif action == "to_png":
            img.save(out, "PNG"); name="to.png"
        elif action == "to_webp":
            img.save(out, "WEBP"); name="to.webp"
        elif action == "to_pdf":
            img.convert("RGB").save(out, "PDF"); name="to.pdf"
        elif action == "gray":
            ImageOps.grayscale(img).convert("RGB").save(out, "JPEG"); name="gray.jpg"
        elif action == "enhance":
            ImageEnhance.Color(img).enhance(1.8).save(out, "JPEG"); name="enhanced.jpg"
        elif action == "blur":
            img.filter(ImageFilter.GaussianBlur(6)).save(out, "JPEG"); name="blur.jpg"
        elif action == "rotate":
            img.rotate(90, expand=True).save(out, "JPEG"); name="rotate.jpg"
        elif action == "flip":
            ImageOps.mirror(img).save(out, "JPEG"); name="flip.jpg"
        elif action == "square":
            w,h=img.size; side=min(w,h); img.crop(((w-side)//2,(h-side)//2,(w+side)//2,(h+side)//2)).save(out, "JPEG"); name="square.jpg"
        elif action == "circle":
            size=min(img.size); mask=Image.new('L',(size,size),0); ImageDraw.Draw(mask).ellipse((0,0,size,size),fill=255)
            crop=img.crop(((img.width-size)//2,(img.height-size)//2,(img.width+size)//2,(img.height+size)//2))
            o=Image.new("RGBA",(size,size)); o.paste(crop,mask=mask); o.save(out,"PNG"); name="circle.png"
        elif action == "border":
            ImageOps.expand(img, border=40, fill='white').save(out,"JPEG"); name="border.jpg"
        elif action == "watermark":
            user_data.setdefault(uid,{})["await_wm"]=True
            await context.bot.send_message(chat_id=uid, text="Watermark text bhejo agle message me:")
            return
        # PASSPORT
        elif action == "pp_35x45":
            pp,_w,_h = create_passport(img, 35, 45)
            pp.save(out, "JPEG", quality=95, dpi=(300,300)); name="passport_35x45.jpg"
        elif action == "pp_2x2":
            pp,_w,_h = create_passport(img, 51, 51)
            pp.save(out, "JPEG", quality=95, dpi=(300,300)); name="passport_2x2.jpg"
        elif action == "pp_25x35":
            pp,_w,_h = create_passport(img, 25, 35)
            pp.save(out, "JPEG", quality=95, dpi=(300,300)); name="passport_25x35.jpg"
        elif action == "pp_sheet_8":
            pp,_w,_h = create_passport(img, 35, 45)
            sheet,count = create_sheet(pp, 152, 102)
            sheet.save(out, "JPEG", quality=95, dpi=(300,300)); name=f"passport_sheet_{count}photos_4x6.jpg"
        elif action == "pp_sheet_6":
            pp,_w,_h = create_passport(img, 51, 51)
            sheet,count = create_sheet(pp, 152, 102)
            sheet.save(out, "JPEG", quality=95, dpi=(300,300)); name=f"passport_sheet_{count}photos_4x6_US.jpg"

    except Exception as e:
        await context.bot.send_message(chat_id=uid, text=f"Error: {e}")
        return

    out.seek(0)
    await context.bot.send_document(chat_id=uid, document=out, filename=name)
    await context.bot.send_message(chat_id=uid, text="✅ Ho gaya! Passport bhi ban gaya. Aur kya karna hai?", reply_markup=main_keyboard() if "pp_" not in action else passport_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if user_data.get(uid, {}).get("await_wm"):
        txt = update.message.text
        user_data[uid]["await_wm"]=False
        img = await get_img(context, user_photos[uid])
        draw_img = img.convert("RGBA")
        draw = ImageDraw.Draw(draw_img)
        try: font=ImageFont.truetype("arial.ttf", 50)
        except: font=ImageFont.load_default()
        draw.text((20, draw_img.height-70), txt, fill=(255,255,255,180), font=font, stroke_width=3, stroke_fill=(0,0,0))
        out=io.BytesIO(); draw_img.convert("RGB").save(out,"JPEG"); out.seek(0)
        await context.bot.send_document(chat_id=uid, document=out, filename="watermark.jpg")
        await context.bot.send_message(chat_id=uid, text="WM Done ✅", reply_markup=main_keyboard())
        return

if __name__=="__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_click))
    print("V4 Bot ON - Passport Maker")
    app.run_polling()
