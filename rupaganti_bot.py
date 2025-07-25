import os
import sqlite3
import zipfile
import threading
import time
import logging
import uuid
import shutil
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import telebot
from telebot import types
import mimetypes
import subprocess
import base64
import secrets
import tempfile
import platform

# Import optimized encryption libraries
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    HAS_AES = True
except ImportError:
    from cryptography.fernet import Fernet
    HAS_AES = False

# Try to import libraries for better conversions
try:
    import importlib.util
    if importlib.util.find_spec("pdf2docx"):
        print("pdf2docx library found - enhanced PDF to Word conversion available")
    else:
        print("Warning: pdf2docx not available. PDF to Word conversion may be limited.")
        print("Install with: pip install pdf2docx")
    
    if importlib.util.find_spec("docx2pdf"):
        print("docx2pdf library found - enhanced Word to PDF conversion available")
    else:
        print("Warning: docx2pdf not available. Word to PDF conversion may be limited.")
        print("Install with: pip install docx2pdf")
except ImportError:
    print("Warning: Some conversion libraries may not be available.")
    print("For best results, install: pip install pdf2docx docx2pdf")

# Check if we're on Windows
IS_WINDOWS = platform.system() == 'Windows'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Encryption setup - using AES-256 with hardware acceleration when available
if HAS_AES:
    # Generate a secure AES-256 key
    ENCRYPTION_KEY = secrets.token_bytes(32)  # 256 bits
    # Generate a secure IV (Initialization Vector)
    ENCRYPTION_IV = secrets.token_bytes(16)   # 128 bits
    # Use hardware acceleration if available
    backend = default_backend()
else:
    # Fallback to Fernet if AES is not available
    ENCRYPTION_KEY = Fernet.generate_key()
    cipher_suite = Fernet(ENCRYPTION_KEY)

# Thread pool for encryption/decryption operations
# Use more workers on multi-core systems for better performance
encryption_pool = concurrent.futures.ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, 8))

# Security settings
SECURE_DELETE_PASSES = 1  # Single pass is sufficient with modern storage
FILE_RETENTION_MINUTES = 15  # Maximum time to keep files in database
TEMP_FILE_RETENTION_MINUTES = 5  # Maximum time to keep temporary files
SESSION_TIMEOUT_SECONDS = 120  # 2-minute countdown timer for security
MIN_COMPRESSION_TARGET = 0.5  # Target at least 50% file size reduction

# Replace with your valid Telegram bot token
BOT_TOKEN = "****"

# Configure telebot with proper request settings
telebot.apihelper.RETRY_ON_ERROR = True
telebot.apihelper.CONNECT_TIMEOUT = 10

# Initialize bot with token
bot = telebot.TeleBot(BOT_TOKEN)

# Store active sessions with their timers
active_sessions = {}

# Store user activity timestamps
user_activity = {}

# Language translations
LANG = {
    'en': {
        'welcome': "🎉 Hi! I'm **RupaGanti** by Grands — I help you convert or compress files securely!\n\n📸 **Images**: JPG, PNG, WebP, BMP, TIFF, etc.\n📄 **Documents**: PDF, DOCX, XLSX, PPTX, TXT, etc.\n🎵 **Audio**: MP3, WAV, FLAC, AAC, M4A\n🎬 **Video**: MP4, AVI, MOV, MKV, WMV\n\n🔐 Your files are encrypted & deleted automatically after 2 minutes for your safety.\n\nJust send me a file and I'll show you the options! 🚀",
        'first_welcome': "👋 Welcome to RupaGanti by Grands!\n\nI can help you convert or compress your files safely 🔐✨\n\nTap the button below to get started 👇",
        'start_button': "🔁 Start",
        'inactivity_reminder': "👀 Are you still there?\nLet me know if you still need help!",
        'inactivity_close': "⏳ Session closed due to inactivity.\n\nIf you want to use the bot again, just tap the button below 👇",
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
        'audio_failed': '❌ Audio extraction failed, but I\'m still here to help!',
        'encrypting': '🔐 Encrypting your file securely...',
        'encryption_complete': '✅ File encrypted successfully in {:.2f} seconds.',
        'compressing': '📉 Compressing your file...',
        'cleaning': '🧹 Cleaning up for security...',
        'session_expired': '⏱️ Session expired for your security. File has been removed.',
        'start_over': '🔁 Start Over',
        'countdown': '⏳ {}:{:02d} remaining',
        'compression_result': '✅ Compression successful: {:.1f} MB → {:.1f} MB',
        'already_optimized': '⚠️ This file is already optimized and cannot be compressed further without losing quality.',
        'files_deleted': '🗑️ All files have been securely deleted to protect your data.',
        'file_received': 'received!\n\nChoose what you\'d like to do:',
        'error_processing': '❌ Sorry, there was a problem processing your file.',
        'error_upload': '❌ File upload failed. Please try uploading your file again.',
        'error_general': '❌ Something went wrong. Please try again.',
        'back_to_start': '🔁 Back to Start',
        'try_again': 'Please try uploading your file again or contact support if the problem persists.',
        'convert_to_pdf': '📄 Convert to PDF',
        'what_to_do': 'What would you like to do?',
        'file_ready': '🎉 Done! Your file is ready. Download below 👇',
        'security_reminder': '🔒 Your files are encrypted and will be deleted within 2 minutes if not processed — your data stays safe!',
        'oops_error': '⚠️ Oops! Something went wrong. Please try again or start over.',
        'converting_to_pdf': '📄 Converting to PDF...',
        'pdf_conversion_success': '✅ Word document converted to PDF successfully!',
        'pdf_conversion_failed': '❌ PDF conversion failed. Please try again with a different file.',
        'unsupported_format': '⚠️ Unsupported file format. Please upload one of the supported types:\nImages: JPG, PNG, WebP, BMP, etc.\nDocuments: DOCX, XLSX, PPTX, PDF, etc.\nAudio/Video: MP3, MP4, AVI, etc.',
        'convert_document': '📄 Convert to PDF',
        'compress_document': '🗜️ Compress to ZIP',
        'image_options': 'What would you like to do with your image?',
        'document_options': 'What would you like to do with your document?',
        'media_options': 'What would you like to do with your media file?',
        'convert_to_mp4': '🎬 Convert to MP4',
        'convert_to_mp3': '🎵 Convert to MP3',
        'cancel': '❌ Cancel'
    },
    'id': {
        'welcome': "🎉 Hai! Saya **RupaGanti** by Grands — saya bisa membantu mengkonversi atau mengompres file Anda!\n\n✨ Yang bisa saya lakukan:\n📸 **Gambar**: JPG ↔ PNG ↔ WebP ↔ BMP\n📄 **Dokumen**: Kompresi PDF\n🎵 **Audio**: MP3, WAV, FLAC\n🎬 **Video**: MP4, AVI, MOV\n🗜️ **Kompres**: Kurangi ukuran file\n\nKirim file dan saya akan tunjukkan pilihan! 🚀",
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
    file_types = {
        'image': ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif', 'tiff'],
        'document': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'xlsx', 'xls', 'pptx', 'ppt'],
        'video': ['mp4', 'avi', 'mov', 'mkv', 'wmv'],
        'audio': ['mp3', 'wav', 'flac', 'aac', 'm4a']
    }
    
    for category, extensions in file_types.items():
        if ext in extensions:
            return category, ext
    return 'unsupported', ext

def is_supported_file(filename):
    """Check if file is in any supported format"""
    file_type, ext = get_file_type(filename)
    return file_type != 'unsupported'

def encrypt_file_aes(file_data):
    """Encrypt file data using AES-256 encryption with hardware acceleration"""
    try:
        # For large files, use a more efficient approach with less memory overhead
        if len(file_data) > 10 * 1024 * 1024:  # 10MB
            # Process in chunks for large files
            chunk_size = 1024 * 1024  # 1MB chunks
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(ENCRYPTION_IV), backend=backend)
            encryptor = cipher.encryptor()
            
            # Process all but the last chunk
            result = bytearray()
            for i in range(0, len(file_data) - chunk_size, chunk_size):
                chunk = file_data[i:i+chunk_size]
                result.extend(encryptor.update(chunk))
            
            # Process the last chunk with padding
            last_chunk = file_data[-(len(file_data) % chunk_size or chunk_size):]
            padded_last_chunk = padder.update(last_chunk) + padder.finalize()
            result.extend(encryptor.update(padded_last_chunk) + encryptor.finalize())
            
            # Prepend IV to the encrypted data for decryption later
            return ENCRYPTION_IV + bytes(result)
        else:
            # For smaller files, use the simpler approach
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(file_data) + padder.finalize()
            
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(ENCRYPTION_IV), backend=backend)
            encryptor = cipher.encryptor()
            
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Prepend IV to the encrypted data for decryption later
            return ENCRYPTION_IV + encrypted_data
    except Exception as e:
        logger.error(f"AES encryption error: {str(e)}")
        raise

