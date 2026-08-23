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

# الخلطة السحرية لتجاوز حظر يوتيوب عبر محاكي أندرويد موثوق
YTDL_BASE_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android'],
        }
    },
    'socket_timeout': 15,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط (يوتيوب، تيكتوك، إنستغرام...) وسأقوم بتحميله فيديو أو صوت MP3 فوراً."
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
            title = info.get('title', 'مقطع فيديو')

        link_id = str(uuid.uuid4())[:8]
        user_urls[link_id] = url

        keyboard = [
            [
                InlineKeyboardButton("🎬 تحميل الفيديو (MP4)", callback_data=f"dl|video|{link_id}"),
                InlineKeyboardButton("🎵 تحميل الصوت (MP3)", callback_data=f"dl|audio|{link_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(f"📌 **العنوان:** {title}\n\nاختر الصيغة المطلوبة للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ تعذر استخراج بيانات الرابط: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    mode = data[1]
    link_id = data[2]

    url = user_urls.get(link_id)
    if not url:
        await query.edit_message_text("❌ انتهت صلاحية الرابط، يرجى إعادة إرساله.")
        return

    await query.edit_message_text("⏳ جاري التحميل والمعالجة...")

    out_file = f"download_{link_id}"

    try:
        ydl_opts = YTDL_BASE_OPTIONS.copy()
        
        if mode == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'outtmpl': f'{out_file}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
                'outtmpl': f'{out_file}.%(ext)s',
            })
            
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "audio" and not filename.endswith(".mp3"):
                filename = os.path.splitext(filename)[0] + ".mp3"

        await query.edit_message_text("📤 جاري رفع الملف إلى تيليغرام...")

        with open(filename, 'rb') as file_to_send:
            if mode == "audio":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file_to_send)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=file_to_send)

        if os.path.exists(filename):
            os.remove(filename)
        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {str(e)}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.run_polling()

if __name__ == '__main__':
    main()
