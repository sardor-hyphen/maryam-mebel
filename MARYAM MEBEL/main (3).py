from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.product import ProductManager
from models.message import MessageManager, Message
from config.config import Config
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from telegram_bot import send_order_notification_to_telegram

main_bp = Blueprint('main', __name__)

# Initialize managers
product_manager = ProductManager(Config.PRODUCTS_JSON)
message_manager = MessageManager(Config.MESSAGES_JSON)

@main_bp.route('/')
def index():
    """Homepage with featured products"""
    products = product_manager.load_products()[:2]  # Get first 2 products
    return render_template('index.html', products=products)

@main_bp.route('/collection')
def collection():
    """Product collection page"""
    category = request.args.get('category', 'all')
    products = product_manager.get_products_by_category(category)
    return render_template('collection.html', products=products)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page with form handling"""
    product_name = request.args.get('product')
    product = None
    product_slug = None
    
    # If product name is provided, get product details
    if product_name:
        product = product_manager.get_product_by_slug(product_name)
        if product:
            product_slug = product.slug
    
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
            product = product_manager.get_product_by_slug(product_slug)
            if product:
                message_text = f"[MAHSULOT BUYURTMASI: {product.name}]\n{message_text}"
        
        # Create message object
        message = Message(
            name=name,
            phone=phone,
            email=email,
            message_text=message_text
        )
        
        # Save message
        message_manager.add_message(message)
        
        # Send notification to Telegram bot
        order_data = {
            'name': name,
            'phone': phone,
            'email': email,
            'message': message_text,
            'product_name': product_name,
            'product_slug': product_slug
        }
        send_order_notification_to_telegram(order_data)
        
        flash('Xabaringiz muvaffaqiyatli yuborildi! Tez orada siz bilan bog\'lanamiz.', 'success')
        return render_template('contact.html', message_sent=True, product_name=product_name, product_slug=product_slug)
    
    return render_template('contact.html', product_name=product_name, product_slug=product_slug)

@main_bp.route('/product/<product_name>')
def product(product_name):
    """Individual product page"""
    product = product_manager.get_product_by_slug(product_name)
    
    if not product:
        flash('Mahsulot topilmadi.', 'error')
        return redirect(url_for('main.collection'))
    
    return render_template('product.html', product=product)

@main_bp.route('/admin-access')
def admin_access():
    """Quick admin access route"""
    return redirect(url_for('admin.login'))