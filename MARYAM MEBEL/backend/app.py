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
import io
import logging

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Table, TableStyle # For creating perfectly aligned tables
    from reportlab.lib import colors # For styling the table with colors
except ImportError as e:
    logger.warning(f"ReportLab libraries not available: {e}")
    # Define placeholder classes if needed so the app doesn't crash
    Table = None
    TableStyle = None



# Add mock for urllib3.contrib.appengine to prevent import errors
try:
    import urllib3.contrib.appengine
except ImportError:
    # Create a mock module for urllib3.contrib.appengine
    class MockAppEngineManager:
        def __init__(self, *args, **kwargs):
            pass

    # Create a mock module
    import sys
    import types
    mock_module = types.ModuleType('urllib3.contrib.appengine')
    mock_module.AppEngineManager = MockAppEngineManager
    mock_module.IS_APP_ENGINE = False
    mock_module.IS_APP_ENGINE_SANDBOX = False
    if 'urllib3.contrib.appengine' not in sys.modules:
        sys.modules['urllib3.contrib.appengine'] = mock_module

# Add fallback for imghdr module (deprecated in Python 3.12)
try:
    import imghdr
    IMGHDR_AVAILABLE = True
except ImportError:
    IMGHDR_AVAILABLE = False
    logging.warning("imghdr library not available (deprecated in Python 3.12), using filetype library instead")

    # Create a mock imghdr module to prevent dependencies from failing
    class MockImgHdr:
        @staticmethod
        def what(filepath):
            # Use our custom implementation if filetype is available
            if FILETYPE_AVAILABLE:
                try:
                    import filetype
                    kind = filetype.guess(filepath)
                    if kind is None:
                        return None
                    return kind.extension
                except Exception:
                    return None
            # If filetype is not available, return None
            return None

    # Add the mock module to sys.modules so other libraries can import it
    import sys
    if 'imghdr' not in sys.modules:
        sys.modules['imghdr'] = MockImgHdr
    imghdr = MockImgHdr

# Add custom function to replace imghdr.what() functionality
def custom_imghdr_what(filepath):
    """
    Custom implementation of imghdr.what() using filetype library.
    Returns the image type or None if not an image.
    """
    if not FILETYPE_AVAILABLE:
        return None

    try:
        import filetype
        kind = filetype.guess(filepath)
        if kind is None:
            return None
        # Return just the extension without the dot
        return kind.extension
    except Exception:
        return None

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configure logging for both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Telegram imports
try:
    import telegram
    # Try the new import structure first (python-telegram-bot v20+)
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
        from telegram.constants import ParseMode
        from telegram.ext import (
            Application as Updater,
            CommandHandler,
            MessageHandler,
            filters as Filters,
            CallbackQueryHandler,
            ConversationHandler,
            ContextTypes as CallbackContext,
        )
    except ImportError:
        # Fall back to the old import structure (python-telegram-bot v13.x)
        try:
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup, ParseMode
            from telegram.ext import (
                Updater,
                CommandHandler,
                MessageHandler,
                Filters,
                CallbackQueryHandler,
                ConversationHandler,
                CallbackContext,
            )
        except ImportError as e:
            # If we still can't import, raise the exception to be caught by the outer except
            raise e

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        logger.warning(f"ReportLab libraries not available: {e}")
        # Continue without ReportLab functionality

    TELEGRAM_AVAILABLE = True
    logger.info("Telegram libraries loaded successfully")
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    logger.error(f"Telegram libraries not available: {e}")
    logger.error("Webhook functionality will be disabled.")
    # Define placeholder classes for when Telegram is not available
    class Update:
        pass

    class CallbackContext:
        pass

    ParseMode = None

# Initialize user manager with fallback
user_manager = None
User = None
admin_bp = None
main_bp = None
init_telegram_service = None
get_telegram_service = None
average_rating = None

# Try to import user management modules
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
    from user import UserManager, User
    user_manager = UserManager('data/users.json')
    logger.info("User management modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import user management: {e}")
    # Create a simple fallback user manager
    class SimpleUser:
        def __init__(self, username, email, telegram_username, first_name, last_name):
            self.username = username
            self.email = email
            self.telegram_username = telegram_username
            self.first_name = first_name
            self.last_name = last_name

        def get_id(self):
            return self.username

        def check_password(self, password):
            return password == "password"  # Simple fallback

        @staticmethod
        def username_exists(username):
            return False

        @staticmethod
        def email_exists(email):
            return False

        @staticmethod
        def telegram_exists(telegram_username):
            return False

    class SimpleUserManager:
        def __init__(self, users_file):
            self.users_file = users_file
            self.users = {}

        def get_user_by_username(self, username):
            return self.users.get(username)

        def get_user_by_id(self, user_id):
            return self.users.get(user_id)

        def username_exists(self, username):
            return username in self.users

        def email_exists(self, email):
            return any(u.email == email for u in self.users.values())

        def telegram_exists(self, telegram_username):
            return any(u.telegram_username == telegram_username for u in self.users.values())

        def add_user(self, user):
            self.users[user.username] = user

    user_manager = SimpleUserManager('data/users.json')
    User = SimpleUser
# Try to import route modules
try:
    from routes import admin, main
    admin_bp = admin.admin_bp
    main_bp = main.main_bp
    logger.info("Route modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import routes: {e}")
    # Create simple fallback blueprints
    from flask import Blueprint
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    main_bp = Blueprint('main', __name__, url_prefix='/main')

# Try to import utility modules
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
    from telegram_service import init_telegram_service, get_telegram_service
    init_telegram_service = init_telegram_service
    get_telegram_service = get_telegram_service
    logger.info("Utility modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import utils: {e}")
    # Create simple fallback functions
    def init_telegram_service(db_path):
        return None

    def get_telegram_service():
        return None

    def average_rating(ratings):
        if not ratings:
            return sum(r['rating'] for r in ratings) / len(ratings)
        return 0

# Initialize Flask app
app = Flask(__name__)
# Set secret key before initializing Session
app.secret_key = os.environ.get('SECRET_KEY', 'maryam_furniture_secret_key_2025')
app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'filesystem')
Session(app)
VACANCY_STATE = {}

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sahifaga kirish uchun tizimga kirishingiz kerak.'
login_manager.login_message_category = 'info'

try:
    from utils import init_app as init_utils
    init_utils(app)
    logger.info("App utilities initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize app utilities: {e}")

@login_manager.user_loader
def load_user(user_id):
    if user_manager:
        return user_manager.get_user_by_id(user_id)
    return None

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
PRODUCTS_FOLDER = 'templates/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jeg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

# Register blueprints
if admin_bp:
    app.register_blueprint(admin_bp)
if main_bp:
    app.register_blueprint(main_bp)

sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCTS_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Bot Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')
logger.info(f"Bot token configured: {BOT_TOKEN[:10]}...")

# Parse ADMIN_IDS from environment variable
admin_ids_str = os.environ.get('ADMIN_IDS', '5559190705,5399658464')
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',')]

# Required channels for contest
REQUIRED_CHANNELS = {
    "@uzb_python": "https://t.me/uzb_python",
    "@prmg_uz": "https://t.me/prmg_uz"
}

# Contest information text
CONTEST_INFO_TEXT = """
🏆 <b>Konkursimiz Haqida Ma'lumot</b> 🏆

<b>Konkursning maqsadi:</b>
Eng ko'p do'stingizni botimizga taklif qilish!

<b>Konkurs muddati:</b>
31-Dekabr, 23:59 gacha

<b>Sovrinlar:</b>
🥇 1-o'rin: 1,000,000 so'm
🥈 2-o'rin: 500,000 so'm
🥉 3-o'rin: 250,000 so'm

<b>Qoidalar:</b>
1. Barcha shart bo'lgan kanallarga a'zo bo'ling.
2. O'zingizning shaxsiy havolangiz orqali do'stlaringizni taklif qiling.
3. Har bir faol taklif uchun sizga 1 ball beriladi.
4. Qo'shimcha bonuslar uchun bosqichlarni bajaring!

Omad tilaymiz! ✨
"""

# Milestones and bonuses
MILESTONES = {
    5: 2,
    10: 3,
    25: 7,
    50: 10,
    100: 15,
    200: 20,
}

CONFIG = {
    "BOT_TOKEN": BOT_TOKEN,
    "ADMIN_IDS": ADMIN_IDS,
    "ADMIN_IDS": ADMIN_IDS,
    "EMPLOYER_ID": int(os.environ.get('EMPLOYER_ID', 5399658464)),
    "CHANNELS": os.environ.get('CHANNELS', '@SpikoAI').split(','),
    "TOPICS": {
        "buyurtma": "📦 Buyurtma holati",
        "texnik": "⚙️ Texnik yordam",
        "hamkorlik": "🤝 Hamkorlik", "taklif": "💡 Taklif va shikoyat",
    },
    "TOPIC_ADMINS": { "buyurtma": [], "texnik": [], "hamkorlik": [], "taklif": [], "taklif": [] }
}
PANEL_PAGE_SIZE = 5

# Webhook Configuration
WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://your-pythonanywhere-username.pythonanywhere.com/telegram-webhook')
WEBHOOK_PORT = int(os.environ.get('TELEGRAM_WEBHOOK_PORT', 443))

# Database setup for bot
def setup_database():
    try:
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'support_bot.db')
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, status TEXT DEFAULT 'active', vip_status BOOLEAN DEFAULT 0, notes TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic TEXT, status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, assigned_admin_id INTEGER, rating INTEGER, FOREIGN KEY (user_id) REFERENCES users (user_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS forwarded_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, admin_id INTEGER, message_id INTEGER, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS messages (message_db_id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, sender_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")

        # Add contest-related tables and columns
        # Add referral_count and referrer_id columns to users table
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        except sqlite3.OperationalError:
            pass # Column already exists

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN milestones_achieved TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass # Column already exists

        # Create a separate table for contest information if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contest_info (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                contest_active BOOLEAN DEFAULT 1,
                contest_end_date TEXT
            )
        """)

        # Insert default contest info if not exists
        cursor.execute("INSERT OR IGNORE INTO contest_info (id, contest_active, contest_end_date) VALUES (1, 1, '2025-12-31')")

        conn.commit()
        logger.info("Database setup completed successfully")
        return conn
    except Exception as e:
        logger.error(f"Failed to setup database: {e}")
        return None

# Initialize database with the correct path
db_connection = setup_database()

# Helper functions
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
        logger.error(f"Kanalni tekshirishda xatolik: {e}");
        return True

# --- Contest Helper Functions ---

def check_and_award_milestones(referrer_id: int, new_score: int, context: CallbackContext):
    """Foydalanuvchining bosqichlardan o'tganligini tekshiradi va bonus beradi."""
    if not db_connection:
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT milestones_achieved FROM users WHERE user_id = ?", (referrer_id,))
        result = cursor.fetchone()
        if not result:
            return

        achieved_str = result[0]
        achieved_list = achieved_str.split(',') if achieved_str else []

        total_bonus_awarded = 0
        newly_achieved = []

        for milestone, bonus in sorted(MILESTONES.items()):
            if new_score >= milestone and str(milestone) not in achieved_list:
                total_bonus_awarded += bonus
                newly_achieved.append(str(milestone))
                try:
                    context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 <b>Ajoyib! Siz {milestone} ta do'stingizni taklif qildingiz!</b>\n\n"
                             f"🎁 Sizga mukofot sifatida <b>+{bonus} bonus ball</b> taqdim etildi!",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.warning(f"Mukofot xabarini yuborishda xato: {e}")

        if total_bonus_awarded > 0:
            cursor.execute("UPDATE users SET referral_count = referral_count + ? WHERE user_id = ?", (total_bonus_awarded, referrer_id))

            updated_achieved_str = ",".join(achieved_list + newly_achieved)
            cursor.execute("UPDATE users SET milestones_achieved = ? WHERE user_id = ?", (updated_achieved_str, referrer_id))

            db_connection.commit()

    except Exception as e:
        logger.error(f"Error in check_and_award_milestones: {e}")

def check_contest_subscription(user_id: int, context: CallbackContext) -> list:
    """Check if user is subscribed to required contest channels"""
    unsubscribed_channels = []
    for channel_username in REQUIRED_CHANNELS.keys():
        try:
            member = context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel_username)
        except Exception as e:
            logger.error(f"Kanallar a'zoligini tekshirishda xatolik: {e} - Kanal: {channel_username}")
            unsubscribed_channels.append(channel_username)
    return unsubscribed_channels

