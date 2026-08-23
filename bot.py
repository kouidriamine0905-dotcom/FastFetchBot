import os
import uuid
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from pytubefix import YouTube

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "FastFetch Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"
user_urls = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط فيديو أو صوت من يوتيوب، وسأقوم بتحميله لك فوراً بأعلى جودة ممكّنة."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري جلب تفاصيل المقطع...")

    try:
        # استخدام عميل 'WEB' أو 'MWEB' للالتفاف على حظر البوتات
        yt = YouTube(url, client='MWEB')
        title = yt.title

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

    try:
        yt = YouTube(url, client='MWEB')
        filename = f"file_{link_id}"

        if mode == "audio":
            stream = yt.streams.filter(only_audio=True).first()
            out_path = stream.download(filename=f"{filename}.mp3")
        else:
            stream = yt.streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()
            if not stream:
                stream = yt.streams.filter(file_extension='mp4').first()
            out_path = stream.download(filename=f"{filename}.mp4")

        await query.edit_message_text("📤 جاري رفع الملف إلى تيليغرام...")

        with open(out_path, 'rb') as file_to_send:
            if mode == "audio":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file_to_send)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=file_to_send)

        if os.path.exists(out_path):
            os.remove(out_path)
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
