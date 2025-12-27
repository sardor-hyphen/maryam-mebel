from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_session import Session
import os
import json
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3  # Added for Telegram bot integration
import uuid

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import Telegram libraries for webhook functionality
try:
    import telegram
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
    TELEGRAM_AVAILABLE = True
    print("Telegram libraries loaded successfully")
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    print(f"Telegram libraries not available: {e}")
    print("Webhook functionality will be disabled.")

# Import user models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
from user import UserManager, User

# Import admin blueprint
sys.path.append(os.path.join(os.path.dirname(__file__), 'routes'))
from admin import admin_bp
from main import main_bp

# Initialize user manager
user_manager = UserManager('data/users.json')

# Import Telegram service
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from telegram_service import init_telegram_service, get_telegram_service
from utils import average_rating  # Import the average_rating function

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'maryam_furniture_secret_key_2025')
app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'filesystem')
Session(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sahifaga kirish uchun tizimga kirishingiz kerak.'
login_manager.login_message_category = 'info'

# Register utility functions with Jinja2 templates
from utils import init_app as init_utils
init_utils(app)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return user_manager.get_user_by_id(user_id)

# Make current_user available in templates
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
PRODUCTS_FOLDER = 'templates/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max file size

# Register admin blueprint
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCTS_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Initialize Telegram service
bot_db_path = os.path.join(os.path.dirname(__file__), '..', 'maryam bot', 'support_bot.db')
telegram_service = init_telegram_service(bot_db_path)

# For direct Telegram bot API usage, use the bot token
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')  # From bot.py

# Telegram Webhook Configuration
# For PythonAnywhere deployment, you'll need to set these environment variables
TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://your-pythonanywhere-username.pythonanywhere.com/telegram-webhook')
TELEGRAM_WEBHOOK_PORT = int(os.environ.get('TELEGRAM_WEBHOOK_PORT', 443))
TELEGRAM_WEBHOOK_CERT_FILE = os.environ.get('TELEGRAM_WEBHOOK_CERT_FILE', None)  # Path to certificate file if needed

telegram_service = init_telegram_service(BOT_TOKEN)

# Admin credentials (in production, use a proper database)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'maryam2025'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_products():
    """Load products from JSON file"""
    try:
        with open('data/products.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # If file is empty
                return []
            products = json.loads(content)
            # Add missing fields to existing products
            for product in products:
                if 'price' not in product:
                    product['price'] = 0
                if 'discount' not in product:
                    product['discount'] = 0
                if 'is_active' not in product:
                    product['is_active'] = True
                if 'id' not in product:
                    product['id'] = str(uuid.uuid4())
            return products
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        # If JSON is invalid, return empty list
        print("Warning: products.json contains invalid JSON. Returning empty product list.")
        return []

def save_products(products):
    """Save products to JSON file"""
    # Ensure all products have required fields
    for product in products:
        if 'price' not in product:
            product['price'] = 0
        if 'discount' not in product:
            product['discount'] = 0
        if 'is_active' not in product:
            product['is_active'] = True
        if 'id' not in product:
            product['id'] = str(uuid.uuid4())
    
    with open('data/products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_messages():
    """Load contact messages from JSON file"""
    try:
        with open('data/messages.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # If file is empty
                return []
            return json.loads(content)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        # If JSON is invalid, return empty list
        print("Warning: messages.json contains invalid JSON. Returning empty message list.")
        return []

def save_message(message_data):
    """Save a new contact message"""
    messages = load_messages()
    message_data['id'] = len(messages) + 1
    message_data['timestamp'] = datetime.now().isoformat()
    message_data['read'] = False
    messages.append(message_data)
    
    with open('data/messages.json', 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# Routes
# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = user_manager.get_user_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            flash('Tizimga muvaffaqiyatli kirdingiz!', 'success')
            # Redirect to collection page after login
            return redirect(url_for('main.collection'))
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
        
        # Check if user already exists
        if user_manager.username_exists(username):
            flash('Bu foydalanuvchi nomi allaqachon mavjud!', 'error')
            return render_template('auth/signup.html')
        
        if user_manager.email_exists(email):
            flash('Bu email allaqachon ro\'yxatdan o\'tgan!', 'error')
            return render_template('auth/signup.html')
        
        if user_manager.telegram_exists(telegram_username):
            flash('Bu Telegram username allaqachon ro\'yxatdan o\'tgan!', 'error')
            return render_template('auth/signup.html')
        
        # Create new user
        user = User(username, email, telegram_username, first_name, last_name)
        user.set_password(password)
        user_manager.add_user(user)
        
        flash('Hisobingiz muvaffaqiyatli yaratildi! Endi tizimga kiring.', 'success')
        # Redirect to login page after successful signup
        return redirect(url_for('login'))
    
    return render_template('auth/signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Tizimdan muvaffaqiyatli chiqildi.', 'info')
    return redirect(url_for('main.index'))

# Route to handle product ratings
@app.route('/rate-product/<product_id>/<rating>', methods=['POST'])
@login_required
def rate_product(product_id, rating):
    try:
        # Load all products
        products = load_products()
        
        # Find the product
        product = None
        for p in products:
            if p.get('id') == product_id:
                product = p
                break
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Mahsulot topilmadi'
            }), 404
        
        # Initialize ratings array if it doesn't exist
        if 'ratings' not in product:
            product['ratings'] = []
        
        # Check if user already rated this product
        user_id = current_user.get_id()
        already_rated = False
        
        for i, r in enumerate(product['ratings']):
            if r.get('user_id') == user_id:
                # Update existing rating
                product['ratings'][i] = {
                    'user_id': user_id,
                    'rating': int(rating),
                    'timestamp': datetime.now().isoformat()
                }
                already_rated = True
                break
        
        if not already_rated:
            # Add new rating
            product['ratings'].append({
                'user_id': user_id,
                'rating': int(rating),
                'timestamp': datetime.now().isoformat()
            })
        
        # Save updated products
        with open('data/products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        # Calculate new average rating
        average_rating = sum(r['rating'] for r in product['ratings']) / len(product['ratings'])
        
        return jsonify({
            'success': True,
            'average_rating': f"{average_rating:.1f}",
            'total_ratings': len(product['ratings']),
            'new_rating': not already_rated
        })
    
    except Exception as e:
        print(f"Error rating product: {e}")
        return jsonify({
            'success': False,
            'error': 'Baho qo\'shishda xatolik yuz berdi'
        }), 500

def create_product_page(product_data):
    """Create a new product page HTML file"""
    # For now, we'll just use the template system
    # In a production environment, you might want to generate static files
    pass

# Telegram Bot Webhook Route
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram webhook requests"""
    if not TELEGRAM_AVAILABLE:
        return "Telegram functionality not available", 500
    
    try:
        # Get the bot token from config
        bot_token = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')  # From .env or default
        
        # Create a bot instance
        bot = telegram.Bot(token=bot_token)
        
        # Create an update object from the request data
        update = Update.de_json(request.get_json(force=True), bot)
        
        # Process the update with the existing bot logic
        process_telegram_update(update, bot)
        
        return "OK", 200
    except Exception as e:
        print(f"Error processing Telegram webhook: {e}")
        import traceback
        traceback.print_exc()
        return "Error", 500

def process_telegram_update(update, bot):
    """Process Telegram update using the existing bot logic"""
    # Import functions from bot.py to handle the full functionality
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'maryam bot'))
    
    try:
        from bot import (
            show_direct_order_menu, 
            handle_user_message,
            open_support_menu,
            my_chats_callback,
            vacancy_start,
            show_topic_menu,
            back_to_menu_callback,
            category_callback,
            product_callback,
            show_catalog_menu,
            topic_callback
        )
        
        # Also import necessary constants and variables
        from bot import CONFIG, db_connection
        
        # Handle different types of updates
        if update.message:
            user = update.message.from_user
            text = update.message.text
            
            # Save user to database if not exists
            cursor = db_connection.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)",
                (user.id, user.first_name, user.username)
            )
            db_connection.commit()
            
            # Handle specific commands and buttons
            if text == "/start":
                # Send main menu
                from telegram import ReplyKeyboardMarkup
                keyboard = ReplyKeyboardMarkup([
                    ["✍️ Murojaat yuborish"], 
                    ["📄 Vakansiyalar", "💬 Mening chatlarim"],
                    ["📦 Buyurtma berish"]
                ], resize_keyboard=True)
                
                bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:",
                    reply_markup=keyboard
                )
            elif text == "📦 Buyurtma berish":
                # Handle the direct order button
                # Create a mock update and context for the function
                class MockContext:
                    def __init__(self):
                        self.user_data = {}
                
                mock_context = MockContext()
                show_direct_order_menu(update, mock_context)
            elif text == "✍️ Murojaat yuborish":
                # Handle support menu button
                class MockContext:
                    def __init__(self):
                        self.user_data = {}
                
                mock_context = MockContext()
                open_support_menu(update, mock_context)
            elif text == "💬 Mening chatlarim":
                # Handle my chats button
                my_chats_callback(update, None)
            elif text == "📄 Vakansiyalar":
                # Handle vacancy button
                class MockContext:
                    def __init__(self):
                        self.user_data = {}
                
                mock_context = MockContext()
                vacancy_start(update, mock_context)
            else:
                # Handle regular messages
                class MockContext:
                    def __init__(self):
                        self.user_data = {}
                        self.bot = bot
                
                mock_context = MockContext()
                mock_context.user_data['selected_topic'] = 'taklif'  # Default topic
                handle_user_message(update, mock_context)
                
        elif update.callback_query:
            # Handle callback queries
            query = update.callback_query
            data = query.data
            
            # Answer the callback query to prevent loading indicator
            bot.answer_callback_query(callback_query_id=query.id)
            
            # Create a mock context
            class MockContext:
                def __init__(self, bot_instance):
                    self.bot = bot_instance
                    self.user_data = {}
            
            mock_context = MockContext(bot)
            
            # Handle different callback patterns
            if data.startswith("topic_"):
                # Handle topic selection
                from bot import topic_callback
                topic_callback(update, mock_context)
            elif data == "back_to_menu":
                # Handle back to menu
                back_to_menu_callback(update, mock_context)
            elif data == "my_chats":
                # Handle my chats
                my_chats_callback(update, mock_context)
            elif data.startswith("cat_"):
                # Handle category selection
                category_callback(update, mock_context)
            elif data.startswith("prod_"):
                # Handle product selection
                product_callback(update, mock_context)
            elif data == "catalog_menu":
                # Handle catalog menu
                show_catalog_menu(update, mock_context)
            # Add more callback handlers as needed
            
    except Exception as e:
        print(f"Error processing update: {e}")
        import traceback
        traceback.print_exc()
        # Try to send error message to user if possible
        try:
            if update and update.message:
                bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Kechirasiz, xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
                )
        except:
            pass

def setup_telegram_webhook(bot_token, webhook_url):
    """Set up Telegram bot webhook"""
    if not TELEGRAM_AVAILABLE:
        print("Telegram functionality not available.")
        return False
    
    try:
        bot = Bot(token=bot_token)
        # Set the webhook
        if TELEGRAM_WEBHOOK_CERT_FILE and os.path.exists(TELEGRAM_WEBHOOK_CERT_FILE):
            # If certificate file is provided and exists, use it
            bot.set_webhook(url=webhook_url, certificate=open(TELEGRAM_WEBHOOK_CERT_FILE, 'rb'))
        else:
            # Set webhook without certificate (for services like PythonAnywhere that handle SSL)
            bot.set_webhook(url=webhook_url)
        print(f"Telegram webhook set to: {webhook_url}")
        return True
    except Exception as e:
        print(f"Error setting up Telegram webhook: {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_telegram_webhook(bot_token):
    """Remove Telegram bot webhook"""
    if not TELEGRAM_AVAILABLE:
        print("Telegram functionality not available.")
        return False
    
    try:
        bot = telegram.Bot(token=bot_token)
        # Remove the webhook
        bot.delete_webhook()
        print("Telegram webhook removed")
        return True
    except Exception as e:
        print(f"Error removing Telegram webhook: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    # Check if we should set up webhook mode
    if len(sys.argv) > 1 and sys.argv[1] == 'webhook':
        # Webhook mode for PythonAnywhere
        bot_token = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')
        
        # Get the webhook URL from environment variable or use default
        webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://your-pythonanywhere-username.pythonanywhere.com/telegram-webhook')
        
        print("Setting up Telegram webhook...")
        if setup_telegram_webhook(bot_token, webhook_url):
            print("Telegram webhook setup successful")
        else:
            print("Failed to set up Telegram webhook")
    elif len(sys.argv) > 1 and sys.argv[1] == 'remove-webhook':
        # Remove webhook mode
        bot_token = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')
        
        print("Removing Telegram webhook...")
        if remove_telegram_webhook(bot_token):
            print("Telegram webhook removed successfully")
        else:
            print("Failed to remove Telegram webhook")
    else:
        # Default mode - run the Flask app
        app.run(debug=True, host='0.0.0.0', port=5000)