def ask_for_contest_subscription(update: Update, context: CallbackContext, unsubscribed_channels: list):
    """Ask user to subscribe to required channels for contest"""
    user = update.effective_user
    buttons = []
    is_callback = update.callback_query and "check_contest_subscription" in update.callback_query.data
    if is_callback:
        text = f"❌ Kechirasiz, <b>{user.full_name}</b>, siz hali ham quyidagi kanallarga a'zo bo'lmadingiz:\n\n"
    else:
        text = f"Salom, <b>{user.full_name}</b>!\n\nKonkursimizda qatnashish uchun quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"

    for channel_username in unsubscribed_channels:
        channel_link = REQUIRED_CHANNELS.get(channel_username, "")
        buttons.append([InlineKeyboardButton(text=f"➡️ {channel_username}", url=channel_link)])

    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_contest_subscription")])
    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def get_user_profile_text(user_id: int) -> str:
    if not db_connection:
        return "Foydalanuvchi topilmadi."
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user_data = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), MAX(created_at) FROM tickets WHERE user_id=?", (user_id,))
        tickets_data = cursor.fetchone()
        if not user_data:
            return "Foydalanuvchi topilmadi."
        # Create a clickable link for the user's name
        user_link = f"<a href='tg://user?id={user_data[0]}'>{user_data[1] if user_data[1] else user_data[2]}</a>"
        profile = f"👤 <b>Foydalanuvchi Profili</b>\n- <b>Ismi:</b> {user_link}\n- <b>Murojaatlar soni:</b> {tickets_data[0]}\n- <b>Oxirgi murojaat:</b> {tickets_data[1].split()[0] if tickets_data[1] else 'N/A'}\n- <b>Statusi:</b> {'⭐ VIP' if user_data[4] else 'Oddiy'}\n"
        if user_data[5]:
            profile += f"- <b>Eslatma:</b> <i>{user_data[5]}</i>\n"
        return profile
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return "Foydalanuvchi ma'lumotlarini olishda xatolik."

def generate_and_send_pdf(context: CallbackContext, user):
    user_data = context.user_data.get('vacancy_info', {})
    if not user_data:
        logger.warning("No vacancy_info found in user_data to generate PDF.")
        return
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # --- Font Setup ---
        main_font = "Helvetica" # Default fallback font
        try:
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(bot_dir, 'DejaVuSans.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                main_font = 'DejaVuSans'
            else:
                 logger.warning(f"Font file not found at {font_path}. Using default font.")
        except Exception as e:
            logger.warning(f"Could not register font: {e}. Using default font.")

        # --- Title ---
        p.setFont(main_font, 18)
        p.drawString(100, 750, "Nomzod Rezyumesi")

        # --- Table Data Preparation ---
        data = [
            ["Maydon", "Qiymat"],
            ["To'liq Ism-sharifi", user_data.get('name', 'N/A')],
            ["Telefon raqami", user_data.get('phone', 'N/A')],
            ["Yashash joyi", user_data.get('region', 'N/A')],
            ["Lavozim", user_data.get('position', 'N/A')],
            ["Oilaviy holati", user_data.get('status', 'N/A')],
            ["Ko'nikmalari", user_data.get('skills', 'N/A')],
            ["Qiziqishlari", user_data.get('interests', 'N/A')],
            ["Motivatsiya", user_data.get('reason', 'N/A')],
        ]

        # --- Table Creation and Styling ---
        # Create the table object, specifying column widths
        table = Table(data, colWidths=[150, 300])

        # Define the style for the table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), # Header background color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), # Center align all cells
            ('FONTNAME', (0, 0), (-1, 0), f'{main_font}-Bold'), # Header font
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), # Header padding
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige), # Body background color
            ('FONTNAME', (0, 1), (-1, -1), main_font), # Body font
            ('GRID', (0, 0), (-1, -1), 1, colors.black) # Add grid lines
        ])

        table.setStyle(style)

        # --- Draw the Table on the Canvas ---
        # Wrap the table on the canvas and draw it
        table.wrapOn(p, 400, 600)  # These values are for sizing, not positioning
        table.drawOn(p, 100, 500)   # Position the table at x=100, y=500

        # --- Finalize PDF ---
        p.showPage()
        p.save()
        buffer.seek(0)

        # --- Send PDF ---
        context.bot.send_document(
            chat_id=CONFIG['EMPLOYER_ID'],
            document=buffer,
            filename=f"Rezyume_{user_data.get('name', 'nomzod')}.pdf",
            caption=(
                f"Yangi nomzoddan rezyume.\n"
                f"Ismi: {user_data.get('name')}\n"
                f"Lavozim: {user_data.get('position')}\n\n"
                f"Foydalanuvchi ma'lumotlari rezyume ichida."
            )
        )
        logger.info(f"PDF generated and sent for user {user.id}")

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")

def check_and_send_new_messages(context):
    """Check for new messages in the database and send them to users"""
    if not db_connection:
        return
    try:
        cursor = db_connection.cursor()
        # Get all messages that haven't been sent yet to users
        cursor.execute("""
            SELECT m.message_db_id, m.ticket_id, m.sender_id, m.sender_name, m.message_text, m.sent_at, t.user_id
            FROM messages m
            JOIN tickets t ON m.ticket_id = t.ticket_id
            WHERE t.user_id > 0
            AND m.message_db_id NOT IN (
                SELECT COALESCE(message_id, 0) FROM forwarded_messages WHERE message_id = m.message_db_id
            )
            ORDER BY m.sent_at ASC
            LIMIT 10
        """)

        messages = cursor.fetchall()

        for message_db_id, ticket_id, sender_id, sender_name, message_text, sent_at, user_id in messages:
            try:
                # Send the message to the user
                sent_message = context.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )

                # Mark the message as sent by adding it to forwarded_messages
                cursor.execute(
                    "INSERT INTO forwarded_messages (ticket_id, admin_id, message_id) VALUES (?, ?, ?)",
                    (ticket_id, sender_id, message_db_id)
                )

                db_connection.commit()
                logger.info(f"Sent message {message_db_id} to user {user_id}")

            except Exception as e:
                logger.error(f"Error sending message {message_db_id} to user {user_id}: {e}")
                # Even if we fail to send, mark it as processed to avoid infinite retries
                try:
                    cursor.execute(
                        "INSERT INTO forwarded_messages (ticket_id, admin_id, message_id) VALUES (?, ?, ?)",
                        (ticket_id, sender_id, message_db_id)
                    )
                    db_connection.commit()
                except:
                    pass

    except Exception as e:
        logger.error(f"Error checking for new messages: {e}")

def get_products_from_web():
    """Get products from the web application's products.json file"""
    try:
        # Try multiple possible locations for the products file
        possible_paths = [
            os.path.join('data', 'products.json'),  # Relative to current directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'products.json'),  # In the same directory as this file
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'products.json'),  # One level up
            '/home/sardor1ubaydiy/mysite/maryam-mebel/MARYAM MEBEL/data/products.json'  # Specific deployment path
        ]

        products_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                products_file_path = path
                break

        if not products_file_path:
            logger.warning(f"Products file not found at any of the expected locations")
            return []

        # Read products from file
        with open(products_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                logger.warning("Products file is empty")
                return []

            products = json.loads(content)
            for product in products:
                if 'price' not in product: product['price'] = 0
                if 'discount' not in product: product['discount'] = 0
                if 'is_active' not in product: product['is_active'] = True
                if 'id' not in product: product['id'] = str(uuid.uuid4())
            return products
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in products file {products_file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading products from web: {e}")
        return []

def get_unique_categories(products):
    """Get unique categories from products"""
    categories = set()
    for product in products:
        category = product.get('category')
        if category:
            categories.add(category)
    return sorted(list(categories))

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["✍️ Murojaat yuborish"],
        ["📄 Vakansiyalar", "💬 Mening chatlarim"],
        ["📦 Katalog", "🏆 Konkurs"],
    ], resize_keyboard=True)

def admin_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["✍️ Murojaat yuborish"],
        ["📄 Vakansiyalar", "💬 Mening chatlarim"],
        ["📦 Katalog"],
        ["📢 Xabar yuborish"]  # Broadcast button for admins only
    ], resize_keyboard=True)

def contest_menu_keyboard():
    """Asosiy menyuni ko'rsatadi."""
    keyboard = [
        ["🏆 Liderlar", "📊 Mening natijalarim"],
        ["🔗 Mening linkim", "ℹ️ Konkurs haqida"],
        ["⬅️ Bosh menyuga qaytish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Vacancy conversation states
(GET_NAME, GET_PHONE, GET_REGION, GET_SKILLS, GET_INTERESTS, GET_POSITION,
GET_STATUS, GET_REASON) = range(8)

# Broadcast states
BROADCAST_MESSAGE = range(8, 9)

# Contest menu state
CONTEST_MENU = range(9, 10)

# Vacancy conversation functions
def vacancy_start(update: Update, context: CallbackContext):
    """Start the vacancy conversation"""
    context.user_data['vacancy_info'] = {}
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]
    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 1/8\n\n"
        "Iltimos, to'liq ism-sharifingizni yozing:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    return GET_NAME

def get_name(update: Update, context: CallbackContext):
    """Get user's full name"""
    context.user_data['vacancy_info']['name'] = update.message.text

    # Create keyboard with contact sharing option and back button
    keyboard = [
        [KeyboardButton("📞 Kontakt yuborish", request_contact=True)],
        [KeyboardButton("Bekor qilish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    # Add inline back button
    inline_keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]

    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 2/8\n\n"
        "Iltimos, telefon raqamingizni yozing yoki kontaktingizni yuboring:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )
    return GET_PHONE

def get_phone(update: Update, context: CallbackContext):
    """Get user's phone number"""
    if update.message.contact:
        context.user_data['vacancy_info']['phone'] = update.message.contact.phone_number
    elif update.message.text and update.message.text != "📞 Kontakt yuborish":
        context.user_data['vacancy_info']['phone'] = update.message.text
    else:
        # If user clicked the button but didn't share contact, ask again
        # Add inline back button
        inline_keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]
        update.message.reply_text(
            "📋 <b>Vakansiya arizasi</b>\n\n"
            "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
            "Hozirgi bosqich: 2/8\n\n"
            "Iltimos, kontaktingizni yuboring yoki telefon raqingizni kiriting:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard)
        )
        return GET_PHONE

    # Create region selection keyboard
    regions = ["Toshkent", "Samarqand", "Buxoro", "Xiva", "Farg'ona", "Andijon", "Namangan", "Qarshi", "Nukus", "Boshqa"]
    keyboard = []
    for region in regions:
        keyboard.append([KeyboardButton(region)])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    # Add inline back button
    inline_keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]

    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 3/8\n\n"
        "Iltimos, yashash joyingizni tanlang:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )
    return GET_REGION

def get_region(update: Update, context: CallbackContext):
    """Get user's region"""
    if update.callback_query:
        query = update.callback_query
        query.answer()
        region = query.data.split("_")[1]
        context.user_data['vacancy_info']['region'] = region
        # Add back button
        back_keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]
        query.edit_message_text(
            text=f"📋 <b>Vakansiya arizasi</b>\n\n"
                 f"Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
                 f"Hozirgi bosqich: 3/8\n\n"
                 f"Sizning hududingiz: {region}",
            parse_mode=ParseMode.HTML
        )
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
            reply_markup=InlineKeyboardMarkup(back_keyboard)
        )
    else:
        context.user_data['vacancy_info']['region'] = update.message.text

    # Create position selection keyboard
    positions = ["Sotuvchi", "Menejer", "Administrator", "Haydovchi", "Oshpaz", "Boshqa lavozim"]
    keyboard = []
    for i, pos in enumerate(positions):
        keyboard.append([InlineKeyboardButton(pos, callback_data=f"pos_{i}_{pos}")])

    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 4/8\n\n"
        "Qaysi lavozimda ishlamoqchisiz?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return GET_POSITION

