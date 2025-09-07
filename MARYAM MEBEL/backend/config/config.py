import os
from werkzeug.security import generate_password_hash

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'maryam_furniture_secret_key_2025'
    UPLOAD_FOLDER = 'static/uploads'
    PRODUCTS_FOLDER = 'templates/products'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Admin credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD_HASH = generate_password_hash('maryam2025')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Database paths
    PRODUCTS_JSON = 'data/products.json'
    MESSAGES_JSON = 'data/messages.json'
    USERS_JSON = 'data/users.json'
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or 'YOUR_BOT_TOKEN_HERE'
    TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL') or 'https://your-domain.com/webhook'
    
    # Flask-Login settings
    LOGIN_DISABLED = False