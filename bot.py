import os
import uuid
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from yt_dlp import YoutubeDL

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "FastFetch Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"
user_urls = {}

# إعدادات أساسية ومستقرة بدون تعديل الـ requirements
YTDL_BASE_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 30,
    'geo_bypass': True,
    'extractor_args': {
        'tiktok': {
            'api_hostname': 'api16-normal-c-useast1a.tiktokv.com'
        }
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط من تيكتوك أو إنستغرام وسأقوم بتحميله لك فوراً."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري جلب تفاصيل المقطع...")

    try:
        ydl_opts = YTDL_BASE_OPTIONS.copy()
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            title = info.get('title', 'مقطع فيديو')

        link_id = str(uuid.uuid4())[:8]
        user_urls[link_id] = url

        keyboard = [
            [
                InlineKeyboardButton("🎬 تحميل الفيديو (MP4)", callback_data=f"dl|video|{link_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(f"📌 **العنوان:** {title[:50]}...\n\nاختر الصيغة المطلوبة للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ تعذر استخراج بيانات الرابط: تأكد أن الرابط عام.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    link_id = data[2]

    url = user_urls.get(link_id)
    if not url:
        await query.edit_message_text("❌ انتهت صلاحية الرابط، يرجى إعادة إرساله.")
        return

    await query.edit_message_text("⏳ جاري التحميل والمعالجة...")

    out_file = f"download_{link_id}"

    try:
        ydl_opts = YTDL_BASE_OPTIONS.copy()
        ydl_opts.update({
            'format': 'best/best',
            'outtmpl': f'{out_file}.%(ext)s',
        })
            
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await query.edit_message_text("📤 جاري رفع الفيديو إلى تيليغرام...")

        with open(filename, 'rb') as file_to_send:
            await context.bot.send_video(chat_id=query.message.chat_id, video=file_to_send)

        if os.path.exists(filename):
            os.remove(filename)
        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل.")

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.run_polling()

if __name__ == '__main__':
    main()