def get_position(update: Update, context: CallbackContext):
    """Get user's desired position"""
    query = update.callback_query
    query.answer()
    _, _, position = query.data.split("_", 2)
    context.user_data['vacancy_info']['position'] = position

    # Create status selection keyboard
    statuses = ["Turmush qurgan", "Turmush qurmagan"]
    keyboard = []
    for i, status in enumerate(statuses):
        keyboard.append([InlineKeyboardButton(status, callback_data=f"status_{i}_{status}")])

    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 5/8\n\n"
        "Oilaviy holatingizni tanlang:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return GET_STATUS

def get_status(update: Update, context: CallbackContext):
    """Get user's family status"""
    query = update.callback_query
    query.answer()
    _, _, status = query.data.split("_", 2)
    context.user_data['vacancy_info']['status'] = status

    # Add back button
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]

    query.edit_message_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 6/8\n\n"
        "Qanday ko'nikmalarga ega ekanligingizni yozing:",
        parse_mode=ParseMode.HTML
    )
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_SKILLS

def get_skills(update: Update, context: CallbackContext):
    """Get user's skills"""
    context.user_data['vacancy_info']['skills'] = update.message.text

    # Add back button
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]

    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 7/8\n\n"
        "Qiziqishlaringiz va hobbiylaringizni yozing:",
        parse_mode=ParseMode.HTML
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_INTERESTS