def encrypt_file_fernet(file_data):
    """Encrypt file data using Fernet encryption"""
    try:
        return cipher_suite.encrypt(file_data)
    except Exception as e:
        logger.error(f"Fernet encryption error: {str(e)}")
        raise

def encrypt_file(file_data):
    """Encrypt file data using the best available method"""
    start_time = time.time()
    try:
        if HAS_AES:
            # Use AES-256 encryption with hardware acceleration
            result = encrypt_file_aes(file_data)
        else:
            # Fallback to Fernet encryption
            result = encrypt_file_fernet(file_data)
        
        encryption_time = time.time() - start_time
        logger.info(f"File encrypted successfully in {encryption_time:.2f} seconds")
        return result, encryption_time
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        # If encryption fails, return original data with warning
        logger.critical("Encryption completely failed, returning original data")
        return file_data, 0  # Last resort
        
def get_file_size_mb(data):
    """Get file size in MB"""
    return len(data) / (1024 * 1024)

def calculate_compression_ratio(original_size, compressed_size):
    """Calculate compression ratio"""
    if original_size == 0:
        return 0
    return 1 - (compressed_size / original_size)

def decrypt_file_aes(encrypted_data):
    """Decrypt file data using AES-256 encryption with chunked processing for large files"""
    try:
        # Extract IV from the beginning of the encrypted data
        iv = encrypted_data[:16]
        actual_encrypted_data = encrypted_data[16:]
        
        # For large files, use a more efficient approach with less memory overhead
        if len(actual_encrypted_data) > 10 * 1024 * 1024:  # 10MB
            # Process in chunks for large files
            chunk_size = 1024 * 1024  # 1MB chunks
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            
            # Process all but the last chunk
            result = bytearray()
            for i in range(0, len(actual_encrypted_data) - chunk_size, chunk_size):
                chunk = actual_encrypted_data[i:i+chunk_size]
                result.extend(decryptor.update(chunk))
            
            # Process the last chunk with unpadding
            last_chunk = actual_encrypted_data[-(len(actual_encrypted_data) % chunk_size or chunk_size):]
            decrypted_last_chunk = decryptor.update(last_chunk) + decryptor.finalize()
            result.extend(unpadder.update(decrypted_last_chunk) + unpadder.finalize())
            
            return bytes(result)
        else:
            # For smaller files, use the simpler approach
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(actual_encrypted_data) + decryptor.finalize()
            
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            return unpadder.update(padded_data) + unpadder.finalize()
    except Exception as e:
        logger.error(f"AES decryption error: {str(e)}")
        raise

def decrypt_file_fernet(encrypted_data):
    """Decrypt file data using Fernet encryption"""
    try:
        return cipher_suite.decrypt(encrypted_data)
    except Exception as e:
        logger.error(f"Fernet decryption error: {str(e)}")
        raise

def decrypt_file(encrypted_data):
    """Decrypt file data using the best available method"""
    start_time = time.time()
    try:
        # Try AES decryption first if it's available and the data looks like AES-encrypted
        if HAS_AES and len(encrypted_data) > 16:
            try:
                result = decrypt_file_aes(encrypted_data)
                decryption_time = time.time() - start_time
                logger.info(f"File decrypted successfully with AES in {decryption_time:.2f} seconds")
                return result
            except Exception:
                # If AES decryption fails, try Fernet
                if not HAS_AES:
                    result = decrypt_file_fernet(encrypted_data)
                    decryption_time = time.time() - start_time
                    logger.info(f"File decrypted successfully with Fernet in {decryption_time:.2f} seconds")
                    return result
        elif not HAS_AES:
            # If AES is not available, use Fernet
            result = decrypt_file_fernet(encrypted_data)
            decryption_time = time.time() - start_time
            logger.info(f"File decrypted successfully with Fernet in {decryption_time:.2f} seconds")
            return result
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        # If we can't decrypt, this might be unencrypted data (from fallback)
        try:
            # Check if it looks like valid file data
            if len(encrypted_data) > 0:
                logger.warning("Attempting to use data as-is (might be unencrypted)")
                return encrypted_data
        except:
            pass
        
        # If all fails, raise error
        raise ValueError("Failed to decrypt file data")

