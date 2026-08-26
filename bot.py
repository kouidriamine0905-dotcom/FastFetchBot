import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)
from yt_dlp import YoutubeDL

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://fastfetchbot.onrender.com")

web_app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في بوت التحميل المباشر!** 🚀\n\n"
        "📥 أرسل لي رابطاً من **TikTok** أو **Instagram** أو **Facebook** وسأقوم بتحميل الفيديو وإرساله لك هنا فوراً!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    url = update.message.text.strip()
    if url.startswith("/"):
        return
        
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبدأ بـ http.")
        return

    # منع يوتيوب نهائياً بناءً على رغبتك
    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text("❌ عذراً، يوتيوب متوقف. البوت يدعم TikTok, Instagram, و Facebook فقط.")
        return

    msg = await update.message.reply_text("⏳ جاري تحميل الفيديو، طفلاً صغيراً...")

    file_path = None
    try:
        # إعدادات التحميل المباشر عبر yt-dlp
        output_template = "video_%s.mp4" % update.message.chat_id
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 50 * 1024 * 1024, # حد أقصى 50 ميجابايت لتناسب حدود تيليجرام المجانية
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        # التأكد من أن الملف تم تحميله بنجاح
        if file_path and os.path.exists(file_path):
            await msg.edit_text("📤 جاري رفع الفيديو وإرساله لك...")
            
            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="✅ تم التحميل بواسطة بوتك الخاص!"
                )
            
            # حذف الرسالة المؤقتة
            await msg.delete()
        else:
            await msg.edit_text("❌ تعذر تحميل هذا الفيديو، ربما يكون الحساب خاصاً أو الرابط غير مدعوم.")

    except Exception as e:
        await msg.edit_text("❌ حدث خطأ أثناء تحميل الفيديو. تأكد أن الرابط عام وليس خاصاً.")
    
    finally:
        # تنظيف وحذف الملف من السيرفر لتوفير المساحة
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

# تسجيل الهاندلرز
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT, handle_link))

@web_app.route('/')
def home():
    return "FastFetch Direct Download Bot is running 24/7!"

@web_app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        
        async def process():
            await telegram_app.initialize()
            await telegram_app.process_update(update)
            await telegram_app.shutdown()

        import asyncio
        asyncio.run(process())
    except Exception as e:
        print(f"Error: {e}")
        
    return 'OK', 200

if __name__ == '__main__':
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TOKEN}"
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
    
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)