def get_interests(update: Update, context: CallbackContext):
    """Get user's interests"""
    context.user_data['vacancy_info']['interests'] = update.message.text

    # Add back button
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]

    update.message.reply_text(
        "📋 <b>Vakansiya arizasi</b>\n\n"
        "Ariza to'ldirish jarayoni 8 bosqichdan iborat.\n"
        "Hozirgi bosqich: 8/8 (oxirgi bosqich)\n\n"
        "Nima uchun bizning kompaniyamizda ishlamoqchisiz?",
        parse_mode=ParseMode.HTML
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yoki quyidagi tugma orqali bosh menyuga qayting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_REASON

def get_reason(update: Update, context: CallbackContext):
    """Get user's reason for applying"""
    context.user_data['vacancy_info']['reason'] = update.message.text

    # Generate and send PDF
    generate_and_send_pdf(context, update.effective_user)

    update.message.reply_text(
        "🎉 <b>Arizangiz qabul qilindi!</b>\n\n"
        "✅ Barcha kerakli ma'lumotlar muvaffaqiyatli yuborildi.\n"
        "⏳ Tez orada HR menejerimiz siz bilan bog'lanadi.\n\n"
        "🏠 Bosh menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

def start_broadcast(update: Update, context: CallbackContext):
    """Start broadcast message creation for admins"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("Sizda bu funksiyadan foydalanish huquqi yo'q.")
        return ConversationHandler.END

    update.message.reply_text(
        "Iltimos, barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    return BROADCAST_MESSAGE

def send_broadcast(update: Update, context: CallbackContext):
    """Send broadcast message to all users"""
    if not db_connection:
        update.message.reply_text("❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.")
        return ConversationHandler.END

    broadcast_message = update.message.text
    admin_user = update.effective_user

    try:
        cursor = db_connection.cursor()
        # Get all users from the database
        cursor.execute("SELECT user_id FROM users WHERE status='active'")
        users = cursor.fetchall()

        success_count = 0
        fail_count = 0

        for (user_id,) in users:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>E'lon</b>\n\n{broadcast_message}",
                    parse_mode=ParseMode.HTML
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error sending broadcast to user {user_id}: {e}")
                fail_count += 1

        update.message.reply_text(
            f"✅ Xabar barcha foydalanuvchilarga yuborildi!\n\n"
            f"✅ Muvaffaqiyatli: {success_count}\n"
            f"❌ Muvaffaqiyatsiz: {fail_count}",
            reply_markup=admin_menu_keyboard() if is_admin(admin_user.id) else main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        update.message.reply_text(
            "❌ Kechirasiz, xabar yuborishda texnik xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            reply_markup=admin_menu_keyboard() if is_admin(admin_user.id) else main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    return ConversationHandler.END

def cancel_broadcast(update: Update, context: CallbackContext):
    """Cancel broadcast message creation"""
    user_id = update.effective_user.id
    update.message.reply_text(
        "✅ Xabar yuborish bekor qilindi.\n\n"
        "🏠 Bosh menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=admin_menu_keyboard() if is_admin(user_id) else main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

def send_broadcast_message(update: Update, context: CallbackContext):
    """Send broadcast message to all users from admin interface"""
    if not db_connection:
        update.message.reply_text("❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.")
        context.user_data.pop('awaiting_broadcast', None)
        return

    broadcast_message = update.message.text
    admin_user = update.effective_user

    try:
        cursor = db_connection.cursor()
        # Get all active users from the database
        cursor.execute("SELECT user_id FROM users WHERE status='active'")
        users = cursor.fetchall()

        success_count = 0
        fail_count = 0

        for (user_id,) in users:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>E'lon</b>\n\n{broadcast_message}",
                    parse_mode=ParseMode.HTML
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error sending broadcast to user {user_id}: {e}")
                fail_count += 1

        update.message.reply_text(
            f"✅ Xabar barcha foydalanuvchilarga yuborildi!\n\n"
            f"✅ Muvaffaqiyatli: {success_count}\n"
            f"❌ Muvaffaqiyatsiz: {fail_count}",
            reply_markup=admin_menu_keyboard() if is_admin(admin_user.id) else main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        update.message.reply_text(
            "❌ Kechirasiz, xabar yuborishda texnik xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            reply_markup=admin_menu_keyboard() if is_admin(admin_user.id) else main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    # Clean up the broadcast state
    context.user_data.pop('awaiting_broadcast', None)
    return ConversationHandler.END

def cancel_vacancy(update: Update, context: CallbackContext):
    """Cancel the vacancy conversation"""
    update.message.reply_text(
        "✅ Ariza bekor qilindi.\n\n"
        "🏠 Bosh menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

# Webhook Configuration
WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://sardor1ubaydiy.pythonanywhere.com/telegram-webhook')
WEBHOOK_PORT = int(os.environ.get('TELEGRAM_WEBHOOK_PORT', 443))

# Web application functions
def allowed_file(filename):
    # First check extension
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False

    # If filetype library is available, also check the actual file content
    if FILETYPE_AVAILABLE:
        # This would be used when we have the actual file content to check
        # For now, we'll just return True since we don't have the file content here
        pass

    # If imghdr is available, also check the actual file content
    if IMGHDR_AVAILABLE:
        # This would be used when we have the actual file content to check
        # For now, we'll just return True since we don't have the file content here
        pass

    return True

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

def save_products(products, context: CallbackContext = None):
    # Store the original length to detect new additions
    previous_length = len(load_products())
    current_length = len(products)

    # Apply default values and generate IDs
    for product in products:
        if 'price' not in product: product['price'] = 0
        if 'discount' not in product: product['discount'] = 0
        if 'is_active' not in product: product['is_active'] = True
        if 'id' not in product: product['id'] = str(uuid.uuid4())

    # Save updated products
    with open('data/products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # If a new product was added and we have context, broadcast it
    if context and current_length > previous_length:
        # Find the new product (the one not in previous list)
        previous_ids = {p['id'] for p in load_products()[:-1]}  # All but potentially the last
        for product in reversed(products):  # Check from most recent
            if product['id'] not in previous_ids:
                broadcast_new_product(product, context)
                break

def load_messages():
    try:
        with open('data/messages.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
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

def check_vacancy_trigger(user_id):
    """Checks if a vacancy was triggered for this user by the webhook."""
    try:
        note_file_path = os.path.join(os.path.dirname(__file__), 'vacancy_trigger.txt')
        if not os.path.exists(note_file_path):
            return False

        with open(note_file_path, 'r') as f:
            triggered_user_id = f.read().strip()

        # If the note is for this user, delete the note and return True
        if triggered_user_id == str(user_id):
            os.remove(note_file_path) # Consume the note
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking vacancy trigger: {e}")
        return False

def broadcast_new_product(new_product, context: CallbackContext):
    """Send a formatted advertisement message about a new product to all users."""
    if not db_connection:
        logger.error("Database connection not available for broadcasting")
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT user_id FROM users WHERE status='active'")
        users = cursor.fetchall()

        success_count = 0
        fail_count = 0

        # Format product details
        name = new_product.get('name', 'Noma\'lum mahsulot')
        description = new_product.get('description', '')
        price = new_product.get('price', 0)
        discount = new_product.get('discount', 0)
        image_url = new_product.get('image', '')

        # Calculate discounted price if applicable
        if discount > 0:
            discounted_price = int(price * (1 - discount / 100))
            price_text = f"{discounted_price:,} so'm 🎉 <i>({price:,} so'mdan {discount}% chegirma)</i>"
        else:
            price_text = f"{price:,} so'm"

        # Create product announcement message
        message_text = f"🚀 <b>Yangi Mahsulot!</b> 🚀\n\n"
        if image_url:
            message_text += f"<a href='{image_url}'>&#8205;</a>"  # Invisible link to force image preview
        message_text += f"<b>{name}</b>\n\n"
        if description:
            message_text += f"{description}\n\n"
        message_text += f"💰 <b>Narxi:</b> {price_text}\n\n"
        message_text += f"Tezroq bo'ling — cheklovlaringizni tekshiring!"

        # Create inline keyboard with view button
        keyboard = [[InlineKeyboardButton("↗️ Ko'rish", callback_data=f"prod_{new_product['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send to all users
        for (user_id,) in users:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    disable_web_page_preview=False
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error sending new product notification to user {user_id}: {e}")
                fail_count += 1

        logger.info(f"New product broadcast completed: {success_count} successful, {fail_count} failed")
    except Exception as e:
        logger.error(f"Error in broadcast_new_product: {e}")

# Web routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if user_manager:
            user = user_manager.get_user_by_username(username)
            if user and user.check_password(password):
                login_user(user)
                flash('Tizimga muvaffaqiyatli kirdingiz!', 'success')
                return redirect(url_for('collection'))
            else:
                flash('Noto\'g\'ri login yoki parol!', 'error')
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        telegram_username = request.form.get('telegram_username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        if user_manager:
            if user_manager.username_exists(username):
                flash('Bu foydalanuvchi nomi allaqachon mavjud!', 'error')
                return render_template('auth/signup.html')
            if user_manager.email_exists(email):
                flash('Bu email allaqachon ro\'yxatdan o\'tgan!', 'error')
                return render_template('auth/signup.html')
            if user_manager.telegram_exists(telegram_username):
                flash('Bu Telegram username allaqachon ro\'yxatdan o\'tgan!', 'error')
                return render_template('auth/signup.html')
            user = User(username, email, telegram_username, first_name, last_name, password)
            user.set_password(password)
            user_manager.add_user(user)
            flash('Hisobingiz muvaffaqiyatli yaratildi! Endi tizimga kiring.', 'success')
            return redirect(url_for('login'))
    return render_template('auth/signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Tizimdan muvaffaqiyatli chiqildi.', 'info')
    return redirect(url_for('index'))

@app.route('/collection')
def collection():
    return render_template('collection.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/product/<product_name>')
def product(product_name):
    return render_template('product.html')

@app.route('/rate-product/<product_id>/<rating>', methods=['POST'])
@login_required
def rate_product(product_id, rating):
    try:
        products = load_products()
        product = None
        for p in products:
            if p.get('id') == product_id:
                product = p
                break
        if not product:
            return jsonify({'success': False, 'error': 'Mahsulot topilmadi'}), 404
        if 'ratings' not in product:
            product['ratings'] = []
        user_id = current_user.get_id()
        already_rated = False
        for i, r in enumerate(product['ratings']):
            if r.get('user_id') == user_id:
                product['ratings'][i] = {'user_id': user_id, 'rating': int(rating), 'timestamp': datetime.now().isoformat()}
                already_rated = True
                break
        if not already_rated:
            product['ratings'].append({'user_id': user_id, 'rating': int(rating), 'timestamp': datetime.now().isoformat()})
        with open('data/products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        avg_rating = average_rating(product['ratings'])
        return jsonify({'success': True, 'average_rating': f"{avg_rating:.1f}", 'total_ratings': len(product['ratings']), 'new_rating': not already_rated})
    except Exception as e:
        print(f"Error rating product: {e}")
        return jsonify({'success': False, 'error': 'Baho qo\'shishda xatolik yuz berdi'}), 500

# Telegram webhook route
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    if not TELEGRAM_AVAILABLE:
        return "Telegram functionality not available", 500
    try:
        bot_token = CONFIG["BOT_TOKEN"]
        bot = telegram.Bot(token=bot_token)
        update = Update.de_json(request.get_json(force=True), bot)
        process_telegram_update(update, bot)
        return "OK", 200
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        import traceback
        traceback.print_exc()
        return "Error", 500

def get_bot_db_connection():
    try:
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'support_bot.db')
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return conn
    except Exception as e:
        logger.error(f"CRITICAL ERROR: Could not connect to bot database at {db_path}: {e}")
        return None

# Telegram bot handlers
def show_contest_menu_command(update: Update, context: CallbackContext):
    """Command handler to show contest menu"""
    # Check subscription to contest channels
    unsubscribed = check_contest_subscription(update.effective_user.id, context)

    if unsubscribed:
        ask_for_contest_subscription(update, context, unsubscribed)
    else:
        # Set contest menu flag
        context.user_data['in_contest_menu'] = True
        show_contest_menu(update, context)

# Webhook Configuration

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    # Check if this is a referral
    referrer_id = None
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])

    if db_connection:
        cursor = db_connection.cursor()
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
        existing_user = cursor.fetchone()

        if not existing_user:
            # Insert new user
            cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, referral_count, referrer_id, milestones_achieved) VALUES (?, ?, ?, ?, ?, ?)",
                           (user.id, user.first_name, user.username, 0, referrer_id, ""))
            db_connection.commit()

            # Award referral point to referrer if valid
            if referrer_id and referrer_id != user.id:
                cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
                db_connection.commit()

                # Get new referral count
                cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,))
                result = cursor.fetchone()
                if result:
                    new_score = result[0]
                    # Check and award milestones
                    check_and_award_milestones(referrer_id, new_score, context)

                    # Notify referrer
                    try:
                        context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Tabriklaymiz! Siz <b>{user.first_name}</b>ni taklif qildingiz va sizga 1 ball qo'shildi.",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.warning(f"Referrerga xabar yuborishda xato: {e}")
        else:
            # Update existing user info if needed
            cursor.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?",
                           (user.first_name, user.username, user.id))
            db_connection.commit()

    # Show admin menu for admin users, regular menu for others
    if is_admin(user.id):
        update.message.reply_text("Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:",
                                 reply_markup=admin_menu_keyboard())
    else:
        update.message.reply_text("Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:",
                                 reply_markup=main_menu_keyboard())
    logger.info(f"Bot started by user {user.id} ({user.first_name})")
    # End any active conversation
    return ConversationHandler.END

def open_support_menu(update: Update, context: CallbackContext):
    if not check_subscription(update, context):
        channels_text = "\n".join(CONFIG["CHANNELS"])
        keyboard = [[InlineKeyboardButton("✅ A'zo bo'ldim", callback_data="check_sub")]]
        update.message.reply_text(f"Murojaat yuborish uchun quyidagi kanallarga a'zo bo'ling:\n\n{channels_text}",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
        return
    show_topic_menu(update, context)

def check_sub_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    query.answer()
    if check_subscription(update, context):
        query.delete_message();
        show_topic_menu(update, context, query.message.chat_id)
    else:
        query.answer("Siz hali barcha kanallarga a'zo bo'lmadingiz.", show_alert=True)

def show_topic_menu(update: Update, context: CallbackContext, chat_id=None, is_edit=False):
    keyboard = []
    for key, value in CONFIG["TOPICS"].items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"topic_{key}")])
    keyboard.append([InlineKeyboardButton("💬 Mening chatlarim", callback_data="my_chats")])

    # Add admin-specific options
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("📢 Xabar yuborish", callback_data="broadcast_message")])

    text = "Murojaatingiz mavzusini tanlang yoki suhbatlar tarixini ko'ring:"
    effective_chat_id = chat_id or (update.effective_chat.id if update else None)
    if is_edit:
        try:
            update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            context.bot.send_message(effective_chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        try:
            update.message.delete()
        except:
            pass
        context.bot.send_message(effective_chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

def topic_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    topic = query.data.split("_")[1]
    context.user_data['selected_topic'] = topic;
    topic_text = CONFIG["TOPICS"].get(topic, "Umumiy");
    query.answer()
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]];
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Siz '{topic_text}' mavzusini tanladingiz. Endi murojaatingizni yozib yuboring.",
                           reply_markup=reply_markup)

def handle_user_message(update: Update, context: CallbackContext):
    user = update.effective_user

    # Check if we're waiting for a broadcast message from an admin
    if context.user_data.get('awaiting_broadcast') and is_admin(user.id):
        # Send broadcast message
        send_broadcast_message(update, context)
        return

    # Check if user is in contest menu mode
    if context.user_data.get('in_contest_menu'):
        # Handle contest menu options
        handle_contest_messages(update, context)
        return

    # Check if the webhook triggered a vacancy for this user
    if check_vacancy_trigger(user.id):
        # If so, start the vacancy conversation handler
        context.user_data['vacancy_info'] = {}
        update.message.reply_text("Iltimos, to'liq ism-sharifingizni yozing:",
                                reply_markup=ReplyKeyboardRemove())
        return GET_NAME

    # Original logic for support messages
    topic = context.user_data.get('selected_topic')
    if not topic:
        update.message.reply_text(
            "❌ Kechirasiz, mavzu tanlanmagan.\n\n"
            "🔄 Iltimos, avval '✍️ Murojaat yuborish' tugmasini bosib, mavzuni tanlang.",
            parse_mode=ParseMode.HTML
        )
        return

    if not db_connection:
        update.message.reply_text(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )
        return

    cursor = db_connection.cursor()
    cursor.execute("INSERT INTO tickets (user_id, topic) VALUES (?, ?)", (user.id, topic));
    ticket_id = cursor.lastrowid
    cursor.execute("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text) VALUES (?, ?, ?, ?)",
                   (ticket_id, user.id, "Siz", update.message.text))
    db_connection.commit();

    profile_text = get_user_profile_text(user.id)
    admin_message_text = f"🔹 <b>Yangi Murojaat!</b> #{ticket_id}\n<b>Mavzu:</b> {CONFIG['TOPICS'].get(topic, 'N/A')}\n\n{profile_text}\n---\n<b>Xabar:</b>\n\"{update.message.text}\""
    keyboard = [[InlineKeyboardButton("✅ Javob berishni boshlash", callback_data=f"claim_{ticket_id}")]]
    target_admins = CONFIG["TOPIC_ADMINS"].get(topic) or CONFIG["ADMIN_IDS"]

    success_count = 0
    for admin_id in target_admins:
        try:
            msg = context.bot.send_message(chat_id=admin_id, text=admin_message_text,
                                          parse_mode=ParseMode.HTML,
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            cursor.execute("INSERT INTO forwarded_messages (ticket_id, admin_id, message_id) VALUES (?, ?, ?)",
                          (ticket_id, admin_id, msg.message_id))
            db_connection.commit()
            success_count += 1
        except Exception as e:
            logger.error(f"{admin_id} ga xabar yuborishda xatolik: {e}")

    if success_count > 0:
        update.message.reply_text(
            f"✅ Murojaatingiz muvaffaqiyatli qabul qilindi!\n"
            f"⏳ Tez orada mutaxassisimiz javob beradi.\n\n"
            f"🆔 Murojaat raqamingiz: #{ticket_id}",
            parse_mode=ParseMode.HTML
        )
    else:
        update.message.reply_text(
            "❌ Kechirasiz, murojaatingizni yetkazishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )

    context.user_data.pop('selected_topic', None)

def admin_claim_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    admin_user = query.from_user;
    ticket_id = int(query.data.split("_")[1]);
    if not db_connection:
        return

    cursor = db_connection.cursor()
    cursor.execute("SELECT admin_id, message_id FROM forwarded_messages WHERE ticket_id=? AND admin_id!=?",
                   (ticket_id, admin_user.id));
    messages_to_delete = cursor.fetchall()
    for admin_id, message_id in messages_to_delete:
        try:
            context.bot.delete_message(chat_id=admin_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Eski xabarni o'chirishda xatolik: {e}")

    is_from_panel = query.message and query.message.text and "Admin Paneli" in query.message.text
    if is_from_panel:
        query.answer("Murojaat qabul qilindi!");
        admin_panel(update, context, is_edit=True, page=0)
    else:
        try:
            query.edit_message_text(f"✅ Murojaat #{ticket_id} siz tomondan qabul qilindi.\n\nIltimos, foydalanuvchi xabariga 'Reply' qiling va javobingizni yozing.")
        except Exception as e:
            logger.warning(f"Xabarni tahrirlashda xatolik: {e}")

    cursor.execute("UPDATE tickets SET assigned_admin_id=?, status='claimed' WHERE ticket_id=?",
                   (admin_user.id, ticket_id))
    cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,));
    user_id = cursor.fetchone()[0];
    db_connection.commit()
    context.bot.send_message(chat_id=user_id,
                           text=f"⏳ Sizning #{ticket_id}-raqamli murojaatingiz mutaxassis {admin_user.first_name} tomonidan ko'rib chiqilmoqda.")
    if not is_from_panel:
        query.answer("Murojaat qabul qilindi!")



    keyboard = [
        [InlineKeyboardButton("⭐⭐⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_5"),
             InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_4"),
             InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_3")],
            [InlineKeyboardButton("⭐⭐", callback_data=f"rate_{ticket_id}_2"),
             InlineKeyboardButton("⭐", callback_data=f"rate_{ticket_id}_1")]
    ]
    try:
        context.bot.send_message(chat_id=user_id,
                               text="Bizning yordamizdan qoniqdingizmi? Iltimos, xizmat sifatini baholang.",
                               reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        update.message.reply_text(f"❌ Xatolik: Foydalanuvchiga xabar yuborib bo'lmadi.\n\n{e}")

def rating_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    _, ticket_id, rating = query.data.split("_")[1]

def handle_admin_reply(update: Update, context: CallbackContext):
    """Handle replies from admins to user tickets"""
    if not db_connection:
        return

    # Get the original message that was replied to
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message

        # Extract ticket ID from the message text (assuming it contains #ticketid)
        message_text = original_message.text or ""
        import re
        ticket_match = re.search(r'#(\d+)', message_text)
        if ticket_match:
            ticket_id = int(ticket_match.group(1))
            cursor = db_connection.cursor()
            cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
            user_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text) VALUES (?, ?, ?, ?)",
                           (ticket_id, update.effective_user.id, update.effective_user.first_name, update.message.text))
            db_connection.commit()
            context.bot.send_message(chat_id=user_id, text=update.message.text)
            query = update.callback_query
            if query:
                query.answer("Javob yuborildi!")
            else:
                update.message.reply_text("Javob yuborildi!")

def check_contest_subscription_callback(update: Update, context: CallbackContext) -> None:
    """Callback to check if user has subscribed to required channels"""
    query = update.callback_query
    query.answer("A'zolik tekshirilmoqda...")
    user_id = query.from_user.id
    unsubscribed = check_contest_subscription(user_id, context)

    if unsubscribed:
        ask_for_contest_subscription(update, context, unsubscribed)
    else:
        query.message.delete()
        show_contest_menu(update, context)

def handle_contest_messages(update: Update, context: CallbackContext) -> None:
    """Handle contest menu messages"""
    text = update.message.text
    if text == "🔗 Mening linkim":
        get_my_link(update, context)
    elif text == "📊 Mening natijalarim":
        get_my_results(update, context)
    elif text == "🏆 Liderlar":
        show_leaderboard(update, context)
    elif text == "ℹ️ Konkurs haqida":
        show_contest_info(update, context)
    elif text == "⬅️ Bosh menyuga qaytish":
        # Clear contest menu flag and show main menu
        context.user_data.pop('in_contest_menu', None)
        user = update.effective_user
        if is_admin(user.id):
            update.message.reply_text("Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:",
                                     reply_markup=admin_menu_keyboard())
        else:
            update.message.reply_text("Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:",
                                     reply_markup=main_menu_keyboard())

def contest_menu_keyboard():
    """Asosiy menyuni ko'rsatadi."""
    keyboard = [
        ["🏆 Liderlar", "📊 Mening natijalarim"],
        ["🔗 Mening linkim", "ℹ️ Konkurs haqida"],
        ["⬅️ Bosh menyuga qaytish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def show_contest_menu(update: Update, context: CallbackContext):
    """Show the contest menu to the user with improved UX"""
    keyboard = contest_menu_keyboard()
    message_text = (
        "🎉 <b>Referal Konkursimizga Xush Kelibsiz!</b> 🎉\n\n"
        "Quyidagi menyulardan birini tanlang:\n\n"
        "🏆 <b>Liderlar</b> - Eng faol ishtirokchilarni ko'rish\n"
        "📊 <b>Mening natijalarim</b> - Sizning ballaringiz\n"
        "🔗 <b>Mening linkim</b> - Do'stlaringizga ulashish uchun shaxsiy havola\n"
        "ℹ️ <b>Konkurs haqida</b> - Batafsil ma'lumot\n\n"
        "✅ Har bir taklif uchun 1 ball, bonuslar esa maxsus bosqichlarda!"
    )
    if update.callback_query:
        context.bot.send_message(
            chat_id=update.effective_user.id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        update.message.reply_text(
            message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

def get_my_link(update: Update, context: CallbackContext) -> None:
    """Foydalanuvchining shaxsiy taklif havolasini yuboradi."""
    user_id = update.effective_user.id
    bot_info = context.bot.get_me()
    bot_username = bot_info.username
    link = f"https://t.me/{bot_username}?start={user_id}"

    share_text = (
        "🚀 Ajoyib konkursda qatnashing va sovrinlar yutib oling!\n\n"
        "Men Maryam Mebel botidan ajoyib chegirmalar va sovrinlar yutib oldim!\n"
        "Siz ham qo'shiling va ball to'plang:\n"
        f"{link}"
    )

    # Inline tugma yaratish
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("↗️ Do'stga ulashish", switch_inline_query=share_text)]
    ])

    update.message.reply_text(
        f"🎯 <b>Sizning shaxsiy taklif havolangiz:</b>\n\n"
        f"```{link}```\n\n"
        f"📎 <b>Qanday ishlatish:</b>\n"
        f"1. Havolani do'stlaringizga yuboring\n"
        f"2. Ular botga kirib konkursda qatnashadi\n"
        f"3. Har bir faol taklif uchun sizga 1 ball qo'shiladi\n\n"
        f"🎁 Bonus ballar maxsus bosqichlarda beriladi!",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

def show_contest_info(update: Update, context: CallbackContext) -> None:
    """Konkurs haqidagi ma'lumotni ko'rsatadi."""
    contest_info = (
        "🏆 <b>Konkursimiz Haqida Ma'lumot</b> 🏆\n\n"
        "<b>Konkursning maqsadi:</b>\n"
        "Eng ko'p do'stingizni botimizga taklif qilish!\n\n"
        "<b>Konkurs muddati:</b>\n"
        "31-Dekabr, 23:59 gacha\n\n"
        "<b>Sovrinlar:</b>\n"
        "🥇 1-o'rin: 1,000,000 so'm\n"
        "🥈 2-o'rin: 500,000 so'm\n"
        "🥉 3-o'rin: 250,000 so'm\n\n"
        "<b>Qoidalar:</b>\n"
        "1️⃣ Barcha shart bo'lgan kanallarga a'zo bo'ling.\n"
        "2️⃣ O'zingizning shaxsiy havolangiz orqali do'stlaringizni taklif qiling.\n"
        "3️⃣ Har bir faol taklif uchun sizga 1 ball beriladi.\n"
        "4️⃣ Qo'shimcha bonuslar uchun bosqichlarni bajaring!\n\n"
        "<b>Bonus bosqichlar:</b>\n"
        "5 taklif - 2 bonus ball\n"
        "10 taklif - 3 bonus ball\n"
        "25 taklif - 7 bonus ball\n"
        "50 taklif - 10 bonus ball\n"
        "100 taklif - 15 bonus ball\n"
        "200 taklif - 20 bonus ball\n\n"
        "Omad tilaymiz! ✨"
    )
    update.message.reply_text(
        contest_info,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

def get_my_results(update: Update, context: CallbackContext) -> None:
    """Show user's contest results"""
    user_id = update.effective_user.id
    if not db_connection:
        update.message.reply_text(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        count = result[0] if result else 0

        # Get user's position in leaderboard
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE referral_count > ?",
            (count,)
        )
        position = cursor.fetchone()[0] + 1 if cursor.fetchone() else 0

        # Get next milestone
        next_milestone = None
        for milestone in sorted(MILESTONES.keys()):
            if count < milestone:
                next_milestone = milestone
                break

        message_text = (
            f"📊 <b>Sizning umumiy balingiz: {count} ball</b>\n\n"
            f"🏅 <b>Joriy reytingdagi o'rningiz: {position}-o'rin</b>\n\n"
        )

        if next_milestone:
            needed = next_milestone - count
            message_text += (
                f"🔜 <b>Keyingi bonus bosqich:</b>\n"
                f"{next_milestone} ball (yana {needed} ball kerak)\n"
                f"Bonus: +{MILESTONES[next_milestone]} ball\n\n"
            )
        else:
            message_text += "🎉 <b>Tabriklaymiz! Siz maksimal bosqichdasiz!</b>\n\n"

        message_text += "🔗 Do'stlaringizni taklif qilib ballaringizni oshiring!"

        update.message.reply_text(
            message_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error getting user results: {e}")
        update.message.reply_text(
            "❌ Natijalarni olishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )

def show_leaderboard(update: Update, context: CallbackContext) -> None:
    """Show contest leaderboard"""
    if not db_connection:
        update.message.reply_text(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT first_name, referral_count FROM users ORDER BY referral_count DESC LIMIT 10")
        leaders = cursor.fetchall()

        if not leaders:
            update.message.reply_text("📭 Hozircha liderlar ro'yxati bo'sh.\n\nBirinchi bo'lib ball to'plang!")
            return

        text = "🏆 <b>Liderlar ro'yxati (Top 10)</b> 🏆\n\n"
        for i, leader in enumerate(leaders):
            name, count = leader
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}
            medal = medals.get(i, f"{i+1}.")
            text += f"{medal} {name} - {count} ball\n"

        # Add user's position
        user_id = update.effective_user.id
        cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
        user_result = cursor.fetchone()
        user_count = user_result[0] if user_result else 0

        cursor.execute("SELECT COUNT(*) FROM users WHERE referral_count > ?", (user_count,))
        user_position = cursor.fetchone()[0] + 1 if cursor.fetchone() else 0

        text += f"\n📍 <b>Sizning o'rningiz:</b> {user_position}-o'rin ({user_count} ball)"
        text += "\n\n🔗 Do'stlaringizni taklif qiling va reytingda yuqorilang!"

        update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        update.message.reply_text(
            "❌ Liderlar ro'yxatini olishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )

def admin_claim_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    admin_user = query.from_user;
    ticket_id = int(query.data.split("_")[1]);
    if not db_connection:
        query.answer(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.",
            show_alert=True
        )
        return

    cursor = db_connection.cursor()
    cursor.execute("SELECT admin_id, message_id FROM forwarded_messages WHERE ticket_id=? AND admin_id!=?",
                   (ticket_id, admin_user.id));
    messages_to_delete = cursor.fetchall()
    for admin_id, message_id in messages_to_delete:
        try:
            context.bot.delete_message(chat_id=admin_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Eski xabarni o'chirishda xatolik: {e}")

    is_from_panel = query.message and query.message.text and "Admin Paneli" in query.message.text
    if is_from_panel:
        query.answer("✅ Murojaat qabul qilindi!");
        admin_panel(update, context, is_edit=True, page=0)
    else:
        try:
            query.edit_message_text(
                f"✅ Murojaat #{ticket_id} siz tomondan qabul qilindi.\n\n"
                f"Iltimos, foydalanuvchi xabariga 'Reply' qiling va javobingizni yozing.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Xabarni tahrirlashda xatolik: {e}")

    cursor.execute("UPDATE tickets SET assigned_admin_id=?, status='claimed' WHERE ticket_id=?",
                   (admin_user.id, ticket_id))
    cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,));
    user_id = cursor.fetchone()[0];
    db_connection.commit()

    # Send notification to user that their ticket has been claimed
    try:
        context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Yangiliklar!</b>\n\n"
                 f"⏳ Sizning #{ticket_id}-raqamli murojaatingiz endi mutaxassis {admin_user.first_name} tomonidan ko'rib chiqilmoqda.\n\n"
                 f"🔄 Javob berilishini kuting.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending claim notification to user {user_id}: {e}")

    if not is_from_panel:
        query.answer("✅ Murojaat qabul qilindi!")

def handle_admin_reply(update: Update, context: CallbackContext):
    """Handle replies from admins to user tickets with improved UX"""
    if not db_connection:
        update.message.reply_text(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.\n\n"
            "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )
        return

    # Get the original message that was replied to
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message

        # Extract ticket ID from the message text (assuming it contains #ticketid)
        message_text = original_message.text or ""
        import re
        ticket_match = re.search(r'#(\d+)', message_text)
        if ticket_match:
            ticket_id = int(ticket_match.group(1))

            # Get the user ID associated with this ticket
            cursor = db_connection.cursor()
            cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
            result = cursor.fetchone()

            if result:
                user_id = result[0]

                # Save the admin's reply to the database
                cursor.execute(
                    "INSERT INTO messages (ticket_id, sender_id, sender_name, message_text) VALUES (?, ?, ?, ?)",
                    (ticket_id, update.effective_user.id, f"Admin ({update.effective_user.first_name})", update.message.text)
                )
                db_connection.commit()

                # Send the reply to the user with improved formatting
                try:
                    # Get admin info for personalized message
                    admin_name = update.effective_user.first_name

                    # Send formatted message to user with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

                    context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ <b>Sizning murojaatingizga javob:</b>\n\n"
                             f"{update.message.text}\n\n"
                             f"<i>👤 Administrator: {admin_name}</i>\n"
                             f"<i>⏰ Sana: {timestamp}</i>\n"
                             f"<i>🆔 Murojaat raqami: #{ticket_id}</i>",
                        parse_mode=ParseMode.HTML
                    )

                    # Update ticket status
                    cursor.execute("UPDATE tickets SET status='replied', assigned_admin_id=? WHERE ticket_id=?",
                                 (update.effective_user.id, ticket_id))
                    db_connection.commit()

                    # Send confirmation to admin with user info
                    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (user_id,))
                    user_result = cursor.fetchone()
                    user_name = user_result[0] if user_result else "Foydalanuvchi"

                    update.message.reply_text(
                        f"✅ Javobingiz <b>{user_name}</b>ga muvaffaqiyatli yuborildi.\n"
                        f"🆔 Murojaat raqami: #{ticket_id}\n"
                        f"⏰ Yuborilgan vaqt: {timestamp}",
                        parse_mode=ParseMode.HTML
                    )

                    # Send rating request after reply with improved UX
                    keyboard = [
                        [InlineKeyboardButton("⭐⭐⭐⭐⭐ (5)", callback_data=f"rate_{ticket_id}_5")],
                        [InlineKeyboardButton("⭐⭐⭐⭐ (4)", callback_data=f"rate_{ticket_id}_4")],
                        [InlineKeyboardButton("⭐⭐⭐ (3)", callback_data=f"rate_{ticket_id}_3")],
                        [InlineKeyboardButton("⭐⭐ (2)", callback_data=f"rate_{ticket_id}_2")],
                        [InlineKeyboardButton("⭐ (1)", callback_data=f"rate_{ticket_id}_1")]
                    ]
                    try:
                        context.bot.send_message(
                            chat_id=user_id,
                            text="📋 <b>Xizmat sifatini baholash</b>\n\n"
                                 "Bizning yordamizdan qoniqdingizmi?\n"
                                 "Iltimos, xizmat sifatini baholang:",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"Error sending rating request to user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error sending admin reply to user {user_id}: {e}")
                    update.message.reply_text(
                        "❌ Xatolik: Foydalanuvchiga javob yuborishda texnik xatolik yuz berdi.\n"
                        "🔄 Iltimos, bir ozdan keyin qayta urinib ko'ring yoki murojaatingizni boshqacha tarzda yuboring.",
                        parse_mode=ParseMode.HTML
                    )
            else:
                update.message.reply_text(
                    "❌ Xatolik: Ko'rsatilgan murojaat ma'lumotlar bazasida topilmadi.\n"
                    "🔄 Iltimos, murojaatni qaytadan tanlang va javob yozing.",
                    parse_mode=ParseMode.HTML
                )
        else:
            update.message.reply_text(
                "❌ Xatolik: Xabardan murojaat raqamini aniqlab bo'lmadi.\n"
                "🔄 Iltimos, foydalanuvchi xabarini 'Reply' tugmasi orqali oching va javobingizni yozing.",
                parse_mode=ParseMode.HTML
            )
    else:
        update.message.reply_text(
            "❌ Xatolik: Siz xabarni 'Reply' tugmasi orqali ochmagansiz.\n"
            "🔄 To'g'ri tarzda:\n"
            "1. Foydalanuvchi xabarini tanlang\n"
            "2. 'Reply' tugmasini bosing\n"
            "3. Javobingizni yozing",
            parse_mode=ParseMode.HTML
        )

def rating_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    _, ticket_id, rating = query.data.split("_")
    if not db_connection:
        query.answer(
            "❌ Ma'lumotlar bazasiga ulanishda xatolik yuz berdi.",
            show_alert=True
        )
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("UPDATE tickets SET rating=?, status='closed' WHERE ticket_id=?", (int(rating), int(ticket_id)))
        db_connection.commit()

        # Thank user and provide follow-up options
        rating_stars = "⭐" * int(rating)
        response_text = (
            f"✅ <b>Rahmat! Siz xizmatimizni {rating_stars} ga baholadingiz.</b>\n\n"
            f"💬 Fikr-mulohazalaringiz biz uchun muhim!\n"
            f"🔄 Agar yana savollaringiz bo'lsa, yangi murojaat yuborishingiz mumkin.\n\n"
            f"🏠 Bosh menyuga qaytish uchun quyidagi tugmani bosing:"
        )

        # Add back to menu button
        keyboard = [[InlineKeyboardButton("🏠 Bosh menyuga qaytish", callback_data="back_to_menu")]]

        query.answer("✅ Bahoyingiz uchun rahmat!")
        query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

        # Send a follow-up message with additional options
        user_id = query.from_user.id
        follow_up_text = (
            "🔧 <b>Qo'shimcha yordam kerakmi?</b>\n\n"
            "Agar savolingizga to'liq javob olmagan bo'lsangiz, "
            "yoki boshqa savollar tug'ilgan bo'lsa, yangi murojaat yuboring.\n\n"
            "🤝 Biz sizga yordam berishdan mamnunmiz!"
        )

        context.bot.send_message(
            chat_id=user_id,
            text=follow_up_text,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error processing rating for ticket {ticket_id}: {e}")
        query.answer(
            "❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            show_alert=True
        )

def admin_panel(update: Update, context: CallbackContext, is_edit: bool = False, page: int = 0):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("Sizda bu buyruq uchun ruxsat yo'q.")
        return

    if not db_connection:
        return

    cursor = db_connection.cursor();
    offset = page * PANEL_PAGE_SIZE
    cursor.execute("SELECT ticket_id, topic, created_at, user_id FROM tickets WHERE status='open' OR status='claimed' ORDER BY created_at ASC LIMIT ? OFFSET ?", (PANEL_PAGE_SIZE, offset))
    open_tickets = cursor.fetchall();
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='open' OR status='claimed'");
    total_open_tickets = cursor.fetchone()[0]

    panel_text = f"📊 <b>Admin Paneli</b>\nJavob kutayotgan murojaatlar: {total_open_tickets}\n\n";
    keyboard = []

    if not open_tickets:
        panel_text += "Hozirda javob kutayotgan murojaatlar mavjud emas."
    else:
        for ticket_id, topic, created_at, user_id in open_tickets:
            # Get user name for display
            cursor.execute("SELECT first_name, username FROM users WHERE user_id=?", (user_id,))
            user_data = cursor.fetchone()
            user_name = user_data[0] if user_data and user_data[0] else (user_data[1] if user_data else "Noma'lum")
            topic_text = CONFIG['TOPICS'].get(topic, 'Noma\'lim').split()[1];
            button_text = f"#{ticket_id} - {user_name} - {topic_text} ({created_at.split()[0]})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"panel_view_{ticket_id}_{page}")])

    # Add broadcast button
    keyboard.append([InlineKeyboardButton("📢 Xabar yuborish", callback_data="broadcast_message")])

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"panel_page_{page-1}"))
    if total_open_tickets > (page + 1) * PANEL_PAGE_SIZE:
        pagination_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"panel_page_{page+1}"))
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if is_edit:
        try:
            update.callback_query.edit_message_text(panel_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Panelni tahrirlashda xatolik: {e}")
    else:
        update.message.reply_text(panel_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def panel_page_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    page = int(query.data.split("_")[2])
    query.answer();
    admin_panel(update, context, is_edit=True, page=page)

def broadcast_callback(update: Update, context: CallbackContext):
    """Handle broadcast button click in admin panel"""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        query.answer("Sizda bu funksiyadan foydalanish huquqi yo'q.", show_alert=True)
        return

    query.answer()
    query.edit_message_text(
        "Iltimos, barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni kiriting:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Bekor qilish", callback_data="cancel_broadcast")]])
    )
    context.user_data['awaiting_broadcast'] = True

