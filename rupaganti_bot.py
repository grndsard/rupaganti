import os
import sqlite3
import zipfile
import threading
import time
import logging
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import telebot
from telebot import types
import mimetypes
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7650951465:AAF45TzccOAlDoSEqsOBd4lcHsxPGhMZEtE"
bot = telebot.TeleBot(BOT_TOKEN)

# Language translations
LANG = {
    'en': {
        'welcome': "🎉 Hi! I'm **RupaGanti** by Grands — I can help you convert or compress your files!\n\n✨ What I can do:\n📸 **Images**: JPG ↔ PNG ↔ WebP ↔ BMP\n📄 **Documents**: PDF compression\n🎵 **Audio**: MP3, WAV, FLAC\n🎬 **Video**: MP4, AVI, MOV\n🗜️ **Compress**: Reduce file size\n\nJust send me a file and I'll show you the options! 🚀",
        'file_received': 'received!\n\nChoose what you\'d like to do:',
        'convert_jpg': '📷 Convert to JPG',
        'convert_png': '🖼️ Convert to PNG',
        'convert_webp': '🌐 Convert to WebP',
        'compress_img': '🗜️ Compress Image',
        'compress_pdf': '🗜️ Compress PDF',
        'extract_mp3': '🎵 Extract Audio (MP3)',
        'zip_file': '📦 Compress to ZIP',
        'done': '✅ Done!',
        'complete': '🎁 This is what you\'ve been waiting for!',
        'help_more': '💬 Need anything else? I\'m here to help — just say the word!',
        'yes_more': '✅ Yes, Process Another',
        'no_thanks': '❌ No, Thanks!',
        'goodbye': '👋 Thanks for using RupaGanti! Type /start anytime to use me again.',
        'ready_next': '📁 Ready for your next file! Just send it to me.',
        'audio_failed': '❌ Audio extraction failed, but I\'m still here to help!'
    },
    'id': {
        'welcome': "🎉 Hai! Saya **RupaGanti** by Grands — saya bisa membantu mengkonversi atau mengompres file Anda!\n\n✨ Yang bisa saya lakukan:\n📸 **Gambar**: JPG ↔ PNG ↔ WebP ↔ BMP\n📄 **Dokumen**: Kompresi PDF\n🎵 **Audio**: MP3, WAV, FLAC\n🎬 **Video**: MP4, AVI, MOV\n🗜️ **Kompres**: Kurangi ukuran file\n\nKirim file dan saya akan tunjukkan pilihan! 🚀",
        'file_received': 'diterima!\n\nPilih yang ingin Anda lakukan:',
        'convert_jpg': '📷 Konversi ke JPG',
        'convert_png': '🖼️ Konversi ke PNG',
        'convert_webp': '🌐 Konversi ke WebP',
        'compress_img': '🗜️ Kompres Gambar',
        'compress_pdf': '🗜️ Kompres PDF',
        'extract_mp3': '🎵 Ekstrak Audio (MP3)',
        'zip_file': '📦 Kompres ke ZIP',
        'done': '✅ Selesai!',
        'complete': '🎁 Inilah yang sudah Anda tunggu!',
        'help_more': '💬 Butuh bantuan lagi? Saya siap membantu — tinggal bilang saja!',
        'yes_more': '✅ Ya, Proses Lagi',
        'no_thanks': '❌ Tidak, Terima Kasih!',
        'goodbye': '👋 Terima kasih telah menggunakan RupaGanti! Ketik /start kapan saja untuk menggunakan saya lagi.',
        'ready_next': '📁 Siap untuk file berikutnya! Kirim saja ke saya.',
        'audio_failed': '❌ Ekstraksi audio gagal, tapi saya masih di sini untuk membantu!'
    },
    'ar': {
        'welcome': "🎉 مرحبا! أنا **RupaGanti** من Grands — يمكنني مساعدتك في تحويل أو ضغط ملفاتك!\n\n✨ ما يمكنني فعله:\n📸 **الصور**: JPG ↔ PNG ↔ WebP ↔ BMP\n📄 **المستندات**: ضغط PDF\n🎵 **الصوت**: MP3, WAV, FLAC\n🎬 **الفيديو**: MP4, AVI, MOV\n🗜️ **الضغط**: تقليل حجم الملف\n\nأرسل لي ملفاً وسأعرض عليك الخيارات! 🚀",
        'file_received': 'تم الاستلام!\n\nاختر ما تريد فعله:',
        'convert_jpg': '📷 تحويل إلى JPG',
        'convert_png': '🖼️ تحويل إلى PNG',
        'convert_webp': '🌐 تحويل إلى WebP',
        'compress_img': '🗜️ ضغط الصورة',
        'compress_pdf': '🗜️ ضغط PDF',
        'extract_mp3': '🎵 استخراج الصوت (MP3)',
        'zip_file': '📦 ضغط إلى ZIP',
        'done': '✅ تم!',
        'complete': '🎁 هذا ما كنت تنتظره!',
        'help_more': '💬 تحتاج شيئاً آخر؟ أنا هنا للمساعدة — فقط قل كلمة!',
        'yes_more': '✅ نعم، معالجة أخرى',
        'no_thanks': '❌ لا، شكراً!',
        'goodbye': '👋 شكراً لاستخدام RupaGanti! اكتب /start في أي وقت لاستخدامي مرة أخرى.',
        'ready_next': '📁 جاهز لملفك التالي! أرسله لي فقط.',
        'audio_failed': '❌ فشل استخراج الصوت، لكنني ما زلت هنا للمساعدة!'
    },
    'jv': {
        'welcome': "🎉 Halo! Aku **RupaGanti** saka Grands — aku bisa ngewangi ngowahi utawa ngompres file sampeyan!\n\n✨ Sing bisa tak lakoni:\n📸 **Gambar**: JPG ↔ PNG ↔ WebP ↔ BMP\n📄 **Dokumen**: Kompresi PDF\n🎵 **Audio**: MP3, WAV, FLAC\n🎬 **Video**: MP4, AVI, MOV\n🗜️ **Kompres**: Ngurangi ukuran file\n\nKirimno file lan tak tuduhno pilihane! 🚀",
        'file_received': 'wis ditampa!\n\nPilih sing arep dilakoni:',
        'convert_jpg': '📷 Owahi dadi JPG',
        'convert_png': '🖼️ Owahi dadi PNG',
        'convert_webp': '🌐 Owahi dadi WebP',
        'compress_img': '🗜️ Kompres Gambar',
        'compress_pdf': '🗜️ Kompres PDF',
        'extract_mp3': '🎵 Jupuk Audio (MP3)',
        'zip_file': '📦 Kompres dadi ZIP',
        'done': '✅ Rampung!',
        'complete': '🎁 Iki sing wis kokenteni!',
        'help_more': '💬 Butuh apa maneh? Aku kene kanggo ngewangi — cukup kandha wae!',
        'yes_more': '✅ Ya, Proses Maneh',
        'no_thanks': '❌ Ora, Matur Nuwun!',
        'goodbye': '👋 Matur nuwun wis nggunakake RupaGanti! Ketik /start kapan wae kanggo nggunakake aku maneh.',
        'ready_next': '📁 Siap kanggo file sabanjure! Kirimno wae marang aku.',
        'audio_failed': '❌ Ekstraksi audio gagal, nanging aku isih kene kanggo ngewangi!'
    }
}

