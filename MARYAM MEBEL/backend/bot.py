# -*- coding: utf-8 -*-
"""
Merged Application: Web Application with Integrated Telegram Bot
This application combines the web interface and Telegram bot functionality
into a single cohesive system with enhanced UX-friendly error handling.
"""

# Flask web application components
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_session import Session
import os
import json
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid
import subprocess
import sys
import time
import threading

# Telegram bot components
import logging
import io
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)

# PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Environment variables
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURATION ---
CONFIG = {
    "BOT_TOKEN": os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc'),
    "ADMIN_IDS": [5559190705, 5399658464],
    "EMPLOYER_ID": 5399658464,
    "CHANNELS": ["@SpikoAI",],
    "TOPICS": {
        "buyurtma": "📦 Buyurtma holati", "texnik": "⚙️ Texnik yordam",
        "hamkorlik": "🤝 Hamkorlik", "taklif": "💡 Taklif va shikoyat",
    },
    "TOPIC_ADMINS": { "buyurtma": [], "texnik": [], "hamkorlik": [], "taklif": [] }
}
PANEL_PAGE_SIZE = 5

# --- FLASK APPLICATION SETUP ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'maryam_furniture_secret_key_2025')
app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'filesystem')
Session(app)
VACANCY_STATE = {}

# Login manager for web interface
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sahifaga kirish uchun tizimga kirishingiz kerak.'
login_manager.login_message_category = 'info'

# File upload configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
PRODUCTS_FOLDER = 'templates/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCTS_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# --- DATABASE SETUP ---
def setup_database():
    """Setup SQLite database for bot functionality"""
    conn = sqlite3.connect("support_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, status TEXT DEFAULT 'active', vip_status BOOLEAN DEFAULT 0, notes TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic TEXT, status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, assigned_admin_id INTEGER, rating INTEGER, FOREIGN KEY (user_id) REFERENCES users (user_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS forwarded_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, admin_id INTEGER, message_id INTEGER, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS messages (message_db_id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, sender_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")
    conn.commit()
    return conn

db_connection = setup_database()

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---