def panel_view_ticket_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    _, _, ticket_id, page = query.data.split("_")[2];
    ticket_id = int(ticket_id);
    page = int(page);
    if not db_connection:
        return
    cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, topic FROM tickets WHERE ticket_id=?", (ticket_id,));
    ticket_data = cursor.fetchone()
    if not ticket_data:
        query.answer("Bu murojaat topilmadi.", show_alert=True);
        return

    user_id, topic = ticket_data[0];
    cursor.execute("SELECT message_text FROM messages WHERE ticket_id=? ORDER BY sent_at ASC LIMIT 1", (ticket_id,))
    first_message = cursor.fetchone()[0]
    profile_text = get_user_profile_text(user_id)
    view_text = f"🔹 <b>Murojaat #{ticket_id}</b>\n<b>Mavzu:</b> {CONFIG['TOPICS'].get(topic, 'Noma\'lim').split()[1]}\n\n{profile_text}\n---\n<b>Xabar:</b>\n\"{first_message}"
    keyboard = [
        [InlineKeyboardButton("✅ Javob berishni boshlash", callback_data=f"claim_{ticket_id}")],
        [InlineKeyboardButton("⬅️ Panelga qaytish", callback_data=f"panel_page_{page}")]
    ]
    query.answer();
    query.edit_message_text(view_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def my_chats_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    user_id = query.from_user.id if query else update.effective_user.id
    if not db_connection:
        return
    cursor = db_connection.cursor()
    cursor.execute("SELECT ticket_id, topic, status FROM tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
    tickets = cursor.fetchall()
    if not tickets:
        if query:
            query.answer("Sizda hali murojaatlar mavjud emas.", show_alert=True)
        else:
            update.message.reply_text("Sizda hali murojaatlar mavjud emas.")
        return

    keyboard = []
    for ticket_id, topic, status in tickets:
        status_icon = "✅" if status == "closed" else "⏳"
        topic_text = CONFIG['TOPICS'].get(topic, 'Noma\'lim mavzu').replace("📦 ", "").replace("⚙�️ ", "").replace("💬� ", "").replace("🤝 ", "").replace("💡� ", "").replace("💡� ", "")
        button_text = f"#{ticket_id} - {topic_text} {status_icon}";
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_ticket_{ticket_id}")])

    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])
    if query:
        query.answer();
        query.edit_message_text("Murojaatlaringiz tarixi:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text("Murojaatlaringiz tarixi:", reply_markup=InlineKeyboardMarkup(keyboard))

def view_ticket_callback(update: Update, context: CallbackContext):
    query = update.callback_query;
    ticket_id = int(query.data.split("_")[2])
    if not db_connection:
        return
    cursor = db_connection.cursor()
    cursor.execute("SELECT sender_name, message_text FROM messages WHERE ticket_id=? ORDER BY sent_at ASC", (ticket_id,));
    messages = cursor.fetchall()
    conversation_text = f"<b>Suhbat tarixi: Murojaat #{ticket_id}</b>\n\n"
    for sender, text in messages:
        conversation_text += f"<b>{sender}:</b>\n{text}\n\n"
    keyboard = [[InlineKeyboardButton("⬅️ Ro'yxatga qaytish", callback_data="my_chats")]];
    query.answer()
    query.edit_message_text(conversation_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def back_to_menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("🏠 Bosh menyuga qaytilyapti...")

    # Clear all conversation data
    context.user_data.clear()

    # Show main menu with confirmation message
    user = update.effective_user
    if is_admin(user.id):
        query.edit_message_text(
            "✅ Muvaffaqiyatli bosh menyuga qaytdingiz!\n\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=admin_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        query.edit_message_text(
            "✅ Muvaffaqiyatli bosh menyuga qaytdingiz!\n\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

    # End conversation
    return ConversationHandler.END

def cancel_broadcast_callback(update: Update, context: CallbackContext):
    """Handle cancel broadcast button click"""
    query = update.callback_query
    user_id = query.from_user.id

    query.answer()
    query.edit_message_text(
        "Xabar yuborish bekor qilindi.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]])
    )
    context.user_data.pop('awaiting_broadcast', None)

def category_callback(update: Update, context: CallbackContext):
    """Handle category selection and show products in that category"""
    query = update.callback_query
    query.answer()

    # Extract category from callback data
    category = query.data.split("_", 1)[1]  # Remove "cat_" prefix

    # Get products from web application
    products = get_products_from_web()

    # Filter products by category
    category_products = [p for p in products if p.get('category') == category]

    if not category_products:
        query.edit_message_text("Ushbu kategoriyada hozirda mahsulotlar mavjud emas.")
        return

    # Create keyboard with products
    keyboard = []
    for product in category_products:
        product_name = product.get('name', 'Noma\'lum mahsulot')
        product_id = product.get('id', '')
        keyboard.append([InlineKeyboardButton(product_name, callback_data=f"prod_{product_id}")])

    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"{category} kategoriyasidagi mahsulotlar:", reply_markup=reply_markup)

def product_callback(update: Update, context: CallbackContext):
    """Handle product selection and show product details"""
    query = update.callback_query
    query.answer()

    # Extract product ID from callback data
    product_id = query.data.split("_", 1)[1]  # Remove "prod_" prefix

    # Get products from web application
    products = get_products_from_web()

    # Find the selected product
    selected_product = None
    for product in products:
        if product.get('id') == product_id:
            selected_product = product
            break

    if not selected_product:
        query.edit_message_text("Mahsulot topilmadi.")
        return

    # Format product details
    name = selected_product.get('name', 'Noma\'lum')
    description = selected_product.get('description', 'Tavsif mavjud emas')
    price = selected_product.get('price', 0)
    discount = selected_product.get('discount', 0)

    # Calculate discounted price if applicable
    if discount > 0:
        discounted_price = price * (1 - discount / 100)
        price_text = f"{discounted_price:,.0f} so'm\n<i>({price:,.0f} so'mdan {discount}% chegirma)</i>"
    else:
        price_text = f"{price:,.0f} so'm"

    # Create product details message
    message_text = f"<b>{name}</b>\n\n"
    message_text += f"{description}\n\n"
    message_text += f"<b>Narxi:</b> {price_text}"

    # Create keyboard with options
    keyboard = [
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")],
        [InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def show_catalog(update: Update, context: CallbackContext):
    """Show catalog menu with categories and breadcrumbs"""
    # Get products from web application
    products = get_products_from_web()

    # Get unique categories
    categories = get_unique_categories(products)

    if not categories:
        update.message.reply_text(
            "📭 Hozirda katalog bo'sh.\n\n"
            "🔄 Iltimos, keyinroq qaytib ko'ring.",
            parse_mode=ParseMode.HTML
        )
        return

    # Create keyboard with categories
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])

    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "📂 <b>Mahsulotlar katalogi</b>\n\n"
        "Quyidagi kategoriyalardan birini tanlang:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def category_callback(update: Update, context: CallbackContext):
    """Handle category selection and show products in that category with breadcrumbs"""
    query = update.callback_query
    query.answer()

    # Extract category from callback data
    category = query.data.split("_", 1)[1]  # Remove "cat_" prefix

    # Get products from web application
    products = get_products_from_web()

    # Filter products by category
    category_products = [p for p in products if p.get('category') == category]

    if not category_products:
        query.edit_message_text(
            f"📂 {category} kategoriyasi\n\n"
            "📭 Ushbu kategoriyada hozirda mahsulotlar mavjud emas.\n\n"
            "↩️ Orqaga qaytish uchun quyidagi tugmalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Katalogga qaytish", callback_data="catalog_menu")],
                [InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return

    # Create keyboard with products
    keyboard = []
    for product in category_products:
        product_name = product.get('name', 'Noma\'lum mahsulot')
        product_id = product.get('id', '')
        keyboard.append([InlineKeyboardButton(product_name, callback_data=f"prod_{product_id}")])

    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")])
    keyboard.append([InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"📂 {category} kategoriyasi\n\n"
        f"Quyidagi {len(category_products)} ta mahsulotdan birini tanlang:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def product_callback(update: Update, context: CallbackContext):
    """Handle product selection and show product details with breadcrumbs"""
    query = update.callback_query
    query.answer()

    # Extract product ID from callback data
    product_id = query.data.split("_", 1)[1]  # Remove "prod_" prefix

    # Get products from web application
    products = get_products_from_web()

    # Find the selected product
    selected_product = None
    for product in products:
        if product.get('id') == product_id:
            selected_product = product
            break

    if not selected_product:
        query.edit_message_text(
            "❌ Mahsulot topilmadi.\n\n"
            "🔄 Iltimos, qaytadan urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Katalogga qaytish", callback_data="catalog_menu")],
                [InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return

    # Format product details
    name = selected_product.get('name', 'Noma\'lum')
    description = selected_product.get('description', 'Tavsif mavjud emas')
    price = selected_product.get('price', 0)
    discount = selected_product.get('discount', 0)
    category = selected_product.get('category', 'Noma\'lum kategoriya')

    # Calculate discounted price if applicable
    if discount > 0:
        discounted_price = price * (1 - discount / 100)
        price_text = f"{discounted_price:,.0f} so'm\n<i>({price:,.0f} so'mdan {discount}% chegirma)</i>"
    else:
        price_text = f"{price:,.0f} so'm"

    # Create product details message
    message_text = (
        f"📂 {category} > <b>{name}</b>\n\n"
        f"{description}\n\n"
        f"<b>Narxi:</b> {price_text}"
    )

    # Create keyboard with options
    keyboard = [
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"cat_{category}")],
        [InlineKeyboardButton("📂 Katalogga qaytish", callback_data="catalog_menu")],
        [InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def back_to_catalog(update: Update, context: CallbackContext):
    """Go back to catalog menu"""
    show_catalog(update, context)

def show_catalog_menu(update: Update, context: CallbackContext):
    """Show catalog menu with categories"""
    show_catalog(update, context)

def show_contest_menu_command(update: Update, context: CallbackContext):
    """Command handler to show contest menu"""
    # Check subscription to contest channels
    from threading import Thread

    def check_and_show():
        # This is a simplified approach - in a real implementation you'd need to properly handle async operations
        update.message.reply_text("Konkurs menyusi ochilmoqda...", reply_markup=contest_menu_keyboard())

        Thread(target=check_and_show).start()

        # Webhook Configuration

        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])

        keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Quyidagi kategoriyalardan birini tanlang:", reply_markup=reply_markup)

    # Remove the duplicate function definitions and WEBHOOK_URL declarations
    # The following lines were duplicates and have been removed:
    # 1. Duplicate get_region function
    # 2. Duplicate WEBHOOK_URL declaration
    # 3. Duplicate vacancy conversation states declaration

    update.message.reply_text("Quyidagi kategoriyalardan birini tanlang:", reply_markup=reply_markup)

    # Vacancy conversation states
    (GET_NAME, GET_PHONE, GET_REGION, GET_SKILLS, GET_INTERESTS, GET_POSITION,
    GET_STATUS, GET_REASON) = range(8)

    # Vacancy conversation functions
    def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        update.message.reply_text(
            "Siz rostdan ham ish joyi qo'shmoqchimisiz? Ha yoki Yo'q tugmasini bosing."
        )
        return GET_NAME

    def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Name of %s: %s", user.first_name, update.message.text)
        context.user_data['name'] = update.message.text
        update.message.reply_text("Telefon raqamingizni kiriting:")
        return GET_PHONE

    def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Phone number of %s: %s", user.first_name, update.message.text)
        context.user_data['phone'] = update.message.text
        update.message.reply_text("Viloyatingizni tanlang:", reply_markup=region_keyboard)
        return GET_REGION

    def get_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Region of %s: %s", user.first_name, update.message.text)
        context.user_data['region'] = update.message.text
        update.message.reply_text("Ko'nikmalaringizni kiriting:")
        return GET_SKILLS

    def get_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Skills of %s: %s", user.first_name, update.message.text)
        context.user_data['skills'] = update.message.text
        update.message.reply_text("Qiziqishlaringizni kiriting:")
        return GET_INTERESTS

    def get_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Interests of %s: %s", user.first_name, update.message.text)
        context.user_data['interests'] = update.message.text
        update.message.reply_text("Lavozimingizni kiriting:")
        return GET_POSITION

    def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Position of %s: %s", user.first_name, update.message.text)
        context.user_data['position'] = update.message.text
        update.message.reply_text("Holatni tanlang:", reply_markup=status_keyboard)
        return GET_STATUS

    def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Status of %s: %s", user.first_name, update.message.text)
        context.user_data['status'] = update.message.text
        update.message.reply_text("Sababni kiriting:")
        return GET_REASON

    def get_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("Reason of %s: %s", user.first_name, update.message.text)
        context.user_data['reason'] = update.message.text
        update.message.reply_text("Ma'lumotlar qabul qilindi. Raxmat!")
        return ConversationHandler.END

    def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)
        update.message.reply_text(
            "Siz rostdan ham ish joyi qo'shmoqchimisiz? Ha yoki Yo'q tugmasini bosing."
        )
        return GET_NAME

    # Broadcast functions
    def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        update.message.reply_text("Xabar yuborish uchun matn kiriting:")
        return BROADCAST_MESSAGE

    def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message.text
        for chat_id in chat_ids:
            context.bot.send_message(chat_id=chat_id, text=message)
        update.message.reply_text("Xabar yuborildi!")
        return ConversationHandler.END

    # Contest menu functions
    def contest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        update.message.reply_text("Konkurs haqida ma'lumot olish uchun quyidagi tugmani bosing:", reply_markup=contest_keyboard)
        return CONTEST_MENU

    def contest_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        update.message.reply_text(CONTEST_INFO_TEXT)
        return ConversationHandler.END

    # --- Konkurs Ma'lumotlari (Oson o'zgartirish uchun) ---
CONTEST_INFO_TEXT = """
🏆 <b>Konkursimiz Haqida Ma'lumot</b> 🏆

<b>Konkursning maqsadi:</b>
Eng ko'p do'stingizni botimizga taklif qilish!

<b>Konkurs muddati:</b>
31-Dekabr, 23:59 gacha

<b>Sovrinlar:</b>
🥇 1-o'rin: 1,000,000 so'm
🥈 2-o'rin: 500,000 so'm
🥉 3-o'rin: 250,000 so'm

<b>Qoidalar:</b>
1. Barcha shart bo'lgan kanallarga a'zo bo'ling.
2. O'zingizning shaxsiy havolangiz orqali do'stlaringizni taklif qiling.
3. Har bir faol taklif uchun sizga 1 ball beriladi.
4. Qo'shimcha bonuslar uchun bosqichlarni bajaring!

Omad tilaymiz! ✨
"""

# --- Bosqichlar va Bonuslar ---
# Format: {takliflar_soni: bonus_ballari}
MILESTONES = {
    5: 2,
    10: 3,
    25: 7,
    50: 10,
    100: 15,
    200: 20,
}

async def check_and_award_milestones(referrer_id: int, new_score: int, context: CallbackContext):
    """Foydalanuvchining bosqichlardan o'tganligini tekshiradi va bonus beradi."""
    if not db_connection:
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT milestones_achieved FROM users WHERE user_id = ?", (referrer_id,))
        result = cursor.fetchone()
        if not result:
            return

        achieved_str = result[0]
        achieved_list = achieved_str.split(',') if achieved_str else []

        total_bonus_awarded = 0
        newly_achieved = []

        for milestone, bonus in sorted(MILESTONES.items()):
            if new_score >= milestone and str(milestone) not in achieved_list:
                total_bonus_awarded += bonus
                newly_achieved.append(str(milestone))
                try:
                    context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 <b>Ajoyib! Siz {milestone} ta do'stingizni taklif qildingiz!</b>\n\n"
                             f"🎁 Sizga mukofot sifatida <b>+{bonus} bonus ball</b> taqdim etildi!",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.warning(f"Mukofot xabarini yuborishda xato: {e}")

        if total_bonus_awarded > 0:
            cursor.execute("UPDATE users SET referral_count = referral_count + ? WHERE user_id = ?", (total_bonus_awarded, referrer_id))

            updated_achieved_str = ",".join(achieved_list + newly_achieved)
            cursor.execute("UPDATE users SET milestones_achieved = ? WHERE user_id = ?", (updated_achieved_str, referrer_id))

            db_connection.commit()

    except Exception as e:
        logger.error(f"Error in check_and_award_milestones: {e}")

# The async functions above are duplicates and have been removed
# The correct implementations are already present in the codebase

async def show_leaderboard(update: Update, context: CallbackContext) -> None:
    if not db_connection:
        await update.message.reply_text("Bot hozirda ishlamayapti. Iltimos, keyinroq qaytadan urinib ko'ring.")
        return

    cursor = db_connection.cursor()
    cursor.execute("SELECT first_name, referral_count FROM users ORDER BY referral_count DESC LIMIT 10")
    leaders = cursor.fetchall()
    if not leaders:
        await update.message.reply_text("Hozircha liderlar ro'yxati bo'sh.")
        return
    text = "🏆 <b>Liderlar ro'yxati (Top 10)</b> 🏆\n\n"
    for i, leader in enumerate(leaders):
        name, count = leader
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        medal = medals.get(i, f"<b>{i+1}.</b>")
        text += f"{medal} {name} - {count} ball\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# Add these functions to the existing ones
# They will be connected in the ConversationHandler

def setup_telegram_webhook(bot_token, webhook_url=None):
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram functionality not available.")
        return False
    try:
        bot = Bot(token=bot_token)
        if webhook_url:
            bot.set_webhook(url=webhook_url)
            logger.info(f"Telegram webhook set to: {webhook_url}")
            return True
        else:
            # Use the global WEBHOOK_URL if not provided
            webhook_url = WEBHOOK_URL
            if webhook_url:
                bot.set_webhook(url=webhook_url)
                logger.info(f"Telegram webhook set to: {webhook_url}")
                return True
            else:
                logger.warning("No webhook URL provided, bot will use polling mode")
                return False
    except Exception as e:
        logger.error(f"Error setting up Telegram webhook: {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_telegram_webhook(bot_token):
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram functionality not available.")
        return False
    try:
        bot = telegram.Bot(token=bot_token)
        bot.delete_webhook()
        logger.info("Telegram webhook removed")
        return True
    except Exception as e:
        logger.error(f"Error removing Telegram webhook: {e}")
        return False

def start_bot():
    """Start the Telegram bot with proper error handling"""
    if not TELEGRAM_AVAILABLE:
        logger.warning("Telegram libraries not available. Bot functionality disabled.")
        return None

    try:
        # Remove any existing webhook to prevent conflicts
        try:
            bot = telegram.Bot(token=CONFIG["BOT_TOKEN"])
            bot.delete_webhook(drop_pending_updates=True)
            logger.info("Removed existing webhook to prevent conflicts")
        except Exception as e:
            logger.warning(f"Could not remove existing webhook: {e}")

        # Create the Application instance
        application = Updater(token=CONFIG["BOT_TOKEN"])

        # Add error handler to prevent continuous error logging
        def error_handler(update, context):
            logger.error(f"Exception while handling an update: {context.error}")

        # Check if the application object has the add_error_handler method
        if hasattr(application, 'add_error_handler'):
            application.add_error_handler(error_handler)
        elif hasattr(application, 'dispatcher') and hasattr(application.dispatcher, 'add_error_handler'):
            application.dispatcher.add_error_handler(error_handler)

        # Add handlers
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                CommandHandler('vacancy', vacancy_start),
                MessageHandler(Filters.regex('^(✍️ Murojaat yuborish)$'), open_support_menu),
                MessageHandler(Filters.regex('^(📄 Vakansiyalar)$'), vacancy_start),
                MessageHandler(Filters.regex('^(📦 Katalog)$'), show_catalog),
                MessageHandler(Filters.regex('^(🏆 Konkurs)$'), show_contest_menu_command),
                MessageHandler(Filters.regex('^(📢 Xabar yuborish)$'), start_broadcast),  # Broadcast entry point
                CallbackQueryHandler(check_sub_callback, pattern='^check_sub$'),
                CallbackQueryHandler(topic_callback, pattern='^topic_'),
                CallbackQueryHandler(category_callback, pattern='^cat_'),
                CallbackQueryHandler(product_callback, pattern='^prod_'),
                CallbackQueryHandler(back_to_catalog, pattern='^back_to_catalog$'),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$'),
                CallbackQueryHandler(my_chats_callback, pattern='^my_chats$'),
                CallbackQueryHandler(category_callback, pattern='^chat_'),
                CallbackQueryHandler(panel_page_callback, pattern='^panel_page_'),
                CallbackQueryHandler(panel_view_ticket_callback, pattern='^panel_view_'),
                CallbackQueryHandler(view_ticket_callback, pattern='^view_ticket_'),
                CallbackQueryHandler(admin_claim_callback, pattern='^claim_'),
                CallbackQueryHandler(rating_callback, pattern='^rate_'),
                CallbackQueryHandler(broadcast_callback, pattern='^broadcast_message$'),
                CallbackQueryHandler(cancel_broadcast_callback, pattern='^cancel_broadcast$'),
                CallbackQueryHandler(check_contest_subscription_callback, pattern='^check_contest_subscription$'),
            ],
            states={
                GET_NAME: [MessageHandler(Filters.text & ~Filters.command, get_name),
                         CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_PHONE: [MessageHandler((Filters.text | Filters.contact) & ~Filters.command, get_phone),
                          CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_REGION: [MessageHandler(Filters.text & ~Filters.command, get_region),
                           CallbackQueryHandler(get_region, pattern='^region_'),
                           CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_POSITION: [CallbackQueryHandler(get_position, pattern='^pos_'),
                             CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_STATUS: [CallbackQueryHandler(get_status, pattern='^status_'),
                           CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_SKILLS: [MessageHandler(Filters.text & ~Filters.command, get_skills),
                           CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, get_interests),
                              CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                GET_REASON: [MessageHandler(Filters.text & ~Filters.command, get_reason),
                           CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                BROADCAST_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, send_broadcast),
                                  CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
                CONTEST_MENU: [MessageHandler(Filters.text & ~Filters.command, handle_contest_messages)],
                # Add other states as needed
            },
            fallbacks=[CommandHandler('start', start), # Global escape command
                       CommandHandler('cancel', cancel_vacancy),
                       MessageHandler(Filters.regex('^⬅️ Bosh menyuga qaytish$'), cancel_vacancy),
                       MessageHandler(Filters.regex('^Bekor qilish$'), cancel_broadcast)]
        )

        # Add handlers - compatible with both old and new versions of python-telegram-bot
        if hasattr(application, 'add_handler'):
            application.add_handler(conv_handler)
            # Remove the generic message handler that was catching all messages
            # application.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_message))
            application.add_handler(MessageHandler(Filters.reply, handle_admin_reply))
            # Add command handler for broadcast
            application.add_handler(CommandHandler('broadcast', start_broadcast))
        elif hasattr(application, 'dispatcher') and hasattr(application.dispatcher, 'add_handler'):
            application.dispatcher.add_handler(conv_handler)
            # Remove the generic message handler that was catching all messages
            # application.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_message))
            application.dispatcher.add_handler(MessageHandler(Filters.reply, handle_admin_reply))

        # Start the bot
        logger.info("Starting Telegram bot...")

        # Check if we're using the newer Application API or older Updater API
        if hasattr(application, 'run_polling'):
            # Newer python-telegram-bot v20+
            application.run_polling(drop_pending_updates=True)
        else:
            # Older versions
            application.start_polling(drop_pending_updates=True)
            application.idle()

        return application

    except telegram.error.Conflict as e:
        logger.error(f"Conflict error: {e}")
        logger.error("This usually means another instance of the bot is already running.")
        logger.error("Please stop the existing bot instance before starting a new one.")
        return None
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        import traceback
        traceback.print_exc()
        return None

FOOTER_HTML = """
<footer class="main-footer" style="padding: 50px 0; background-color: #000; border-top: 1px solid #222; text-align: center; position: relative;">
    <div class="container">
        <a href="/" class="logo" style="justify-content: center; margin-bottom: 30px; display: inline-flex; align-items: center; text-decoration: none;">
            <img src="/static/logo.png" alt="Maryam Logo" style="width: 45px; height: auto; margin-right: 15px;">
            <span class="logo-text" style="color: white; font-family: 'Montserrat', sans-serif; font-weight: 700; font-size: 2rem; background: #cc0000; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Maryam</span>
        </a>
        <p style="color: #888; font-size: 0.9rem;">&copy; 2025 Maryam Furniture Factory. Barcha huquqlar himoyalangan.</p>
        <div style="margin-top: 20px; display: flex; justify-content: center; gap: 30px;">
            <a href="https://t.me/maryam_furniture" target="_blank" style="color: #888; text-decoration: none; transition: color 0.3s ease;" onmouseover="this.style.color='#cc0000'" onmouseout="this.style.color='#888'">
                <i class="fab fa-telegram-plane" style="font-size: 1.5rem;"></i>
            </a>
            <a href="https://instagram.com/maryam_furniture" target="_blank" style="color: #888; text-decoration: none; transition: color 0.3s ease;" onmouseover="this.style.color='#cc0000'" onmouseout="this.style.color='#888'">
                <i class="fab fa-instagram" style="font-size: 1.5rem;"></i>
            </a>
        </div>
    </div>
</footer>
"""

@app.after_request
def after_request(response):
    # Only modify HTML responses
    if response.content_type and 'text/html' in response.content_type:
        # Get the response data
        try:
            content = response.get_data(as_text=True)
            # Check if this is a full HTML document and doesn't already have the Maryam Furniture footer
            if '<!DOCTYPE html>' in content and '</body>' in content and 'Maryam Furniture Factory' not in content:
                # Inject the footer before the closing body tag
                modified_content = content.replace('</body>', FOOTER_HTML + '\n</body>')
                response.set_data(modified_content)
        except Exception as e:
            # If there's any error, just return the original response
            pass
    return response

if __name__ == '__main__':
    # Initialize database
    db_connection = setup_database()

    # Start bot in a separate thread
    bot_thread = None
    if TELEGRAM_AVAILABLE:
        logger.info("Telegram libraries available, starting bot...")
        try:
            # Try to start the bot
            bot_app = start_bot()
            if bot_app:
                logger.info("Telegram bot started successfully")
            else:
                logger.warning("Telegram bot failed to start")
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
    else:
        logger.warning("Telegram libraries not available, running web server only")

    # Run Flask app
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
