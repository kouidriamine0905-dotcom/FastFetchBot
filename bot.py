import os
import uuid
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)

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
        api_res = requests.post(
            "https://cobalt-api.koyeb.app/",
            json={"url": url},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=10
        )
        
        if api_res.status_code != 200:
            api_res = requests.post(
                "https://api.cobalt.tools/",
                json={"url": url},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )

        data = api_res.json()
        
        if data.get("status") in ["error", "rate-limit"]:
            raise Exception("تعذر معالجة الرابط عبر السيرفر الوسيط.")

        link_id = str(uuid.uuid4())[:8]
        user_urls[link_id] = {
            'url': url,
            'download_url': data.get('url')
        }

        keyboard = [
            [
                InlineKeyboardButton("🎬 تحميل الفيديو (MP4)", callback_data=f"dl|video|{link_id}"),
                InlineKeyboardButton("🎵 تحميل الصوت (MP3)", callback_data=f"dl|audio|{link_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text("📌 **تم العثور على المقطع بنجاح!**\n\nاختر الصيغة المطلوبة للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ تعذر استخراج بيانات الرابط. يرجى المحاولة لاحقاً.\nالسبب: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    mode = data[1]
    link_id = data[2]

    item = user_urls.get(link_id)
    if not item:
        await query.edit_message_text("❌ انتهت صلاحية الرابط، يرجى إعادة إرساله.")
        return

    await query.edit_message_text("⏳ جاري التحميل والمعالجة...")

    try:
        payload = {"url": item['url']}
        if mode == "audio":
            payload["downloadMode"] = "audio"
            payload["audioFormat"] = "mp3"

        res = requests.post(
            "https://api.cobalt.tools/",
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30
        ).json()

        dl_link = res.get("url")
        if not dl_link:
            raise Exception("لم يتم توليد رابط التحميل المباشر.")

        await query.edit_message_text("📤 جاري رفع الملف إلى تيليغرام...")

        file_res = requests.get(dl_link, stream=True)
        filename = f"file_{link_id}.{'mp3' if mode == 'audio' else 'mp4'}"

        with open(filename, 'wb') as f:
            for chunk in file_res.iter_content(chunk_size=8192):
                f.write(chunk)

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