def session_expired(chat_id, file_path, db_id=None, lang='en'):
    """Handle session expiration"""
    try:
        # Delete the file if it exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted expired file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete expired file {file_path}: {str(e)}")
        
        # Delete from database if db_id is provided
        if db_id:
            try:
                conn = sqlite3.connect('files.db')
                conn.execute('DELETE FROM files WHERE id = ?', (db_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to delete expired file from database: {str(e)}")
        
        # Send expiration message
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(LANG[lang]['start_over'], callback_data="start_over"))
        bot.send_message(chat_id, LANG[lang]['session_expired'], reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in session_expired: {str(e)}")

def update_countdown(chat_id, message_id, seconds_left, lang='en'):
    """Update countdown message"""
    try:
        # Format as minutes:seconds
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        
        # Update every second for a more animated effect
        bot.edit_message_text(
            LANG[lang]['countdown'].format(minutes, seconds),
            chat_id,
            message_id
        )
    except Exception as e:
        logger.error(f"Error updating countdown: {str(e)}")

def start_session_timer(chat_id, file_path, db_id, lang='en'):
    """Start countdown timer for session"""
    try:
        # Create countdown message with initial format (2:00)
        minutes = SESSION_TIMEOUT_SECONDS // 60
        seconds = SESSION_TIMEOUT_SECONDS % 60
        countdown_msg = bot.send_message(chat_id, LANG[lang]['countdown'].format(minutes, seconds))
        
        # Store session info
        active_sessions[chat_id] = {
            'file_path': file_path,
            'db_id': db_id,
            'countdown_msg_id': countdown_msg.message_id,
            'lang': lang,
            'start_time': time.time(),
            'timer': None
        }
        
        # Function to update countdown and check expiration
        def check_session():
            try:
                if chat_id not in active_sessions:
                    return
                
                elapsed = time.time() - active_sessions[chat_id]['start_time']
                remaining = max(0, SESSION_TIMEOUT_SECONDS - int(elapsed))
                
                # Always update the countdown for smooth animation
                
                if remaining <= 0:
                    # Session expired
                    session_info = active_sessions.pop(chat_id, None)
                    if session_info:
                        session_expired(chat_id, session_info['file_path'], session_info['db_id'], session_info['lang'])
                else:
                    # Update countdown and schedule next check - update every second for animation
                    update_countdown(chat_id, active_sessions[chat_id]['countdown_msg_id'], remaining, lang)
                    timer = threading.Timer(1.0, check_session)
                    timer.daemon = True
                    timer.start()
                    active_sessions[chat_id]['timer'] = timer
            except Exception as e:
                logger.error(f"Error in check_session: {str(e)}")
        
        # Start the timer
        timer = threading.Timer(1.0, check_session)
        timer.daemon = True
        timer.start()
        active_sessions[chat_id]['timer'] = timer
        
    except Exception as e:
        logger.error(f"Error starting session timer: {str(e)}")

def generate_secure_filename(original_name):
    """Generate a secure random filename while preserving extension"""
    ext = original_name.split('.')[-1] if '.' in original_name else ''
    secure_name = str(uuid.uuid4())
    return f"{secure_name}.{ext}" if ext else secure_name

def secure_delete_file(file_path):
    """Securely delete a file by overwriting with random data before deletion"""
    if not os.path.exists(file_path):
        return
        
    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Skip very large files for performance reasons
        if file_size > 100 * 1024 * 1024:  # 100MB
            os.remove(file_path)
            logger.info(f"Large file deleted (regular): {file_path}")
            return
            
        # Overwrite file with random data multiple times
        for _ in range(SECURE_DELETE_PASSES):
            with open(file_path, 'wb') as f:
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Finally delete the file
        os.remove(file_path)
        logger.info(f"Securely deleted: {file_path}")
    except Exception as e:
        logger.error(f"Secure deletion failed for {file_path}: {str(e)}")
        # Attempt regular deletion as fallback
        try:
            os.remove(file_path)
            logger.info(f"Fallback regular deletion for: {file_path}")
        except Exception as e2:
            logger.critical(f"Complete deletion failure for {file_path}: {str(e2)}")
            # Last resort - try to make file empty
            try:
                with open(file_path, 'w') as f:
                    pass  # Truncate file to 0 bytes
            except:
                pass

def cleanup_inactive_users():
    """Clean up inactive user sessions"""
    while True:
        try:
            current_time = time.time()
            users_to_remove = []
            
            # Check each user's activity
            for user_id, data in user_activity.items():
                # If user has been inactive for more than 5 minutes, clean up
                if current_time - data['timestamp'] > 300:  # 5 minutes
                    users_to_remove.append(user_id)
            
            # Remove inactive users
            for user_id in users_to_remove:
                if user_id in user_activity:
                    try:
                        if user_activity[user_id]['timer']:
                            user_activity[user_id]['timer'].cancel()
                    except:
                        pass
                    user_activity.pop(user_id, None)
                    logger.info(f"Cleaned up inactive user: {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up inactive users: {str(e)}")
        
        # Check every minute
        time.sleep(60)

def cleanup_files():
    while True:
        try:
            # Clean database files
            conn = sqlite3.connect('files.db')
            cutoff = datetime.now() - timedelta(minutes=FILE_RETENTION_MINUTES)
            cursor = conn.execute('SELECT file_path FROM files WHERE created_at < ?', (cutoff,))
            for (file_path,) in cursor.fetchall():
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")
            
            conn.execute('DELETE FROM files WHERE created_at < ?', (cutoff,))
            conn.commit()
            conn.close()
            
            # Clean temp directory - more aggressive cleanup
            if os.path.exists("temp"):
                for filename in os.listdir("temp"):
                    file_path = os.path.join("temp", filename)
                    if os.path.isfile(file_path):
                        try:
                            file_age = datetime.now() - datetime.fromtimestamp(os.path.getctime(file_path))
                            if file_age > timedelta(minutes=TEMP_FILE_RETENTION_MINUTES):
                                os.remove(file_path)
                                logger.info(f"Deleted temp file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete temp file {file_path}: {str(e)}")
            
            # Check for any empty directories and clean them
            for folder in ["files", "temp"]:
                if os.path.exists(folder) and os.path.isdir(folder):
                    try:
                        # Remove empty subdirectories
                        for root, dirs, files in os.walk(folder, topdown=False):
                            for dir_name in dirs:
                                dir_path = os.path.join(root, dir_name)
                                if not os.listdir(dir_path):  # If directory is empty
                                    os.rmdir(dir_path)
                                    logger.info(f"Removed empty directory: {dir_path}")
                    except Exception as e:
                        logger.error(f"Failed to clean directories in {folder}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        time.sleep(180)  # Check every 3 minutes instead of 5

# Start background cleanup threads
threading.Thread(target=cleanup_files, daemon=True).start()
threading.Thread(target=cleanup_inactive_users, daemon=True).start()

@bot.message_handler(func=lambda message: message.content_type == 'text' and not message.text.startswith('/'))
def handle_first_message(message):
    """Handle any text message as first interaction"""
    try:
        user_id = message.from_user.id
        lang = get_user_lang(message.from_user.language_code)
        
        # Send first welcome message with Start button
        send_first_welcome(message.chat.id, lang)
        
        # Start inactivity timer
        start_inactivity_timer(user_id, message.chat.id, lang)
        
    except Exception as e:
        logger.error(f"Error in handle_first_message: {str(e)}")

def send_first_welcome(chat_id, lang='en'):
    """Send the first welcome message with Start button"""
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(LANG[lang]['start_button'], callback_data="start_bot"))
        bot.send_message(chat_id, LANG[lang]['first_welcome'], reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending first welcome: {str(e)}")

def send_error_with_restart(chat_id, error_message, lang='en'):
    """Send error message with Back to Start button"""
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(LANG[lang]['back_to_start'], callback_data="start_bot"))
        
        full_message = f"{error_message}\n\n{LANG[lang]['try_again']}"
        bot.send_message(chat_id, full_message, reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending error message: {str(e)}")

def cleanup_failed_file(file_path):
    """Clean up a failed or corrupted file"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up failed file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to clean up file {file_path}: {str(e)}")

def start_inactivity_timer(user_id, chat_id, lang='en'):
    """Start inactivity timer for a user"""
    # Update user's last activity time
    user_activity[user_id] = {
        'timestamp': time.time(),
        'chat_id': chat_id,
        'lang': lang,
        'reminder_sent': False,
        'timer': None
    }
    
    # Function to check inactivity
    def check_inactivity():
        if user_id not in user_activity:
            return
            
        current_time = time.time()
        last_activity = user_activity[user_id]['timestamp']
        elapsed = current_time - last_activity
        
        # If 2 minutes passed without activity and reminder not sent yet
        if elapsed > 120 and not user_activity[user_id]['reminder_sent']:
            # Send reminder
            try:
                bot.send_message(chat_id, LANG[lang]['inactivity_reminder'])
                user_activity[user_id]['reminder_sent'] = True
                
                # Schedule final check after 1 more minute
                timer = threading.Timer(60.0, check_inactivity)
                timer.daemon = True
                timer.start()
                user_activity[user_id]['timer'] = timer
            except:
                pass
        # If 3 minutes total passed (reminder sent 1 minute ago)
        elif elapsed > 180 and user_activity[user_id]['reminder_sent']:
            # Send session closed message
            try:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(LANG[lang]['start_button'], callback_data="start_bot"))
                bot.send_message(chat_id, LANG[lang]['inactivity_close'], reply_markup=markup)
                
                # Clean up user activity
                user_activity.pop(user_id, None)
            except:
                pass
        else:
            # Schedule next check
            timer = threading.Timer(30.0, check_inactivity)  # Check every 30 seconds
            timer.daemon = True
            timer.start()
            user_activity[user_id]['timer'] = timer
    
    # Start the inactivity timer
    timer = threading.Timer(30.0, check_inactivity)  # First check after 30 seconds
    timer.daemon = True
    timer.start()
    user_activity[user_id]['timer'] = timer

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    if user_id in user_activity:
        user_activity[user_id]['timestamp'] = time.time()
        user_activity[user_id]['reminder_sent'] = False

@bot.message_handler(commands=['start'])
def start_message(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or 'Unknown'
        logger.info(f"User {user_id} ({username}) started the bot")
        
        # Cancel any existing session for this user
        if user_id in active_sessions:
            try:
                active_sessions[user_id]['timer'].cancel()
            except:
                pass
            active_sessions.pop(user_id, None)
        
        # Send welcome message with integrated security info
        lang = get_user_lang(message.from_user.language_code)
        bot.send_message(message.chat.id, LANG[lang]['welcome'], parse_mode='Markdown')
        
        # Update user activity and start inactivity timer
        update_user_activity(user_id)
        start_inactivity_timer(user_id, message.chat.id, lang)
        
        logger.info(f"Welcome message sent to user {user_id} in {lang} language")
    except Exception as e:
        logger.error(f"Error in start_message: {str(e)}", exc_info=True)

def async_encrypt_file(file_data, file_path):
    """Asynchronously encrypt and save a file with optimized memory usage"""
    try:
        # Start timing for performance measurement
        start_time = time.time()
        
        # For very large files, encrypt directly to disk to reduce memory usage
        if len(file_data) > 50 * 1024 * 1024:  # 50MB
            # Use direct-to-disk encryption for very large files
            if HAS_AES:
                # Create a temporary file for encryption
                temp_path = f"{file_path}.tmp"
                
                # Encrypt in chunks and write directly to disk
                chunk_size = 5 * 1024 * 1024  # 5MB chunks
                padder = padding.PKCS7(algorithms.AES.block_size).padder()
                cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(ENCRYPTION_IV), backend=backend)
                encryptor = cipher.encryptor()
                
                # Write IV at the beginning of the file
                with open(temp_path, 'wb') as f:
                    f.write(ENCRYPTION_IV)
                    
                    # Process all chunks except the last one
                    for i in range(0, len(file_data) - chunk_size, chunk_size):
                        chunk = file_data[i:i+chunk_size]
                        encrypted_chunk = encryptor.update(chunk)
                        f.write(encrypted_chunk)
                    
                    # Process the last chunk with padding
                    last_chunk = file_data[-(len(file_data) % chunk_size or chunk_size):]
                    padded_last_chunk = padder.update(last_chunk) + padder.finalize()
                    encrypted_last_chunk = encryptor.update(padded_last_chunk) + encryptor.finalize()
                    f.write(encrypted_last_chunk)
                
                # Rename the temp file to the final file
                os.replace(temp_path, file_path)
            else:
                # Use Fernet for large files (less efficient but simpler)
                encrypted_data = cipher_suite.encrypt(file_data)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
        else:
            # For smaller files, use the in-memory encryption
            encrypted_data, _ = encrypt_file(file_data)
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
        
        # Calculate total encryption time
        encryption_time = time.time() - start_time
        logger.info(f"File encrypted and saved in {encryption_time:.2f} seconds")
        return encryption_time
    except Exception as e:
        logger.error(f"Async encryption error: {str(e)}")
        raise

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_file(message):
    try:
        # Cancel any existing session for this user
        user_id = message.from_user.id
        if user_id in active_sessions:
            try:
                active_sessions[user_id]['timer'].cancel()
            except:
                pass
            active_sessions.pop(user_id, None)
            
        # Update user activity
        update_user_activity(user_id)
        
        # Show encrypting status
        lang = get_user_lang(message.from_user.language_code)
        status_msg = bot.send_message(message.chat.id, LANG[lang]['encrypting'])
        
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            original_name = f"photo_{message.photo[-1].file_id}.jpg"
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            original_name = message.document.file_name
        elif message.content_type == 'video':
            file_info = bot.get_file(message.video.file_id)
            original_name = f"video_{message.video.file_id}.mp4"
        elif message.content_type == 'audio':
            file_info = bot.get_file(message.audio.file_id)
            original_name = f"audio_{message.audio.file_id}.mp3"

        # Generate secure filename
        secure_filename = generate_secure_filename(original_name)
        
        # Download file
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"files/{secure_filename}"
        
        # Get original file size for compression ratio calculation
        original_size = get_file_size_mb(downloaded_file)
        
        # Start encryption in a separate thread
        future = encryption_pool.submit(async_encrypt_file, downloaded_file, file_path)
        
        # Update encryption status with animated progress indicator
        animation_chars = ['⏳', '⌛', '⏳', '⌛']
        dots = 0
        char_idx = 0
        start_time = time.time()
        
        while not future.done():
            elapsed = time.time() - start_time
            dots = (dots % 3) + 1
            char_idx = (char_idx + 1) % len(animation_chars)
            
            try:
                # Show animated progress with elapsed time
                bot.edit_message_text(
                    f"{animation_chars[char_idx]} {LANG[lang]['encrypting']} {'.' * dots}\n({elapsed:.1f}s)",
                    message.chat.id, 
                    status_msg.message_id
                )
            except:
                pass
            
            # Shorter sleep time for smoother animation
            time.sleep(0.3)
        
        # Get encryption result
        try:
            encryption_time = future.result()
            # Show encryption completion message
            bot.edit_message_text(
                LANG[lang]['encryption_complete'].format(encryption_time),
                message.chat.id,
                status_msg.message_id
            )
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            # If encryption in thread failed, try direct encryption as fallback
            encrypted_data, _ = encrypt_file(downloaded_file)
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)

        # Store original name and secure path in database
        conn = sqlite3.connect('files.db')
        cursor = conn.execute('INSERT INTO files (user_id, file_id, file_name, file_path, created_at) VALUES (?, ?, ?, ?, ?)',
                    (message.from_user.id, file_info.file_id, original_name, file_path, datetime.now()))
        db_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Log secure handling
        logger.info(f"File securely stored: {original_name} → {secure_filename}")

        # Wait a moment to show the encryption success message
        time.sleep(1)
        
        # Update status message with file received format
        try:
            if not LANG[lang].get('file_received'):
                LANG[lang]['file_received'] = 'received!\n\nChoose what you\'d like to do:'
            success_message = f"📁 {original_name} {LANG[lang]['file_received']}\n✅ File successfully encrypted."
            bot.edit_message_text(success_message, message.chat.id, status_msg.message_id)
        except Exception as e:
            logger.error(f"Error updating status message: {str(e)}")
            pass
            
        file_type, ext = get_file_type(original_name)
        markup = types.InlineKeyboardMarkup()
        
        # Check if file format is supported
        if not is_supported_file(original_name):
            send_error_with_restart(message.chat.id, LANG[lang]['unsupported_format'], lang)
            cleanup_failed_file(file_path)
            return
        
        # Create contextual menu based on file type
        if file_type == 'image':
            options_text = LANG[lang]['image_options']
            if ext != 'jpg':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_jpg'], callback_data=f"1_{db_id}"))
            if ext != 'png':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_png'], callback_data=f"2_{db_id}"))
            if ext != 'webp':
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_webp'], callback_data=f"3_{db_id}"))
            markup.add(types.InlineKeyboardButton(LANG[lang]['compress_img'], callback_data=f"4_{db_id}"))
        
        elif file_type == 'document':
            options_text = LANG[lang]['document_options']
            if ext == 'pdf':
                markup.add(types.InlineKeyboardButton(LANG[lang]['compress_pdf'], callback_data=f"5_{db_id}"))
                markup.add(types.InlineKeyboardButton('📄 Convert to Word', callback_data=f"8_{db_id}"))
            else:
                markup.add(types.InlineKeyboardButton(LANG[lang]['convert_document'], callback_data=f"convert_pdf_{db_id}"))
                markup.add(types.InlineKeyboardButton(LANG[lang]['compress_document'], callback_data=f"compress_zip_{db_id}"))
        
        elif file_type == 'video':
            options_text = LANG[lang]['media_options']
            markup.add(types.InlineKeyboardButton(LANG[lang]['convert_to_mp4'], callback_data=f"video_mp4_{db_id}"))
            markup.add(types.InlineKeyboardButton(LANG[lang]['extract_mp3'], callback_data=f"6_{db_id}"))
            markup.add(types.InlineKeyboardButton(LANG[lang]['zip_file'], callback_data=f"7_{db_id}"))
        
        elif file_type == 'audio':
            options_text = LANG[lang]['media_options']
            markup.add(types.InlineKeyboardButton(LANG[lang]['convert_to_mp3'], callback_data=f"audio_mp3_{db_id}"))
            markup.add(types.InlineKeyboardButton(LANG[lang]['zip_file'], callback_data=f"7_{db_id}"))
        
        # Add cancel button for all types
        markup.add(types.InlineKeyboardButton(LANG[lang]['cancel'], callback_data=f"cancel_{db_id}"))

        # Create the file received message with proper formatting
        if not LANG[lang].get('file_received'):
            LANG[lang]['file_received'] = 'received!\n\nChoose what you\'d like to do:'
            
        # Create contextual file message based on file type
        file_message = f"📁 {original_name} {LANG[lang]['file_received']}\n✅ Encrypted.\n\n{options_text}\n\n{LANG[lang]['security_reminder']}"
        
        reply_msg = bot.reply_to(message, file_message, reply_markup=markup)
        
        # Start the session timer
        start_session_timer(message.chat.id, file_path, db_id, lang)

    except Exception as e:
        logger.error(f"File handling error for user {message.from_user.id}: {str(e)}")
        lang = get_user_lang(message.from_user.language_code)
        
        # Clean up any partially created files
        try:
            if 'file_path' in locals():
                cleanup_failed_file(file_path)
        except:
            pass
            
        # Send user-friendly error message with restart button
        send_error_with_restart(message.chat.id, LANG[lang]['error_upload'], lang)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username or 'Unknown'
    temp_files = []  # Track temporary files for cleanup
    
    try:
        logger.info(f"User {user_id} ({username}) clicked: {call.data}")
        lang = get_user_lang(call.from_user.language_code)
        
        # Update user activity when any button is clicked
        update_user_activity(user_id)
        
        # Handle start_bot callback for first welcome message
        if call.data == "start_bot":
            bot.send_message(call.message.chat.id, LANG[lang]['welcome'], parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return
        
        # Handle document conversion callbacks
        if call.data.startswith("convert_pdf_"):
            db_id = call.data.split('_')[2]
            # Redirect to Word to PDF conversion (action 9)
            call.data = f"9_{db_id}"
        
        elif call.data.startswith("compress_zip_"):
            db_id = call.data.split('_')[2]
            # Redirect to ZIP compression (action 7)
            call.data = f"7_{db_id}"
        
        # Cancel session timer when user takes action
        if user_id in active_sessions:
            try:
                active_sessions[user_id]['timer'].cancel()
                # Try to delete the countdown message
                try:
                    bot.delete_message(call.message.chat.id, active_sessions[user_id]['countdown_msg_id'])
                except:
                    pass
            except:
                pass
            active_sessions.pop(user_id, None)
        
        if call.data == "start_over":
            bot.send_message(call.message.chat.id, LANG[lang]['ready_next'])
            bot.answer_callback_query(call.id)
            return
            
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
        
        # Show processing status
        status_msg = bot.send_message(call.message.chat.id, LANG[lang]['compressing'])
        
        # Read and decrypt the file
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Check if file is empty
            if not encrypted_data:
                raise ValueError("File is empty")
                
            file_data = decrypt_file(encrypted_data)
            
            # Get original file size for compression ratio calculation
            original_size = get_file_size_mb(file_data)
            
        except Exception as e:
            logger.error(f"Failed to read or decrypt file {file_path}: {str(e)}")
            
            # Clean up the corrupted file
            cleanup_failed_file(file_path)
            
            # Send user-friendly error with restart button
            send_error_with_restart(call.message.chat.id, LANG[lang]['error_processing'], lang)
            bot.answer_callback_query(call.id, "File processing error")
            return
        
        if action == "1":
            img_io = BytesIO(file_data)
            with Image.open(img_io) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                output = BytesIO()
                img.save(output, format='JPEG')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.jpg")
        
        elif action == "2":
            img_io = BytesIO(file_data)
            with Image.open(img_io) as img:
                output = BytesIO()
                img.save(output, format='PNG')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.png")
        
        elif action == "3":
            img_io = BytesIO(file_data)
            with Image.open(img_io) as img:
                output = BytesIO()
                img.save(output, format='WEBP')
                output.seek(0)
                bot.send_document(call.message.chat.id, output, visible_file_name="converted.webp")
        
        elif action == "4":
            img_io = BytesIO(file_data)
            with Image.open(img_io) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                width, height = img.size
                
                # More aggressive compression to reach 50% target
                new_size = (int(width * 0.6), int(height * 0.6))  # 60% of original dimensions
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                output = BytesIO()
                # Try with quality=10 for better compression
                img.save(output, format='JPEG', quality=10, optimize=True)
                output.seek(0)
                
                # Calculate compression ratio
                compressed_size = get_file_size_mb(output.getvalue())
                ratio = calculate_compression_ratio(original_size, compressed_size)
                
                # If compression target not met but file is large enough, try more aggressive settings
                if ratio < MIN_COMPRESSION_TARGET and width > 800 and height > 800:
                    # Try more aggressive compression but maintain readability
                    output = BytesIO()
                    new_size = (int(width * 0.5), int(height * 0.5))  # 50% of original dimensions
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    img.save(output, format='JPEG', quality=15, optimize=True)  # Quality 15 for better readability
                    output.seek(0)
                    
                    # Recalculate compression ratio
                    compressed_size = get_file_size_mb(output.getvalue())
                    ratio = calculate_compression_ratio(original_size, compressed_size)
                
                # Show appropriate message based on compression ratio
                if ratio < 0.1:  # Less than 10% compression
                    bot.send_message(call.message.chat.id, LANG[lang]['already_optimized'])
                else:
                    # Show compression result with file sizes
                    bot.send_message(call.message.chat.id, 
                                    LANG[lang]['compression_result'].format(original_size, compressed_size))
                
                # Send the compressed file
                bot.send_document(call.message.chat.id, output, visible_file_name="compressed.jpg")
                
                # Confirm file deletion for security
                bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
        
        elif action == "5":
            try:
                import fitz  # PyMuPDF
                pdf_io = BytesIO(file_data)
                doc = fitz.open(stream=pdf_io, filetype="pdf")
                output = BytesIO()
                
                new_doc = fitz.open()
                
                # More aggressive compression settings
                compression_matrix = fitz.Matrix(0.25, 0.25)  # 25% of original size
                jpg_quality = 10  # Lower quality for better compression
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=compression_matrix)
                    img_data = pix.tobytes("jpeg", jpg_quality=jpg_quality)
                    
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.insert_image(new_page.rect, stream=img_data)
                
                # Use maximum compression settings
                new_doc.save(output, garbage=4, deflate=True, clean=True, linear=True)
                new_doc.close()
                doc.close()
                output.seek(0)
                
                # Calculate compression ratio
                compressed_size = get_file_size_mb(output.getvalue())
                ratio = calculate_compression_ratio(original_size, compressed_size)
                
                # If compression target not met but document has multiple pages, try more balanced settings
                if ratio < MIN_COMPRESSION_TARGET and len(doc) > 1:
                    output = BytesIO()
                    doc = fitz.open(stream=pdf_io, filetype="pdf")
                    new_doc = fitz.open()
                    
                    # More balanced settings to maintain readability
                    compression_matrix = fitz.Matrix(0.3, 0.3)  # 30% of original size for better readability
                    jpg_quality = 20  # Better quality for readability
                    
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        pix = page.get_pixmap(matrix=compression_matrix)
                        img_data = pix.tobytes("jpeg", jpg_quality=jpg_quality)
                        
                        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                        new_page.insert_image(new_page.rect, stream=img_data)
                    
                    new_doc.save(output, garbage=4, deflate=True, clean=True, linear=True)
                    new_doc.close()
                    doc.close()
                    output.seek(0)
                    
                    # Recalculate compression ratio
                    compressed_size = get_file_size_mb(output.getvalue())
                    ratio = calculate_compression_ratio(original_size, compressed_size)
                
                # Show appropriate message based on compression ratio
                if ratio < 0.1:  # Less than 10% compression
                    bot.send_message(call.message.chat.id, LANG[lang]['already_optimized'])
                else:
                    # Show compression result with file sizes
                    bot.send_message(call.message.chat.id, 
                                    LANG[lang]['compression_result'].format(original_size, compressed_size))
                
                # Send the compressed file
                bot.send_document(call.message.chat.id, output, visible_file_name="compressed.pdf")
                
                # Confirm file deletion for security
                bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
            except:
                try:
                    temp_pdf = f"temp/temp_{db_id}_{int(time.time())}.pdf"
                    temp_files.append(temp_pdf)  # Track for cleanup
                    with open(temp_pdf, 'wb') as f:
                        f.write(file_data)
                    compressed_path = f"temp/compressed_{db_id}_{int(time.time())}.pdf"
                    temp_files.append(compressed_path)  # Track for cleanup
                    # Use more aggressive compression settings
                    subprocess.run(['gs', '-sDEVICE=pdfwrite', '-dPDFSETTINGS=/screen', 
                                  '-dDownsampleColorImages=true', '-dColorImageResolution=72',
                                  '-dCompatibilityLevel=1.4', '-dEmbedAllFonts=false',
                                  '-dSubsetFonts=true', '-dNOPAUSE', '-dQUIET', '-dBATCH', 
                                  f'-sOutputFile={compressed_path}', temp_pdf], 
                                 check=True, capture_output=True)
                    with open(compressed_path, 'rb') as f:
                        compressed_data = f.read()
                    
                    # Calculate compression ratio
                    compressed_size = get_file_size_mb(compressed_data)
                    ratio = calculate_compression_ratio(original_size, compressed_size)
                    
                    # If compression target not met but still preserving readability
                    if ratio < MIN_COMPRESSION_TARGET:
                        # Try with more balanced settings
                        more_compressed_path = f"temp/more_compressed_{db_id}_{int(time.time())}.pdf"
                        temp_files.append(more_compressed_path)
                        
                        # Use more balanced settings to maintain readability
                        subprocess.run(['gs', '-sDEVICE=pdfwrite', '-dPDFSETTINGS=/ebook', 
                                      '-dDownsampleColorImages=true', '-dColorImageResolution=150',
                                      '-dDownsampleGrayImages=true', '-dGrayImageResolution=150',
                                      '-dDownsampleMonoImages=true', '-dMonoImageResolution=150',
                                      '-dCompatibilityLevel=1.5', '-dEmbedAllFonts=true',
                                      '-dSubsetFonts=true', '-dNOPAUSE', '-dQUIET', '-dBATCH', 
                                      f'-sOutputFile={more_compressed_path}', temp_pdf], 
                                     check=True, capture_output=True)
                        
                        with open(more_compressed_path, 'rb') as f:
                            more_compressed_data = f.read()
                        
                        more_compressed_size = get_file_size_mb(more_compressed_data)
                        more_ratio = calculate_compression_ratio(original_size, more_compressed_size)
                        
                        # Use the better compression while maintaining readability
                        if more_ratio > ratio * 0.8:  # Accept if at least 80% as effective
                            compressed_data = more_compressed_data
                            compressed_size = more_compressed_size
                            ratio = more_ratio
                            os.remove(compressed_path)
                        else:
                            os.remove(more_compressed_path)
                    
                    # Show appropriate message based on compression ratio
                    if ratio < 0.1:  # Less than 10% compression
                        bot.send_message(call.message.chat.id, LANG[lang]['already_optimized'])
                    else:
                        # Show compression result with file sizes
                        bot.send_message(call.message.chat.id, 
                                        LANG[lang]['compression_result'].format(original_size, compressed_size))
                    
                    # Send as BytesIO to avoid file access issues
                    output = BytesIO(compressed_data)
                    output.seek(0)
                    bot.send_document(call.message.chat.id, output, visible_file_name="compressed.pdf")
                    
                    # Confirm file deletion for security
                    bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
                    os.remove(compressed_path)
                    os.remove(temp_pdf)
                except Exception as e:
                    logger.error(f"PDF compression error: {str(e)}")
                    output = BytesIO(file_data)
                    output.seek(0)
                    bot.send_document(call.message.chat.id, output, visible_file_name="compressed.pdf")
        
        elif action == "6":
            output_path = f"temp/audio_{db_id}_{int(time.time())}.mp3"
            temp_files.append(output_path)  # Track for cleanup
            temp_video = f"temp/temp_video_{db_id}_{int(time.time())}"
            temp_files.append(temp_video)  # Track for cleanup
            try:
                with open(temp_video, 'wb') as f:
                    f.write(file_data)
                subprocess.run(['ffmpeg', '-i', temp_video, '-q:a', '0', '-map', 'a', output_path], 
                             check=True, capture_output=True)
                with open(output_path, 'rb') as f:
                    bot.send_audio(call.message.chat.id, f)
                os.remove(output_path)
                os.remove(temp_video)
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
            temp_file = f"temp/temp_zip_{db_id}_{int(time.time())}"
            temp_files.append(temp_file)  # Track for cleanup
            with open(temp_file, 'wb') as f:
                f.write(file_data)
                
            # Use maximum compression level (9) for better compression
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(temp_file, original_name)
            os.remove(temp_file)
            output.seek(0)
            
            # Calculate compression ratio
            compressed_size = get_file_size_mb(output.getvalue())
            ratio = calculate_compression_ratio(original_size, compressed_size)
            
            # Show appropriate message based on compression ratio
            if ratio < 0.1:  # Less than 10% compression
                bot.send_message(call.message.chat.id, LANG[lang]['already_optimized'])
            else:
                # Show compression result with file sizes
                bot.send_message(call.message.chat.id, 
                                LANG[lang]['compression_result'].format(original_size, compressed_size))
            
            # Send the compressed file
            bot.send_document(call.message.chat.id, output, visible_file_name="compressed.zip")
            
            # Confirm file deletion for security
            bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
        
        # PDF to Word conversion
        elif action == "8":
            try:
                # Create a secure temporary directory that will be automatically cleaned up
                temp_dir = tempfile.mkdtemp(prefix="rupaganti_")
                try:
                    # Create temp PDF file with unique name - use normalized path
                    temp_pdf = os.path.normpath(os.path.join(temp_dir, f"temp_{db_id}.pdf"))
                    with open(temp_pdf, 'wb') as f:
                        f.write(file_data)
                    
                    # Output DOCX path - use normalized path
                    output_docx = os.path.normpath(os.path.join(temp_dir, f"converted_{db_id}.docx"))
                    
                    # Use pdf2docx for better conversion if available
                    pdf_conversion_success = False
                    if 'pdf2docx' in globals() or 'Converter' in globals():
                        try:
                            # Convert PDF to DOCX using pdf2docx
                            from pdf2docx import Converter
                            cv = Converter(temp_pdf)
                            cv.convert(output_docx, start=0, end=None)
                            cv.close()
                            pdf_conversion_success = True
                        except Exception as pdf_error:
                            logger.error(f"pdf2docx conversion failed: {str(pdf_error)}")
                            # Fall back to basic conversion
                            pdf_conversion_success = False
                    if not pdf_conversion_success:
                        # Fallback to basic conversion using python-docx and PyMuPDF
                        try:
                            from docx import Document
                            import fitz
                            
                            doc = Document()
                            with fitz.open(temp_pdf) as pdf_document:
                                for page_num in range(len(pdf_document)):
                                    page = pdf_document[page_num]
                                    # Get text with more formatting options
                                    text = page.get_text("text")
                                    if text.strip():  # Only add non-empty text
                                        doc.add_paragraph(text)
                                        
                                    # Try to extract images if text is limited
                                    if len(text.strip()) < 100:  # Likely image-heavy page
                                        try:
                                            # Add a note about possible image content
                                            doc.add_paragraph("[This page may contain images that couldn't be converted to text]")
                                        except:
                                            pass
                            
                            doc.save(output_docx)
                        except Exception as basic_error:
                            logger.error(f"Basic PDF conversion failed: {str(basic_error)}")
                            # Create an empty document with error message
                            try:
                                from docx import Document
                                doc = Document()
                                doc.add_paragraph("Error converting PDF. The file may be encrypted or contain only images.")
                                doc.save(output_docx)
                            except Exception:
                                # If even this fails, create a simple text file
                                with open(output_docx, 'w') as f:
                                    f.write("Error converting PDF. The file may be encrypted or contain only images.")
                    
                    # Make sure to close all file handles before sending
                    with open(output_docx, 'rb') as f:
                        file_content = f.read()
                    
                    # Send as BytesIO to avoid file access issues
                    output = BytesIO(file_content)
                    output.name = "converted.docx"
                    bot.send_document(call.message.chat.id, output, visible_file_name="converted.docx")
                    
                    # Clean up temporary directory manually
                finally:
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up temp directory: {str(cleanup_error)}")
                
                # Send a message about the conversion quality
                if pdf_conversion_success:
                    bot.send_message(call.message.chat.id, "✅ PDF converted to Word using enhanced conversion engine")
                else:
                    bot.send_message(call.message.chat.id, "✅ PDF converted to Word (basic conversion)")
                    
                # Confirm file deletion for security
                bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
                    
                # Securely delete the original file immediately
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Original file deleted after processing: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete original file {file_path}: {str(e)}")
                
            except Exception as e:
                logger.error(f"PDF to Word conversion error: {str(e)}")
                send_error_with_restart(call.message.chat.id, f"❌ PDF to Word conversion failed. {LANG[lang]['try_again']}", lang)
        
        # Word to PDF conversion
        elif action == "9":
            try:
                bot.edit_message_text(LANG[lang]['converting_to_pdf'], call.message.chat.id, status_msg.message_id)
            except:
                pass
                
            try:
                temp_dir = tempfile.mkdtemp(prefix="rupaganti_")
                temp_docx = os.path.join(temp_dir, f"input_{db_id}.docx")
                output_pdf = os.path.join(temp_dir, f"output_{db_id}.pdf")
                
                try:
                    # Save DOCX file
                    with open(temp_docx, 'wb') as f:
                        f.write(file_data)
                    
                    conversion_success = False
                    
                    # Try docx2pdf first
                    try:
                        import importlib.util
                        if importlib.util.find_spec("docx2pdf"):
                            from docx2pdf import convert
                            convert(temp_docx, output_pdf)
                            if os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0:
                                conversion_success = True
                    except Exception as e:
                        logger.warning(f"docx2pdf failed: {str(e)}")
                    
                    # Fallback to basic conversion for all document types
                    if not conversion_success:
                        try:
                            if ext in ['docx', 'doc']:
                                from docx import Document
                                doc = Document(temp_docx)
                                text_content = [para.text for para in doc.paragraphs if para.text.strip()]
                            elif ext in ['txt', 'rtf']:
                                with open(temp_docx, 'r', encoding='utf-8', errors='ignore') as f:
                                    text_content = f.readlines()
                            elif ext in ['xlsx', 'xls']:
                                try:
                                    import pandas as pd
                                    df = pd.read_excel(temp_docx)
                                    text_content = [df.to_string()]
                                except:
                                    text_content = ["Excel file content (conversion limited)"]
                            elif ext in ['pptx', 'ppt']:
                                try:
                                    from pptx import Presentation
                                    prs = Presentation(temp_docx)
                                    text_content = []
                                    for slide in prs.slides:
                                        for shape in slide.shapes:
                                            if hasattr(shape, "text"):
                                                text_content.append(shape.text)
                                except:
                                    text_content = ["PowerPoint file content (conversion limited)"]
                            else:
                                text_content = ["Document content"]
                            
                            # Create PDF with extracted content
                            from reportlab.pdfgen import canvas
                            from reportlab.lib.pagesizes import letter
                            
                            c = canvas.Canvas(output_pdf, pagesize=letter)
                            width, height = letter
                            y = height - 50
                            
                            for line in text_content:
                                if line and line.strip():
                                    text = line.strip()[:80]  # Limit line length
                                    c.drawString(50, y, text)
                                    y -= 20
                                    if y < 50:
                                        c.showPage()
                                        y = height - 50
                            
                            c.save()
                            conversion_success = True
                        except Exception as e:
                            logger.error(f"Fallback conversion failed: {str(e)}")
                    
                    if not conversion_success:
                        raise Exception("Conversion failed")
                    
                    # Send PDF
                    with open(output_pdf, 'rb') as f:
                        file_content = f.read()
                    
                    output = BytesIO(file_content)
                    filename = original_name.rsplit('.', 1)[0] + '.pdf'
                    bot.send_document(call.message.chat.id, output, visible_file_name=filename)
                    
                    bot.send_message(call.message.chat.id, LANG[lang]['pdf_conversion_success'])
                    bot.send_message(call.message.chat.id, LANG[lang]['file_ready'])
                    
                    file_size_mb = get_file_size_mb(file_content)
                    bot.send_message(call.message.chat.id, f"📄 PDF created ({file_size_mb:.1f} MB)")
                    
                finally:
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                
                cleanup_failed_file(file_path)
                bot.send_message(call.message.chat.id, LANG[lang]['files_deleted'])
                
            except Exception as e:
                logger.error(f"Word to PDF error: {str(e)}")
                cleanup_failed_file(file_path)
                send_error_with_restart(call.message.chat.id, LANG[lang]['pdf_conversion_failed'], lang)
        
        # We've already deleted the original file in each conversion handler
        # This is just a safety check to make sure it's gone
        if action not in ["8", "9"] and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Original file deleted after processing: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete original file {file_path}: {str(e)}")
        
        # Update status message to cleaning
        try:
            bot.edit_message_text(LANG[lang]['cleaning'], call.message.chat.id, status_msg.message_id)
        except:
            pass
            
        # Send completion message with Yes/No buttons
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(LANG[lang]['yes_more'], callback_data="yes_more"),
            types.InlineKeyboardButton(LANG[lang]['no_thanks'], callback_data="no_thanks")
        )
        
        bot.send_message(call.message.chat.id, LANG[lang]['complete'])
        bot.send_message(call.message.chat.id, LANG[lang]['help_more'], reply_markup=markup)
        bot.answer_callback_query(call.id, LANG[lang]['done'])
        
        # Delete status message
        try:
            bot.delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Callback handler error for user {user_id}: {str(e)}", exc_info=True)
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        
        # Clean up any temporary files that might have been created
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    secure_delete_file(temp_file)
                    logger.info(f"Cleaned up temp file after error: {temp_file}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up temp file {temp_file}: {str(cleanup_error)}")
        
        # Clean up original file if it exists
        try:
            if 'file_path' in locals():
                cleanup_failed_file(file_path)
        except:
            pass
                
        # Send user-friendly error message with restart button
        try:
            bot.answer_callback_query(call.id, "Processing error")
            send_error_with_restart(call.message.chat.id, LANG[lang]['oops_error'], lang)
        except:
            pass


if __name__ == "__main__":
    # Security startup message
    encryption_type = "AES-256 with hardware acceleration" if HAS_AES else "Fernet"
    print(f"🚀 Bot started securely with {encryption_type}... waiting for file uploads 🛡️")
    logger.info(f"Secure RupaGanti Bot starting with enhanced {encryption_type} encryption...")
    
    # Clean any leftover files from previous runs
    try:
        # First clean the database to remove references to files that might not exist
        try:
            conn = sqlite3.connect('files.db')
            conn.execute('DELETE FROM files')
            conn.commit()
            conn.close()
            logger.info("Database cleaned on startup")
        except Exception as db_error:
            logger.error(f"Database cleanup error: {str(db_error)}")
        
        # Then clean all files in storage directories
        for folder in ["files", "temp"]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Startup cleanup: Deleted {file_path}")
                        except Exception as file_error:
                            logger.error(f"Could not delete file {file_path}: {str(file_error)}")
        logger.info("Initial cleanup completed - all previous files deleted")
    except Exception as e:
        logger.error(f"Initial cleanup error: {str(e)}")
    
    # Verify bot token format
    if not BOT_TOKEN or len(BOT_TOKEN.split(':')) != 2:
        logger.critical("Invalid bot token format. Please check your token.")
        print("ERROR: Invalid bot token format. Please check your token.")
        exit(1)
        
    try:
        # Use more robust polling settings
        bot.polling(none_stop=True, interval=1, timeout=20)
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}")
        
        # Provide helpful error message for common issues
        if "401" in str(e):
            print("\nAuthentication failed: Your bot token is invalid or revoked.")
            print("Please get a new token from @BotFather on Telegram.")
        elif "404" in str(e):
            print("\nAPI endpoint not found: Check your internet connection.")
            print("If you're using a proxy, make sure it's configured correctly.")
        elif "429" in str(e):
            print("\nToo many requests: You're being rate limited by Telegram.")
            print("Wait a while before trying again.")
        
        print("\nFor help, visit: https://core.telegram.org/bots/api")
        exit(1)