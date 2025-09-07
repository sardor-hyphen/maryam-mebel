from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
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

# Import user models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
from user import UserManager, User

# Import admin blueprint
sys.path.append(os.path.join(os.path.dirname(__file__), 'routes'))
from admin import admin_bp

# Initialize user manager
user_manager = UserManager('data/users.json')

# Import Telegram service
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from telegram_service import init_telegram_service, get_telegram_service
from utils import average_rating  # Import the average_rating function

app = Flask(__name__)
app.secret_key = 'maryam_furniture_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'
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
UPLOAD_FOLDER = 'static/uploads'
PRODUCTS_FOLDER = 'templates/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Register admin blueprint
app.register_blueprint(admin_bp)

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCTS_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Initialize Telegram service
bot_db_path = os.path.join(os.path.dirname(__file__), '..', 'maryam bot', 'support_bot.db')
telegram_service = init_telegram_service(bot_db_path)

# For direct Telegram bot API usage, use the bot token
BOT_TOKEN = "8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc"  # From bot.py
telegram_service = init_telegram_service(BOT_TOKEN)

# Admin credentials (in production, use a proper database)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('maryam2025')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_products():
    """Load products from JSON file"""
    try:
        with open('data/products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
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
            return json.load(f)
    except FileNotFoundError:
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
@app.route('/')
def index():
    # Check if user is logged in
    if current_user.is_authenticated:
        # If logged in, redirect to shop (collection) page
        return redirect(url_for('collection'))
    else:
        # If not logged in, show landing page with featured products
        products = load_products()
        # Sort products by creation date (newest first) and get the first 2
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        featured_products = products[:2]  # Get first 2 products for homepage
        return render_template('index.html', products=featured_products)

@app.route('/collection')
def collection():
    # Load products for display
    products = load_products()
    
    # Check if user is logged in
    if not current_user.is_authenticated:
        # If not logged in, we'll still render the page but with auth requirement
        # The frontend will handle showing the auth modal
        pass
    
    return render_template('collection.html', products=products)



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    product_name = request.args.get('product')
    product = None
    product_slug = None
    
    # If product name is provided, get product details
    if product_name:
        products = load_products()
        for p in products:
            if p.get('slug') == product_name:
                product = p
                product_slug = p.get('slug')
                break
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email', '')
        message_text = request.form.get('message')
        product_slug = request.form.get('product_slug', '')
        product_name = request.form.get('product_name', '')
        
        # If product is specified, prepend product info to message
        if product_slug:
            products = load_products()
            for p in products:
                if p.get('slug') == product_slug:
                    product = p
                    message_text = f"[MAHSULOT BUYURTMASI: {p.get('name', 'Noma\'lum')}]\n{message_text}"
                    break
        
        # Save message
        message_data = {
            'name': name,
            'phone': phone,
            'email': email,
            'message': message_text
        }
        
        save_message(message_data)
        
        # Send notification to Telegram bot
        try:
            # Path to the Telegram bot database
            bot_db_path = os.path.join(os.path.dirname(__file__), '..', 'maryam bot', 'support_bot.db')
            
            # Connect to the Telegram bot database
            conn = sqlite3.connect(bot_db_path)
            cursor = conn.cursor()
            
            # Create a new ticket for the order
            # Using 'buyurtma' as the topic since that's what the bot uses for orders
            cursor.execute(
                "INSERT INTO tickets (user_id, topic, status, created_at) VALUES (?, ?, ?, ?)",
                (0, 'buyurtma', 'open', datetime.now().isoformat())
            )
            
            # Get the ticket ID of the newly created ticket
            ticket_id = cursor.lastrowid
            
            # Create a message for the ticket
            full_message_text = f"📦 YANGI BUYURTMA\n\n"
            full_message_text += f"Ism: {name}\n"
            full_message_text += f"Telefon: {phone}\n"
            
            if email:
                full_message_text += f"Email: {email}\n"
            
            if product_name:
                full_message_text += f"Mahsulot: {product_name}\n"
            
            full_message_text += f"\nXabar: {message_text}"
            
            # Insert the message
            cursor.execute(
                "INSERT INTO messages (ticket_id, sender_id, sender_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)",
                (ticket_id, 0, "Mijoz", full_message_text, datetime.now().isoformat())
            )
            
            # Commit changes
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error sending order notification to Telegram bot: {e}")
        
        flash('Xabaringiz muvaffaqiyatli yuborildi! Tez orada siz bilan bog\'lanamiz.', 'success')
        return render_template('contact_success.html')
    
    return render_template('contact.html', product_name=product_name, product_slug=product_slug)

@app.route('/product/<product_name>')
def product(product_name):
    products = load_products()
    product = None
    
    for p in products:
        if p.get('slug') == product_name:
            product = p
            break
    
    if not product:
        flash('Mahsulot topilmadi.', 'error')
        return redirect(url_for('collection'))
    
    return render_template('product.html', product=product)

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
    return redirect(url_for('index'))

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)