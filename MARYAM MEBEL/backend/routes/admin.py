from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from models.product import ProductManager, Product
from models.message import MessageManager
from utils.helpers import save_uploaded_file, create_slug
from config.config import Config
import os
import sys
import sqlite3

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize managers
product_manager = ProductManager(Config.PRODUCTS_JSON)
message_manager = MessageManager(Config.MESSAGES_JSON)

def login_required(f):
    """Decorator to require admin login"""
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == Config.ADMIN_USERNAME and check_password_hash(Config.ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Muvaffaqiyatli kirildi!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Noto\'g\'ri login yoki parol!', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Tizimdan chiqildi.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/')
@login_required
def dashboard():
    """Admin dashboard"""
    products = product_manager.load_products()
    messages = message_manager.load_messages()
    # Convert Message objects to dictionaries for JSON serialization
    messages_dict = [message.to_dict() for message in messages]
    unread_count = message_manager.get_unread_count()
    
    return render_template('admin/dashboard.html', 
                         products=products, 
                         messages=messages_dict,
                         unread_count=unread_count)

@admin_bp.route('/orders')
@login_required
def orders():
    """View orders from Telegram bot"""
    try:
        # Path to the Telegram bot database
        bot_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'maryam bot', 'support_bot.db')
        
        # Connect to the Telegram bot database
        conn = sqlite3.connect(bot_db_path)
        cursor = conn.cursor()
        
        # Get all tickets with topic 'buyurtma' (orders)
        cursor.execute("""
            SELECT t.ticket_id, t.created_at, t.status, m.message_text
            FROM tickets t
            JOIN messages m ON t.ticket_id = m.ticket_id
            WHERE t.topic = 'buyurtma'
            ORDER BY t.created_at DESC
        """)
        
        orders = cursor.fetchall()
        conn.close()
        
        # Parse order information from messages
        parsed_orders = []
        for order in orders:
            ticket_id, created_at, status, message_text = order
            
            # Extract order details from message text
            order_details = {
                'ticket_id': ticket_id,
                'created_at': created_at,
                'status': status,
                'customer_name': 'Noma\'lum',
                'phone': 'Noma\'lum',
                'email': '',
                'product': '',
                'message': message_text
            }
            
            # Parse the message text to extract details
            lines = message_text.split('\n')
            for line in lines:
                if line.startswith('Ism:'):
                    order_details['customer_name'] = line.replace('Ism:', '').strip()
                elif line.startswith('Telefon:'):
                    order_details['phone'] = line.replace('Telefon:', '').strip()
                elif line.startswith('Email:'):
                    order_details['email'] = line.replace('Email:', '').strip()
                elif line.startswith('Mahsulot:'):
                    order_details['product'] = line.replace('Mahsulot:', '').strip()
            
            parsed_orders.append(order_details)
        
        return render_template('admin/orders.html', orders=parsed_orders)
    except Exception as e:
        flash(f'Buyurtmalarni yuklashda xatolik yuz berdi: {str(e)}', 'error')
        return render_template('admin/orders.html', orders=[])

@admin_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Create new product"""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        slug = request.form.get('slug') or create_slug(name)
        description = request.form.get('description')
        category = request.form.get('category')
        material = request.form.get('material')
        year = request.form.get('year')
        warranty = request.form.get('warranty')
        includes = request.form.get('includes')
        price = request.form.get('price', type=int) or 0
        discount = request.form.get('discount', type=int) or 0
        is_active = request.form.get('is_active') == 'True'
        
        # Handle main image upload
        main_image = ''
        if 'main_image' in request.files:
            main_image = save_uploaded_file(
                request.files['main_image'], 
                Config.UPLOAD_FOLDER, 
                Config.ALLOWED_EXTENSIONS
            ) or ''
        
        # Handle gallery images
        gallery_images = []
        for i in range(1, 5):  # Support up to 4 gallery images
            file_key = f'gallery_image_{i}'
            if file_key in request.files:
                image_path = save_uploaded_file(
                    request.files[file_key],
                    Config.UPLOAD_FOLDER,
                    Config.ALLOWED_EXTENSIONS
                )
                if image_path:
                    gallery_images.append(image_path)
        
        # Create product
        product = Product(
            name=name,
            slug=slug,
            description=description,
            category=category,
            material=material,
            year=year,
            warranty=warranty,
            includes=includes,
            price=price,
            discount=discount,
            is_active=is_active,
            main_image=main_image,
            gallery_images=gallery_images
        )
        
        # Save product
        product_manager.add_product(product)
        
        # Create product page
        create_product_page(product)
        
        flash('Mahsulot muvaffaqiyatli qo\'shildi!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/new_product.html')

@admin_bp.route('/products/<string:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit existing product"""
    # Find the product to edit
    product = product_manager.get_product_by_id(product_id)
    
    if not product:
        flash('Mahsulot topilmadi.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        slug = request.form.get('slug') or create_slug(name)
        description = request.form.get('description')
        category = request.form.get('category')
        material = request.form.get('material')
        year = request.form.get('year')
        warranty = request.form.get('warranty')
        includes = request.form.get('includes')
        price = request.form.get('price', type=int) or 0
        discount = request.form.get('discount', type=int) or 0
        is_active = request.form.get('is_active') == 'True'
        
        # Handle main image upload
        main_image = product.main_image  # Keep existing image if not updated
        if 'main_image' in request.files and request.files['main_image'].filename != '':
            main_image = save_uploaded_file(
                request.files['main_image'], 
                Config.UPLOAD_FOLDER, 
                Config.ALLOWED_EXTENSIONS
            ) or product.main_image
        
        # Handle gallery images
        gallery_images = product.gallery_images[:]  # Keep existing images
        for i in range(1, 5):  # Support up to 4 gallery images
            file_key = f'gallery_image_{i}'
            if file_key in request.files and request.files[file_key].filename != '':
                image_path = save_uploaded_file(
                    request.files[file_key],
                    Config.UPLOAD_FOLDER,
                    Config.ALLOWED_EXTENSIONS
                )
                if image_path:
                    # Replace the image at this index or append if it doesn't exist
                    if i <= len(gallery_images):
                        gallery_images[i-1] = image_path
                    else:
                        gallery_images.append(image_path)
        
        # Update product
        product.name = name
        product.slug = slug
        product.description = description
        product.category = category
        product.material = material
        product.year = year
        product.warranty = warranty
        product.includes = includes
        product.price = price
        product.discount = discount
        product.is_active = is_active
        product.main_image = main_image
        product.gallery_images = gallery_images
        
        # Save updated product
        if product_manager.update_product(product_id, product):
            flash('Mahsulot muvaffaqiyatli yangilandi!', 'success')
        else:
            flash('Mahsulotni yangilashda xatolik yuz berdi.', 'error')
        
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/new_product.html', product=product)

@admin_bp.route('/products/<string:product_id>/delete', methods=['GET'])
@login_required
def delete_product(product_id):
    """Delete product"""
    if product_manager.delete_product(product_id):
        flash('Mahsulot muvaffaqiyatli o\'chirildi!', 'success')
    else:
        flash('Mahsulot topilmadi.', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/messages/<int:message_id>/read')
@login_required
def mark_message_read(message_id):
    """Mark message as read"""
    message_manager.mark_as_read(message_id)
    return redirect(url_for('admin.dashboard'))

def create_product_page(product):
    """Create individual product page HTML file"""
    # This function would create the product page
    # For now, we'll use the template system
    pass