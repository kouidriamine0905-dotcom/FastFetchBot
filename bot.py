import os
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes
)

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "FastFetch Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط (يوتيوب، تيكتوك، إنستغرام، فيسبوك) وسأجلب لك رابط التحميل فوراً!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري معالجة الرابط عبر السيرفر السريع...")

    try:
        api_url = "https://coapi.it/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {"url": url}

        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        res_data = response.json()

        status = res_data.get("status")

        if status == "redirect" or status == "stream":
            download_url = res_data.get("url")
            keyboard = [[InlineKeyboardButton("📥 تحميل الملف مباشرة", url=download_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await msg.edit_text("✅ **تم تجهيز رابط التحميل بنجاح!**\nاضغط على الزر أدناه للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')
            
        elif status == "picker":
            choices = res_data.get("picker", [])
            if choices:
                download_url = choices[0].get("url")
                keyboard = [[InlineKeyboardButton("📥 تحميل الملف", url=download_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await msg.edit_text("✅ **تم تجهيز المقطع!** اضغط أدناه للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await msg.edit_text("❌ عذراً، لم نتمكن من العثور على رابط مباشر لهذا الملف.")
        else:
            await msg.edit_text("❌ تعذر تحميل هذا الرابط، تأكد أنه عام وليس خاصاً.")

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ في الاتصال بالخدمة. حاول مجدداً لاحقاً.")

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    app.run_polling()

if __name__ == '__main__':
    main()
