import os
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)
from yt_dlp import YoutubeDL

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://fastfetchbot.onrender.com")

web_app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()

# إعدادات خاصة لـ yt-dlp تتخطى الحماية وتدعم تيكتوك، إنستغرام، وفيسبوك
YTDL_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 30,
    'geo_bypass': True,
    'format': 'best/best',
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في بوت التحميل السريع!** 🚀\n\n"
        "📥 أرسل لي رابطاً من:\n"
        "• 🎥 **TikTok**\n"
        "• 📸 **Instagram**\n"
        "• 📘 **Facebook**\n\n"
        "وسأقوم بتجهيز رابط التحميل لك فوراً!"
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

    # منع يوتيوب بشكل نهائي وتنبيه المستخدم
    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text("❌ عذراً، خدمة يوتيوب متوقفة حالياً. البوت يدعم TikTok, Instagram, و Facebook فقط.")
        return

    msg = await update.message.reply_text("🔍 جاري معالجة الرابط واستخراج الفيديو...")

    try:
        with YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            
            title = info.get('title', 'مقطع فيديو')
            direct_url = info.get('url')

        if direct_url:
            keyboard = [[InlineKeyboardButton("📥 تحميل الفيديو مباشرة", url=direct_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await msg.edit_text(f"📌 **{title[:40]}...**\n\n✅ تم تجهيز الرابط بنجاح:", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await msg.edit_text("❌ تعذر العثور على رابط التحميل المباشر لهذا الرابط.")

    except Exception as e:
        await msg.edit_text("❌ عذراً، هذا الرابط خاص أو غير مدعوم حالياً.")

# تسجيل الهاندلرز
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT, handle_link))

@web_app.route('/')
def home():
    return "FastFetch Webhook Bot (TikTok, Insta, FB) is running 24/7!"

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
