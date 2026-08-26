import os
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

TOKEN = "8729731201:AAEVEHKVGxKUs1psp2xPCeDlF8iEQdaJHa0"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://fastfetchbot.onrender.com")

web_app = Flask(__name__)

# تهيئة تطبيق تيليجرام
telegram_app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي أي رابط (يوتيوب، تيكتوك، إنستغرام، فيسبوك) وسأجلب لك رابط التحميل فوراً!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    url = update.message.text.strip()
    if url.startswith("/"):
        return
        
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري معالجة الرابط عبر السيرفر السريع...")

    try:
        # استخدام خدمة بديلة ومستقرة تماماً لجلب روابط الميديا
        api_url = f"https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "vQuality": "720"
        }

        response = requests.post(api_url, json=payload, headers=headers, timeout=20)
        res_data = response.json()

        status = res_data.get("status")

        if status == "stream" or status == "redirect":
            download_url = res_data.get("url")
            keyboard = [[InlineKeyboardButton("📥 تحميل الملف مباشرة", url=download_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await msg.edit_text("✅ **تم تجهيز رابط التحميل بنجاح!**\nاضغط على الزر أدناه للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')
            
        elif status == "picker":
            # في حال وجود أكثر من خيار جودة أو صور متعددة
            picker_items = res_data.get("picker", [])
            if picker_items:
                download_url = picker_items[0].get("url")
                keyboard = [[InlineKeyboardButton("📥 تحميل الملف", url=download_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await msg.edit_text("✅ **تم تجهيز المقطع!** اضغط أدناه للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await msg.edit_text("❌ عذراً، لم نتمكن من استخراج رابط التحميل.")
        else:
            error_text = res_data.get("text", "تأكد أن الرابط عام وليس خاصاً.")
            await msg.edit_text(f"❌ تعذر التحميل: {error_text}")

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ في الاتصال بالخدمة. حاول مجدداً لاحقاً.")

# تسجيل الأوامر والرسائل
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT, handle_link))

@web_app.route('/')
def home():
    return "FastFetch Webhook Bot is running 24/7!"

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
        print(f"Error processing update: {e}")
        
    return 'OK', 200

if __name__ == '__main__':
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TOKEN}"
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
    
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)