def get_user_lang(lang_code):
    if lang_code and lang_code.startswith('id'):
        return 'id'
    elif lang_code and lang_code.startswith('ar'):
        return 'ar'
    elif lang_code and lang_code.startswith('jv'):
        return 'jv'
    return 'en'

os.makedirs("files", exist_ok=True)
os.makedirs("temp", exist_ok=True)

def init_db():
    conn = sqlite3.connect('files.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS files
                    (id INTEGER PRIMARY KEY, user_id INTEGER, file_id TEXT, 
                     file_name TEXT, file_path TEXT, created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def get_file_type(filename):
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    types = {
        'image': ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif', 'tiff'],
        'document': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
        'video': ['mp4', 'avi', 'mov', 'mkv', 'wmv'],
        'audio': ['mp3', 'wav', 'flac', 'aac', 'm4a']
    }
    for category, extensions in types.items():
        if ext in extensions:
            return category, ext
    return 'other', ext

def cleanup_files():
    while True:
        try:
            conn = sqlite3.connect('files.db')
            cutoff = datetime.now() - timedelta(hours=1)
            cursor = conn.execute('SELECT file_path FROM files WHERE created_at < ?', (cutoff,))
            for (file_path,) in cursor.fetchall():
                if os.path.exists(file_path):
                    os.remove(file_path)
            conn.execute('DELETE FROM files WHERE created_at < ?', (cutoff,))
            conn.commit()
            conn.close()
        except:
            pass
        time.sleep(300)

threading.Thread(target=cleanup_files, daemon=True).start()

@bot.message_handler(commands=['start'])
def start_message(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or 'Unknown'
        logger.info(f"User {user_id} ({username}) started the bot")
        
        lang = get_user_lang(message.from_user.language_code)
        bot.reply_to(message, LANG[lang]['welcome'], parse_mode='Markdown')
        
        logger.info(f"Welcome message sent to user {user_id} in {lang} language")
    except Exception as e:
        logger.error(f"Error in start_message: {str(e)}", exc_info=True)

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_file(message):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            file_name = f"photo_{file_info.file_id}.jpg"
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            file_name = message.document.file_name
        elif message.content_type == 'video':
            file_info = bot.get_file(message.video.file_id)
            file_name = f"video_{file_info.file_id}.mp4"
        elif message.content_type == 'audio':
            file_info = bot.get_file(message.audio.file_id)
            file_name = f"audio_{file_info.file_id}.mp3"

        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"files/{file_info.file_id}_{file_name}"
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        conn = sqlite3.connect('files.db')
        cursor = conn.execute('INSERT INTO files (user_id, file_id, file_name, file_path, created_at) VALUES (?, ?, ?, ?, ?)',
                    (message.from_user.id, file_info.file_id, file_name, file_path, datetime.now()))
        db_id = cursor.lastrowid
        conn.commit()
        conn.close()

        lang = get_user_lang(message.from_user.language_code)
        file_type, ext = get_file_type(file_name)
        markup = types.InlineKeyboardMarkup()
        
        if file_type == 'image':
            if ext != 'jpg':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_jpg'], callback_data=f"1_{db_id}"))
            if ext != 'png':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_png'], callback_data=f"2_{db_id}"))
            if ext != 'webp':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_webp'], callback_data=f"3_{db_id}"))
            markup.add(types.InlineKeyboardButton(LANG[lang]['compress_img'], callback_data=f"4_{db_id}"))
        
        elif file_type == 'document' and ext == 'pdf':
            markup.add(types.InlineKeyboardButton(LANG[lang]['compress_pdf'], callback_data=f"5_{db_id}"))
        
        elif file_type == 'video':
            markup.add(types.InlineKeyboardButton(LANG[lang]['extract_mp3'], callback_data=f"6_{db_id}"))
        
        markup.add(types.InlineKeyboardButton(LANG[lang]['zip_file'], callback_data=f"7_{db_id}"))

        bot.reply_to(message, f"📁 {file_name} {LANG[lang]['file_received']}", 
                    reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username or 'Unknown'
    
    try:
        logger.info(f"User {user_id} ({username}) clicked: {call.data}")
        lang = get_user_lang(call.from_user.language_code)
        
        if call.data == "yes_more":
            bot.edit_message_text(LANG[lang]['ready_next'], 
                                call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id)
            return
            
        if call.data == "no_thanks":
            bot.edit_message_text(LANG[lang]['goodbye'], 
                                call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id)
            return
            
        if '_' not in call.data:
            bot.answer_callback_query(call.id, "❌ Invalid action!")
            return
            
        action, db_id = call.data.split('_')
        
        conn = sqlite3.connect('files.db')
        cursor = conn.execute('SELECT file_path, file_name FROM files WHERE id = ?', (db_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.answer_callback_query(call.id, "❌ File not found!")
            return
            
        file_path, original_name = result
        
        if action == "1":
            with Image.open(file_path) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                output = BytesIO()
                img.save(output, format='JPEG')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.jpg")
        
        elif action == "2":
            with Image.open(file_path) as img:
                output = BytesIO()
                img.save(output, format='PNG')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.png")
        
        elif action == "3":
            with Image.open(file_path) as img:
                output = BytesIO()
                img.save(output, format='WEBP')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.webp")
        
        elif action == "4":
            with Image.open(file_path) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                width, height = img.size
                new_size = (int(width * 0.7), int(height * 0.7))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                output = BytesIO()
                img.save(output, format='JPEG', quality=15, optimize=True)
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="compressed.jpg")
        
        elif action == "5":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                output = BytesIO()
                
                new_doc = fitz.open()
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
                    img_data = pix.tobytes("jpeg", jpg_quality=15)
                    
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.insert_image(new_page.rect, stream=img_data)
                
                new_doc.save(output, garbage=4, deflate=True, clean=True)
                new_doc.close()
                doc.close()
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="compressed.pdf")
            except:
                try:
                    compressed_path = f"temp/compressed_{db_id}.pdf"
                    subprocess.run(['gs', '-sDEVICE=pdfwrite', '-dPDFSETTINGS=/ebook', 
                                  '-dNOPAUSE', '-dQUIET', '-dBATCH', f'-sOutputFile={compressed_path}', file_path], 
                                 check=True, capture_output=True)
                    with open(compressed_path, 'rb') as f:
                        bot.send_document(call.message.chat.id, f, visible_file_name="compressed.pdf")
                    os.remove(compressed_path)
                except:
                    with open(file_path, 'rb') as f:
                        bot.send_document(call.message.chat.id, f, visible_file_name="compressed.pdf")
        
        elif action == "6":
            output_path = f"temp/audio_{db_id}.mp3"
            try:
                subprocess.run(['ffmpeg', '-i', file_path, '-q:a', '0', '-map', 'a', output_path], 
                             check=True, capture_output=True)
                with open(output_path, 'rb') as f:
                    bot.send_audio(call.message.chat.id, f)
                os.remove(output_path)
            except:
                bot.answer_callback_query(call.id, "❌ Audio extraction failed (ffmpeg not found)!")
                # Still show completion message even if audio extraction fails
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔄 Process Another File", callback_data="new_file"))
                bot.send_message(call.message.chat.id, LANG[lang]['audio_failed'])
                bot.send_message(call.message.chat.id, LANG[lang]['help_more'], reply_markup=markup)
                return
        
        elif action == "7":
            output = BytesIO()
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, original_name)
            output.seek(0)
            bot.send_document(call.message.chat.id, output, visible_file_name="compressed.zip")
        
        # Send completion message with Yes/No buttons
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(LANG[lang]['yes_more'], callback_data="yes_more"),
            types.InlineKeyboardButton(LANG[lang]['no_thanks'], callback_data="no_thanks")
        )
        
        bot.send_message(call.message.chat.id, LANG[lang]['complete'])
        bot.send_message(call.message.chat.id, LANG[lang]['help_more'], reply_markup=markup)
        bot.answer_callback_query(call.id, LANG[lang]['done'])
        
    except Exception as e:
        logger.error(f"Error for user {user_id}: {str(e)}", exc_info=True)
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

if __name__ == "__main__":
    logger.info("🤖 RupaGanti Bot starting...")
    print("🤖 RupaGanti Bot starting...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}", exc_info=True)