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

# إعدادات لتجاوز حظر يوتيوب عبر التخفي كـ Android/iOS client
COMMON_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios']
        }
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط فيديو أو صوت من يوتيوب، وسأقوم بتحميله لك فوراً بأعلى جودة ممكّنة."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري جلب تفاصيل المقطع...")

    try:
        ydl_opts = dict(COMMON_YDL_OPTS)
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'مقطع فيديو')

        link_id = str(uuid.uuid4())[:8]
        user_urls[link_id] = url

        keyboard = [
            [
                InlineKeyboardButton("🎬 1080p", callback_data=f"dl|1080|{link_id}"),
                InlineKeyboardButton("🎬 720p", callback_data=f"dl|720|{link_id}"),
            ],
            [
                InlineKeyboardButton("🎬 480p/360p", callback_data=f"dl|best|{link_id}"),
                InlineKeyboardButton("🎵 صوت MP3", callback_data=f"dl|mp3|{link_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(f"📌 **العنوان:** {title}\n\nاختر صيغة/جودة التحميل المطلوب:", reply_markup=reply_markup, parse_mode='Markdown')

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

    if mode == "mp3":
        ydl_opts = {
            **COMMON_YDL_OPTS,
            'format': 'bestaudio/best',
            'outtmpl': f'{out_file}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'max_filesize': 50 * 1024 * 1024,
        }
    else:
        fmt_str = f'bestvideo[height<={mode}][ext=mp4]+bestaudio[ext=m4a]/best[height<={mode}][ext=mp4]/best' if mode != 'best' else 'best[ext=mp4]/best'
        ydl_opts = {
            **COMMON_YDL_OPTS,
            'format': fmt_str,
            'outtmpl': f'{out_file}.%(ext)s',
            'max_filesize': 50 * 1024 * 1024,
        }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "mp3":
                filename = os.path.splitext(filename)[0] + ".mp3"

        await query.edit_message_text("📤 جاري رفع الملف إلى تيليغرام...")

        with open(filename, 'rb') as file_to_send:
            if mode == "mp3":
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
    