# File handling
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Product management
def load_products():
    try:
        with open('data/products.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            products = json.loads(content)
            for product in products:
                if 'price' not in product: product['price'] = 0
                if 'discount' not in product: product['discount'] = 0
                if 'is_active' not in product: product['is_active'] = True
                if 'id' not in product: product['id'] = str(uuid.uuid4())
            return products
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("Warning: products.json contains invalid JSON. Returning empty product list.")
        return []

def save_products(products):
    for product in products:
        if 'price' not in product: product['price'] = 0
        if 'discount' not in product: product['discount'] = 0
        if 'is_active' not in product: product['is_active'] = True
        if 'id' not in product: product['id'] = str(uuid.uuid4())
    with open('data/products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_messages():
    try:
        with open('data/messages.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content: return []
            return json.loads(content)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("Warning: messages.json contains invalid JSON. Returning empty message list.")
        return []

def save_message(message_data):
    messages = load_messages()
    message_data['id'] = len(messages) + 1
    message_data['timestamp'] = datetime.now().isoformat()
    message_data['read'] = False
    messages.append(message_data)
    with open('data/messages.json', 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# Telegram bot helper functions
def is_admin(user_id): 
    return user_id in CONFIG["ADMIN_IDS"]

def check_subscription(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    try:
        for channel in CONFIG["CHANNELS"]:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: 
                return False
        return True
    except Exception as e:
        logger.error(f"Kanalni tekshirishda xatolik: {e}")
        # UX-friendly: Allow user to proceed if there's an error checking subscription
        return True

def get_user_profile_text(user_id: int) -> str:
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user_data = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), MAX(created_at) FROM tickets WHERE user_id=?", (user_id,))
    tickets_data = cursor.fetchone()
    
    if not user_data: 
        # UX-friendly error handling
        return "❌ Foydalanuvchi topilmadi. Iltimos, botni qayta ishga tushiring: /start"
    
    try:
        user_link = f"<a href='tg:#user?id={user_data[0]}'>{user_data[1]}</a>"
        profile = f"👤 <b>Foydalanuvchi Profili</b>\n- <b>Ismi:</b> {user_link}\n- <b>Murojaatlar soni:</b> {tickets_data[0]}\n- <b>Oxirgi murojaat:</b> {tickets_data[1].split()[0] if tickets_data[1] else 'N/A'}\n- <b>Statusi:</b> {'⭐ VIP' if user_data[4] else 'Oddiy'}\n"
        if user_data[5]: 
            profile += f"- <b>Eslatma:</b> <i>{user_data[5]}</i>\n"
        return profile
    except Exception as e:
        logger.error(f"Error generating user profile: {e}")
        return "❌ Profil ma'lumotlarini olishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."

def generate_and_send_pdf(context: CallbackContext, user):
    user_data = context.user_data.get('vacancy_info', {})
    if not user_data: 
        logger.warning("No vacancy data found for PDF generation")
        return
    
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Setup font
        try:
            # Use absolute path for font file
            project_root = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(project_root, 'DejaVuSans.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                main_font = 'DejaVuSans'
            else:
                logger.warning("DejaVuSans.ttf font file not found, using default font")
                main_font = "Helvetica"
        except Exception as e:
            logger.warning(f"DejaVuSans.ttf shrifti topilmadi: {e}. Standart shrift ishlatiladi.")
            main_font = "Helvetica"
        
        def draw_multiline_text(text, x, y):
            lines = text.split('\n')
            line_height = 14
            for line in lines: 
                p.drawString(x, y, line)
                y -= line_height
            return y
        
        p.setFont(main_font, 16)
        p.drawString(100, 750, f"Yangi Nomzod: {user_data.get('name', 'N/A')}")
        p.line(100, 748, 500, 748)
        y = 720
        p.setFont(main_font, 12)
        
        fields = {
            "To'liq Ism-sharifi": user_data.get('name'), 
            "Telefon raqami": user_data.get('phone'), 
            "Yashash joyi": user_data.get('region'), 
            "Lavozim": user_data.get('position'), 
            "Oilaviy holati": user_data.get('status'), 
            "Ko'nikmalari": user_data.get('skills'), 
            "Qiziqishlari": user_data.get('interests'), 
            "Motivatsiya": user_data.get('reason'),
        }
        
        for key, value in fields.items():
            if value: 
                p.setFont(main_font, 10)
                p.drawString(100, y, key)
                p.setFont(main_font, 12)
                y = draw_multiline_text(value, 120, y - 15)
                y -= 15
        
        p.showPage()
        p.save()
        buffer.seek(0)
        
        # Send document with error handling
        try:
            # Use the bot from the context properly
            context.bot.send_document(
                chat_id=CONFIG['EMPLOYER_ID'], 
                document=buffer, 
                filename=f"Rezyume_{user_data.get('name', 'nomzod')}.pdf", 
                caption=f"Yangi nomzoddan rezyume.\nIsmi: {user_data.get('name')}\nLavozim: {user_data.get('position')}"
            )
            logger.info(f"PDF successfully sent for user: {user_data.get('name')}")
        except Exception as e:
            logger.error(f"Error sending PDF document: {e}")
            # Try to notify the user about the issue
            try:
                context.bot.send_message(
                    chat_id=getattr(user, 'id', CONFIG['EMPLOYER_ID']),
                    text="⚠️ Rezyumeingizni HR bo'limiga yuborishda texnik xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
                )
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        # UX-friendly error handling - notify user
        try:
            context.bot.send_message(
                chat_id=getattr(user, 'id', CONFIG['EMPLOYER_ID']),
                text="❌ Rezyumeingizni tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring yoki administratorga murojaat qiling."
            )
        except:
            pass

# --- FLASK ROUTES ---

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # UX-friendly validation
        if not username or not password:
            flash('❌ Iltimos, barcha maydonlarni to\'ldiring!', 'error')
            return render_template('auth/login.html')
        
        # In a real implementation, you would validate against your user database
        # For now, we'll use a simple check
        if username == os.environ.get('ADMIN_USERNAME', 'admin') and password == os.environ.get('ADMIN_PASSWORD', 'maryam2025'):
            # Simulate login success
            flash('✅ Tizimga muvaffaqiyatli kirdingiz!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('❌ Noto\'g\'ri login yoki parol!', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('✅ Tizimdan muvaffaqiyatli chiqildi.', 'info')
    return redirect(url_for('index'))

# --- TELEGRAM BOT HANDLERS ---

def start(update: Update, context: CallbackContext):
    """UX-enhanced start command with better error handling"""
    try:
        user = update.effective_user
        cursor = db_connection.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", 
                      (user.id, user.first_name, user.username))
        db_connection.commit()
        
        # UX-friendly welcome message with clear instructions
        welcome_message = (
            "👋 Assalomu alaykum! Botimizga xush kelibsiz!\n\n"
            "📋 <b>Asosiy menyumiz:</b>\n"
            "• <b>✍️ Murojaat yuborish</b> - Savolingizni yozing\n"
            "• <b>📄 Vakansiyalar</b> - Ishga joylashish uchun ariza topshiring\n"
            "• <b>💬 Mening chatlarim</b> - Oldingi murojaatlaringiz tarixi\n"
            "• <b>📦 Buyurtma berish</b> - Mahsulot buyurtma qiling\n"
            "• <b>📂 Katalog</b> - Mahsulotlarimiz bilan tanishing\n\n"
            "Tanlovingizni quyidagi tugmalar orqali amalga oshiring:"
        )
        
        keyboard = ReplyKeyboardMarkup([
            ["✍️ Murojaat yuborish"],
            ["📄 Vakansiyalar", "💬 Mening chatlarim"],
            ["📦 Buyurtma berish", "📂 Katalog"]
        ], resize_keyboard=True)
        
        update.message.reply_text(welcome_message, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "⚠️ Kechirasiz, botni ishga tushirishda xatolik yuz berdi. "
                "Iltimos, bir ozdan so'ng qayta urinib ko'ring: /start"
            )
        except:
            pass

def open_support_menu(update: Update, context: CallbackContext):
    """Enhanced support menu with better error handling"""
    try:
        if not check_subscription(update, context):
            channels_text = "\n".join(CONFIG["CHANNELS"])
            keyboard = [[InlineKeyboardButton("✅ A'zo bo'ldim", callback_data="check_sub")]]
            update.message.reply_text(
                f"⚠️ Murojaat yuborish uchun quyidagi kanallarga a'zo bo'ling:\n\n{channels_text}\n\n"
                "A'zo bo'lganingizdan so'ng \"✅ A'zo bo'ldim\" tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        show_topic_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error opening support menu: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "❌ Murojaat menyusini ochishda xatolik yuz berdi. "
                "Iltimos, /start buyrug'i orqali bosh menyuga qayting."
            )
        except:
            pass

def show_topic_menu(update: Update, context: CallbackContext, chat_id=None, is_edit=False):
    """Enhanced topic menu with better UX"""
    try:
        keyboard = []
        for key, value in CONFIG["TOPICS"].items():
            keyboard.append([InlineKeyboardButton(value, callback_data=f"topic_{key}")])
        
        keyboard.append([InlineKeyboardButton("💬 Mening chatlarim", callback_data="my_chats")])
        keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])
        
        text = (
            "📝 <b>Murojaatingiz mavzusini tanlang:</b>\n\n"
            "• <b>📦 Buyurtma holati</b> - Buyurtmangizni kuzatish\n"
            "• <b>⚙️ Texnik yordam</b> - Texnik savollar\n"
            "• <b>🤝 Hamkorlik</b> - Hamkorlik takliflari\n"
            "• <b>💡 Taklif va shikoyat</b> - Taklif va shikoyatlaringiz\n\n"
            "Yoki \"💬 Mening chatlarim\" orqali oldingi murojaatlaringizni ko'ring:"
        )
        
        effective_chat_id = chat_id or (update.effective_chat.id if update else None)
        
        if is_edit:
            try:
                update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            except:
                context.bot.send_message(effective_chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            try:
                update.message.delete()
            except:
                pass
            context.bot.send_message(effective_chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logger.error(f"Error showing topic menu: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "❌ Mavzular menyusini ochishda xatolik yuz berdi. "
                "Iltimos, /start buyrug'i orqali qayta urinib ko'ring."
            )
        except:
            pass

# --- VACANCY CONVERSATION HANDLERS ---

(GET_NAME, GET_PHONE, GET_REGION, GET_SKILLS, GET_INTERESTS, GET_POSITION, GET_STATUS, GET_REASON) = range(8)

def vacancy_start(update: Update, context: CallbackContext):
    """Enhanced vacancy start with better instructions"""
    try:
        context.user_data['vacancy_info'] = {}
        update.message.reply_text(
            "📋 <b>Rezyume to'ldirishni boshladik!</b>\n\n"
            "Iltimos, quyidagi savollarga javob bering:\n\n"
            "1️⃣ <b>To'liq ism-sharifingizni yozing:</b>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML
        )
        return GET_NAME
    except Exception as e:
        logger.error(f"Error starting vacancy process: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "❌ Rezyume to'ldirish jarayonini boshlashda xatolik yuz berdi. "
                "Iltimos, /start buyrug'i orqali qayta urinib ko'ring."
            )
        except:
            pass
        return ConversationHandler.END

def get_name(update: Update, context: CallbackContext):
    """Enhanced name collection with validation"""
    try:
        name = update.message.text.strip()
        
        # UX-friendly validation
        if not name or len(name) < 3:
            update.message.reply_text(
                "⚠️ Iltimos, to'liq ism-sharifingizni kiriting (kamida 3 ta belgi):"
            )
            return GET_NAME
        
        context.user_data['vacancy_info']['name'] = name
        
        keyboard = [[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]]
        update.message.reply_text(
            f"✅ Rahmat, {name}!\n\n"
            "2️⃣ Endi telefon raqamingizni yuboring:\n"
            "👉 '📞 Raqamni yuborish' tugmasini bosing",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return GET_PHONE
    except Exception as e:
        logger.error(f"Error collecting name: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "❌ Ism-sharifingizni saqlashda xatolik yuz berdi. "
                "Iltimos, qayta urinib ko'ring:"
            )
        except:
            pass
        return GET_NAME

def get_phone(update: Update, context: CallbackContext):
    """Enhanced phone collection with validation"""
    try:
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
        elif update.message.text:
            phone = update.message.text.strip()
        
        # UX-friendly validation
        if not phone or len(phone) < 9:
            update.message.reply_text(
                "⚠️ Iltimos, to'g'ri telefon raqamini yuboring:\n"
                "👉 '📞 Raqamni yuborish' tugmasini bosing yoki raqamni matn shaklida yozing"
            )
            return GET_PHONE
        
        context.user_data['vacancy_info']['phone'] = phone
        update.message.reply_text(
            "✅ Raqam qabul qilindi!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        regions = [
            "Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", 
            "Farg'ona", "Jizzax", "Xorazm", "Namangan", "Navoiy", 
            "Qashqadaryo", "Samarqand", "Sirdaryo", "Surxondaryo", "Qoraqalpog'iston"
        ]
        keyboard = [[InlineKeyboardButton(r, callback_data=f"region_{r}")] for r in regions]
        
        update.message.reply_text(
            "3️⃣ Yashash joyingizni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GET_REGION
    except Exception as e:
        logger.error(f"Error collecting phone: {e}")
        # UX-friendly error handling
        try:
            update.message.reply_text(
                "❌ Telefon raqamingizni saqlashda xatolik yuz berdi. "
                "Iltimos, qayta urinib ko'ring:"
            )
        except:
            pass
        return GET_PHONE

def get_region(update: Update, context: CallbackContext):
    """Handle region selection"""
    try:
        query = update.callback_query
        region = query.data.split('_', 1)[1]
        context.user_data['vacancy_info']['region'] = region
        query.answer()
        
        query.edit_message_text(
            "4️⃣ Ko'nikmalaringizni yozing (masalan: Kompyuter savodxonligi, Payvandlash, Sotuv...):"
        )
        return GET_SKILLS
    except Exception as e:
        logger.error(f"Error collecting region: {e}")
        try:
            update.callback_query.answer(
                "❌ Hududni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                show_alert=True
            )
        except:
            pass
        return GET_REGION

def get_skills(update: Update, context: CallbackContext):
    """Handle skills collection"""
    try:
        skills = update.message.text.strip()
        
        # UX-friendly validation
        if not skills or len(skills) < 3:
            update.message.reply_text(
                "⚠️ Iltimos, kamida 3 ta ko'nikmani kiriting:"
            )
            return GET_SKILLS
        
        context.user_data['vacancy_info']['skills'] = skills
        update.message.reply_text(
            "5️⃣ Qiziqishlaringizni yozing (masalan: Kitob o'qish, Futbol, Dasturlash...):"
        )
        return GET_INTERESTS
    except Exception as e:
        logger.error(f"Error collecting skills: {e}")
        try:
            update.message.reply_text(
                "❌ Ko'nikmalaringizni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring:"
            )
        except:
            pass
        return GET_SKILLS

def get_interests(update: Update, context: CallbackContext):
    """Handle interests collection"""
    try:
        interests = update.message.text.strip()
        
        # UX-friendly validation
        if not interests or len(interests) < 3:
            update.message.reply_text(
                "⚠️ Iltimos, kamida 3 ta qiziqishni kiriting:"
            )
            return GET_INTERESTS
        
        context.user_data['vacancy_info']['interests'] = interests
        
        positions = [
            "Oddiy ishchi", "Omborchi", "Haydovchi", "Mebel ustasi", 
            "Sotuv menejeri", "Buxgalter", "HR menejeri", "Bo'lim boshlig'i", "Direktor (CEO)"
        ]
        keyboard = [[InlineKeyboardButton(p, callback_data=f"pos_{p}")] for p in positions]
        
        update.message.reply_text(
            "6️⃣ Qaysi lavozimga qiziqasiz?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GET_POSITION
    except Exception as e:
        logger.error(f"Error collecting interests: {e}")
        try:
            update.message.reply_text(
                "❌ Qiziqishlaringizni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring:"
            )
        except:
            pass
        return GET_INTERESTS

def get_position(update: Update, context: CallbackContext):
    """Handle position selection"""
    try:
        query = update.callback_query
        position = query.data.split('_', 1)[1]
        context.user_data['vacancy_info']['position'] = position
        query.answer()
        
        statuses = ["Kambag'al", "O'rta hol", "Yaxshi", "Boy"]
        keyboard = [[InlineKeyboardButton(s, callback_data=f"status_{s}")] for s in statuses]
        
        query.edit_message_text(
            "7️⃣ Moddiy holatingizni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GET_STATUS
    except Exception as e:
        logger.error(f"Error collecting position: {e}")
        try:
            update.callback_query.answer(
                "❌ Lavozimni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                show_alert=True
            )
        except:
            pass
        return GET_POSITION

def get_status(update: Update, context: CallbackContext):
    """Handle status selection"""
    try:
        query = update.callback_query
        status = query.data.split('_', 1)[1]
        context.user_data['vacancy_info']['status'] = status
        query.answer()
        
        query.edit_message_text(
            "8️⃣ Nima uchun aynan bizning kompaniyamizda ishlashni xohlaysiz? Qisqacha yozing."
        )
        return GET_REASON
    except Exception as e:
        logger.error(f"Error collecting status: {e}")
        try:
            update.callback_query.answer(
                "❌ Holatni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                show_alert=True
            )
        except:
            pass
        return GET_STATUS

def get_reason(update: Update, context: CallbackContext):
    """Handle reason collection and complete vacancy process"""
    try:
        reason = update.message.text.strip()
        
        # UX-friendly validation
        if not reason or len(reason) < 10:
            update.message.reply_text(
                "⚠️ Iltimos, kamida 10 ta belgi kiriting:"
            )
            return GET_REASON
        
        context.user_data['vacancy_info']['reason'] = reason
        update.message.reply_text(
            "✅ Murojaatingiz qabul qilindi! Ma'lumotlaringiz kadrlar bo'limiga yuborildi. Tez orada siz bilan bog'lanamiz.",
            reply_markup=ReplyKeyboardMarkup([
                ["✍️ Murojaat yuborish"],
                ["📄 Vakansiyalar", "💬 Mening chatlarim"],
                ["📦 Buyurtma berish", "📂 Katalog"]
            ], resize_keyboard=True)
        )
        
        # Generate and send PDF
        generate_and_send_pdf(context, update.effective_user)
        context.user_data.pop('vacancy_info', None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error collecting reason: {e}")
        try:
            update.message.reply_text(
                "❌ Arizangizni yakunlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring:"
            )
        except:
            pass
        return GET_REASON

# --- BOT ERROR HANDLING ---

def error_handler(update: object, context: CallbackContext):
    """Global error handler with UX-friendly responses"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Try to notify the user about the error in a friendly way
    try:
        if update and hasattr(update, 'message') and update.message:
            update.message.reply_text(
                "⚠️ Kechirasiz, so'rovingizni bajarishda kutilmagan xatolik yuz berdi.\n"
                "Muammo bizning jamoamiz tomonidan hal etilmoqda.\n"
                "Iltimos, bir ozdan so'ng qayta urinib ko'ring yoki /start orqali bosh menyuga qayting."
            )
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            update.callback_query.answer(
                "⚠️ Kechirasiz, amaliyotda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                show_alert=True
            )
    except:
        pass

# --- BOT INITIALIZATION ---

def init_bot():
    """Initialize and start the Telegram bot"""
    try:
        updater = Updater(CONFIG["BOT_TOKEN"], use_context=True)
        dp = updater.dispatcher

        # Add conversation handler for vacancies with enhanced error handling
        vacancy_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(Filters.regex('^📄 Vakansiyalar$'), vacancy_start)],
            states={
                GET_NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
                GET_PHONE: [MessageHandler(Filters.contact | Filters.text, get_phone)],
                GET_REGION: [CallbackQueryHandler(get_region, pattern="^region_")],
                GET_SKILLS: [MessageHandler(Filters.text & ~Filters.command, get_skills)],
                GET_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, get_interests)],
                GET_POSITION: [CallbackQueryHandler(get_position, pattern="^pos_")],
                GET_STATUS: [CallbackQueryHandler(get_status, pattern="^status_")],
                GET_REASON: [MessageHandler(Filters.text & ~Filters.command, get_reason)],
            },
            fallbacks=[
                CommandHandler('start', start), 
                CommandHandler('cancel', cancel_vacancy),
                MessageHandler(Filters.all, fallback_handler)
            ],
            # UX enhancement: Allow conversation to continue after timeout
            conversation_timeout=300,  # 5 minutes
            # UX enhancement: Handle errors gracefully
        )

        # Register handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.regex('^✍️ Murojaat yuborish$'), open_support_menu))
        dp.add_handler(vacancy_conv_handler)  # Add the vacancy conversation handler
        
        # Add global error handler
        dp.add_error_handler(error_handler)
        
        # Start the bot
        updater.start_polling()
        logger.info("Telegram bot started successfully")
        
        return updater
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        return None

def fallback_handler(update: Update, context: CallbackContext):
    """Fallback handler for unhandled messages with UX-friendly response"""
    try:
        update.message.reply_text(
            "🤔 Kechirasiz, sizning so'rovingizni tushunmadim.\n\n"
            "Quyidagi variantlardan birini tanlang:\n"
            "• /start - Bosh menyuni ochish\n"
            "• Yoki menyudagi tugmalardan birini bosing"
        )
    except:
        pass

def cancel_vacancy(update: Update, context: CallbackContext):
    """Enhanced cancel handler with confirmation"""
    try:
        update.message.reply_text(
            "✅ Rezyume to'ldirish bekor qilindi.\n"
            "Bosh menyudasiz. Kerakli bo'limni tanlang:",
            reply_markup=ReplyKeyboardMarkup([
                ["✍️ Murojaat yuborish"],
                ["📄 Vakansiyalar", "💬 Mening chatlarim"],
                ["📦 Buyurtma berish", "📂 Katalog"]
            ], resize_keyboard=True)
        )
        context.user_data.pop('vacancy_info', None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error cancelling vacancy: {e}")
        try:
            update.message.reply_text("✅ Jarayon bekor qilindi.")
        except:
            pass
        return ConversationHandler.END

# --- APPLICATION STARTUP ---

def start_bot_thread():
    """Start the Telegram bot in a separate thread"""
    def run():
        bot_updater = init_bot()
        if bot_updater:
            bot_updater.idle()
    
    bot_thread = threading.Thread(target=run, name="TelegramBot")
    bot_thread.daemon = True
    bot_thread.start()
    return bot_thread

if __name__ == '__main__':
    # Start the Telegram bot in a separate thread
    bot_thread = start_bot_thread()
    
    # Start the Flask web server
    app.run(debug=True, host='0.0.0.0', port=5000)