import os
import uuid
import threading
import sqlite3
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

# --- إحصائيات البوت (قاعدة بيانات خفيفة وسريعة) ---
def init_db():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY, downloads INTEGER)')
    c.execute('INSERT OR IGNORE INTO stats (id, downloads) VALUES (1, 0)')
    conn.commit()
    conn.close()

def track_user(user_id):
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def increment_downloads():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('UPDATE stats SET downloads = downloads + 1 WHERE id = 1')
    conn.commit()
    conn.close()

def get_bot_stats():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users_count = c.fetchone()[0]
    c.execute('SELECT downloads FROM stats WHERE id = 1')
    row = c.fetchone()
    downloads_count = row[0] if row else 0
    conn.close()
    return users_count, downloads_count

# تهيئة القاعدة عند بدء التشغيل
init_db()
# ------------------------------------------------

# إعدادات yt-dlp لتخطي حماية تيكتوك وإنستغرام وفيسبوك
YTDL_BASE_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 25,
    'geo_bypass': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    track_user(user_id)
    
    welcome_text = (
        "✨ **أهلاً بك في FastFetch Bot!** 🚀\n\n"
        "📥 أرسل لي رابطاً من (تيكتوك، إنستغرام، فيسبوك...) وسأقوم بتحميله فيديو أو صوت MP3 فوراً."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users, downloads = get_bot_stats()
    stats_text = (
        "📊 **إحصائيات البوت الحالية:**\n\n"
        f"👥 **عدد المستخدمين الكلي:** `{users}`\n"
        f"📥 **عدد التحميلات الناجحة:** `{downloads}`"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    track_user(user_id)  # تسجيل المستخدم تلقائياً

    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text("❌ عذراً، يوتيوب متوقف حالياً. البوت يدعم تيكتوك، إنستغرام، وفيسبوك.")
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
                InlineKeyboardButton("🎵 تحميل الصوت (MP3)", callback_data=f"dl|audio|{link_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(f"📌 **العنوان:** {title[:50]}\n\nاختر الصيغة المطلوبة للتحميل:", reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ تعذر استخراج بيانات الرابط، تأكد أنه عام وليس خاصاً.")

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
    filename = None

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
                'format': 'best/best',
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

        # تسجيل عملية تحميل ناجحة في قاعدة البيانات
        increment_downloads()

        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل أو الرفع.")
    
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))  # أمر عرض الإحصائيات
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
