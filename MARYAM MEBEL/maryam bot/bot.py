# -*- coding: utf-8 -*-

import sqlite3
import logging
import io
import time
import threading
import json  # Add json import for reading products
import os    # Add os import for file operations
from datetime import datetime
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

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. SOZLAMALAR (CONFIG) ---
CONFIG = {
    "BOT_TOKEN": "8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc",
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

# --- 2. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 3. MA'LUMOTLAR BAZASI ---
def setup_database():
    conn = sqlite3.connect("support_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, status TEXT DEFAULT 'active', vip_status BOOLEAN DEFAULT 0, notes TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic TEXT, status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, assigned_admin_id INTEGER, rating INTEGER, FOREIGN KEY (user_id) REFERENCES users (user_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS forwarded_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, admin_id INTEGER, message_id INTEGER, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS messages (message_db_id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, sender_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id))")
    conn.commit()
    return conn

db_connection = setup_database()

# --- 4. YORDAMCHI FUNKSIYALAR ---
def is_admin(user_id): return user_id in CONFIG["ADMIN_IDS"]

def check_subscription(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    try:
        for channel in CONFIG["CHANNELS"]:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        return True
    except Exception as e:
        logger.error(f"Kanalni tekshirishda xatolik: {e}"); return True

def get_user_profile_text(user_id: int) -> str:
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user_data = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), MAX(created_at) FROM tickets WHERE user_id=?", (user_id,))
    tickets_data = cursor.fetchone()
    if not user_data: return "Foydalanuvchi topilmadi."
    user_link = f"<a href='tg:#user?id={user_data[0]}'>{user_data[1]}</a>"
    profile = f"👤 <b>Foydalanuvchi Profili</b>\n- <b>Ismi:</b> {user_link}\n- <b>Murojaatlar soni:</b> {tickets_data[0]}\n- <b>Oxirgi murojaat:</b> {tickets_data[1].split()[0] if tickets_data[1] else 'N/A'}\n- <b>Statusi:</b> {'⭐ VIP' if user_data[4] else 'Oddiy'}\n"
    if user_data[5]: profile += f"- <b>Eslatma:</b> <i>{user_data[5]}</i>\n"
    return profile

def generate_and_send_pdf(context: CallbackContext, user):
    user_data = context.user_data.get('vacancy_info', {})
    if not user_data: return
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        main_font = 'DejaVuSans'
    except:
        logger.warning("DejaVuSans.ttf shrifti topilmadi."); main_font = "Helvetica"
    def draw_multiline_text(text, x, y):
        lines = text.split('\n'); line_height = 14
        for line in lines: p.drawString(x, y, line); y -= line_height
        return y
    p.setFont(main_font, 16)
    p.drawString(100, 750, f"Yangi Nomzod: {user_data.get('name', 'N/A')}")
    p.line(100, 748, 500, 748); y = 720; p.setFont(main_font, 12)
    fields = {"To'liq Ism-sharifi": user_data.get('name'), "Telefon raqami": user_data.get('phone'), "Yashash joyi": user_data.get('region'), "Lavozim": user_data.get('position'), "Oilaviy holati": user_data.get('status'), "Ko'nikmalari": user_data.get('skills'), "Qiziqishlari": user_data.get('interests'), "Motivatsiya": user_data.get('reason'),}
    for key, value in fields.items():
        if value: p.setFont(main_font, 10); p.drawString(100, y, key); p.setFont(main_font, 12); y = draw_multiline_text(value, 120, y - 15); y -= 15
    p.showPage(); p.save(); buffer.seek(0)
    context.bot.send_document(chat_id=CONFIG['EMPLOYER_ID'], document=buffer, filename=f"Rezyume_{user_data.get('name', 'nomzod')}.pdf", caption=f"Yangi nomzoddan rezyume.\nIsmi: {user_data.get('name')}\nLavozim: {user_data.get('position')}")

def check_and_send_new_messages(context):
    """Check for new messages in the database and send them to users"""
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
        # Path to the products.json file in the web application
        products_file_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'products.json')
        
        # Check if file exists
        if not os.path.exists(products_file_path):
            logger.warning(f"Products file not found at {products_file_path}")
            return []
        
        # Read products from file
        with open(products_file_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Sort products by creation date (newest first)
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return products
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

def show_catalog_menu(update: Update, context: CallbackContext):
    """Show catalog menu with categories"""
    # Get products from web application
    products = get_products_from_web()
    
    # Get unique categories
    categories = get_unique_categories(products)
    
    if not categories:
        update.message.reply_text("Hozirda katalog bo'sh. Iltimos, keyinroq qaytib ko'ring.")
        return
    
    # Create keyboard with categories
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Quyidagi kategoriyalardan birini tanlang:", reply_markup=reply_markup)

def category_callback(update: Update, context: CallbackContext):
    """Handle category selection"""
    query = update.callback_query
    category = query.data.split("_", 1)[1]  # Get category name (everything after "cat_")
    query.answer()
    
    # Get products from web application
    products = get_products_from_web()
    
    # Filter products by category
    category_products = [p for p in products if p.get('category') == category]
    
    if not category_products:
        query.edit_message_text(
            f"{category} kategoriyasida hozirda mahsulotlar mavjud emas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")]])
        )
        return
    
    # Create message with category products
    message_text = f"🛍️ <b>{category} uchun mahsulotlar</b>\n\nQuyidagilar👇"
    
    # Create keyboard with products
    keyboard = []
    for product in category_products:
        product_name = product.get('name', 'Noma\'lum')
        product_slug = product.get('slug', '')
        if product_slug:
            keyboard.append([InlineKeyboardButton(product_name, callback_data=f"prod_{product_slug}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(message_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def product_callback(update: Update, context: CallbackContext):
    """Handle product selection"""
    query = update.callback_query
    product_slug = query.data.split("_", 1)[1]  # Get product slug (everything after "prod_")
    query.answer()
    
    # Get products from web application
    products = get_products_from_web()
    
    # Find the selected product
    selected_product = None
    for product in products:
        if product.get('slug') == product_slug:
            selected_product = product
            break
    
    if not selected_product:
        query.edit_message_text(
            "Mahsulot topilmadi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="catalog_menu")]])
        )
        return
    
    # Create product details message
    product_name = selected_product.get('name', 'Noma\'lum')
    product_description = selected_product.get('description', 'Tavsif mavjud emas')
    product_category = selected_product.get('category', 'Noma\'lum')
    product_material = selected_product.get('material', 'Noma\'lum')
    product_year = selected_product.get('year', 'Noma\'lum')
    product_warranty = selected_product.get('warranty', 'Noma\'lum')
    product_includes = selected_product.get('includes', 'Noma\'lum')
    
    message_text = f"🛍️ <b>{product_name}</b>\n\n"
    message_text += f"📋 <b>Tavsif:</b> {product_description}\n\n"
    message_text += f"🏷️ <b>Kategoriya:</b> {product_category}\n"
    message_text += f"🪵 <b>Material:</b> {product_material}\n"
    message_text += f"📅 <b>Ishlab chiqarilgan yili:</b> {product_year}\n"
    message_text += f"🛡️ <b>Kafolat:</b> {product_warranty}\n"
    message_text += f"📦 <b>Mahsulot tarkibi:</b> {product_includes}\n\n"
    message_text += "📞 Buyurtma berish uchun /contact tugmasini bosing"
    
    # Get main image if available
    main_image = selected_product.get('main_image', '')
    
    # Create keyboard with back button
    keyboard = [
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"cat_{product_category}")],
        [InlineKeyboardButton("🏠 Bosh menyuga", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send product details with main image if available
    if main_image and main_image.startswith('/static/'):
        # Convert web path to local file path
        image_path = os.path.join(os.path.dirname(__file__), '..', 'backend', main_image.lstrip('/'))
        if os.path.exists(image_path):
            try:
                query.edit_message_text("Rasm yuborilmoqda...")
                context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=open(image_path, 'rb'),
                    caption=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                query.edit_message_text("Mahsulot tafsilotlari yuqorida ko'rsatilgan.")
                return
            except Exception as e:
                logger.error(f"Error sending product image: {e}")
    
    # If no image or error, send text only
    query.edit_message_text(message_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["✍️ Murojaat yuborish"], 
        ["📄 Vakansiyalar", "💬 Mening chatlarim"],
         # Add catalog button as a separate row
        ["📦 Buyurtma berish"]  # Add direct order button
    ], resize_keyboard=True)

(GET_NAME, GET_PHONE, GET_REGION, GET_SKILLS, GET_INTERESTS, GET_POSITION, GET_STATUS, GET_REASON) = range(8)

# --- 5. ASOSIY HANDLERLAR ---

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    cursor = db_connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user.id, user.first_name, user.username))
    db_connection.commit()
    update.message.reply_text("Assalomu alaykum! Bosh menyudasiz. Kerakli bo'limni tanlang:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

def open_support_menu(update: Update, context: CallbackContext):
    if not check_subscription(update, context):
        channels_text = "\n".join(CONFIG["CHANNELS"])
        keyboard = [[InlineKeyboardButton("✅ A'zo bo'ldim", callback_data="check_sub")]]
        update.message.reply_text(f"Murojaat yuborish uchun quyidagi kanallarga a'zo bo'ling:\n\n{channels_text}", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    show_topic_menu(update, context)

def check_sub_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    if check_subscription(update, context):
        query.delete_message(); show_topic_menu(update, context, query.message.chat_id)
    else:
        query.answer("Siz hali barcha kanallarga a'zo bo'lmadingiz.", show_alert=True)

def show_topic_menu(update: Update, context: CallbackContext, chat_id=None, is_edit=False):
    keyboard = []
    for key, value in CONFIG["TOPICS"].items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"topic_{key}")])
    keyboard.append([InlineKeyboardButton("💬 Mening chatlarim", callback_data="my_chats")])
    text = "Murojaatingiz mavzusini tanlang yoki suhbatlar tarixini ko'ring:"
    effective_chat_id = chat_id or (update.effective_chat.id if update else None)
    if is_edit:
        try: update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except: context.bot.send_message(effective_chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        try: update.message.delete()
        except: pass
        context.bot.send_message(effective_chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

def topic_callback(update: Update, context: CallbackContext):
    query = update.callback_query; topic = query.data.split("_")[1]
    context.user_data['selected_topic'] = topic; topic_text = CONFIG["TOPICS"].get(topic, "Umumiy"); query.answer()
    keyboard = [[InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")]]; reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Siz '{topic_text}' mavzusini tanladingiz. Endi murojaatingizni yozib yuboring.", reply_markup=reply_markup)

def handle_user_message(update: Update, context: CallbackContext):
    user = update.effective_user; topic = context.user_data.get('selected_topic')
    if not topic:
        update.message.reply_text("Iltimos, avval '✍️ Murojaat yuborish' tugmasini bosib, mavzuni tanlang."); return
    cursor = db_connection.cursor()
    cursor.execute("INSERT INTO tickets (user_id, topic) VALUES (?, ?)", (user.id, topic)); ticket_id = cursor.lastrowid
    cursor.execute("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text) VALUES (?, ?, ?, ?)", (ticket_id, user.id, "Siz", update.message.text))
    db_connection.commit(); profile_text = get_user_profile_text(user.id)
    admin_message_text = f"🔹 <b>Yangi Murojaat!</b> #{ticket_id}\n<b>Mavzu:</b> {CONFIG['TOPICS'].get(topic, 'N/A')}\n\n{profile_text}\n---\n<b>Xabar:</b>\n\"{update.message.text}\""
    keyboard = [[InlineKeyboardButton("✅ Javob berishni boshlash", callback_data=f"claim_{ticket_id}")]]
    target_admins = CONFIG["TOPIC_ADMINS"].get(topic) or CONFIG["ADMIN_IDS"]
    for admin_id in target_admins:
        try:
            msg = context.bot.send_message(chat_id=admin_id, text=admin_message_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
            cursor.execute("INSERT INTO forwarded_messages (ticket_id, admin_id, message_id) VALUES (?, ?, ?)", (ticket_id, admin_id, msg.message_id))
            db_connection.commit()
        except Exception as e: logger.error(f"{admin_id} ga xabar yuborishda xatolik: {e}")
    update.message.reply_text(f"✅ Murojaatingiz qabul qilindi. Tez orada mutaxassisimiz javob beradi.\nMurojaat raqamingiz: #{ticket_id}")
    context.user_data.pop('selected_topic', None)

def admin_claim_callback(update: Update, context: CallbackContext):
    query = update.callback_query; admin_user = query.from_user; ticket_id = int(query.data.split("_")[1]); cursor = db_connection.cursor()
    cursor.execute("SELECT admin_id, message_id FROM forwarded_messages WHERE ticket_id=? AND admin_id!=?", (ticket_id, admin_user.id)); messages_to_delete = cursor.fetchall()
    for admin_id, message_id in messages_to_delete:
        try: context.bot.delete_message(chat_id=admin_id, message_id=message_id)
        except Exception as e: logger.warning(f"Eski xabarni o'chirishda xatolik: {e}")
    is_from_panel = query.message and query.message.text and "Admin Paneli" in query.message.text
    if is_from_panel: query.answer("Murojaat qabul qilindi!"); admin_panel(update, context, is_edit=True, page=0)
    else:
        try: query.edit_message_text(f"✅ Murojaat #{ticket_id} siz tomondan qabul qilindi.\n\nFoydalanuvchiga javob berish uchun ushbu xabarga 'Reply' qiling.")
        except Exception as e: logger.warning(f"Xabarni tahrirlashda xatolik: {e}")
    cursor.execute("UPDATE tickets SET assigned_admin_id=?, status='claimed' WHERE ticket_id=?", (admin_user.id, ticket_id))
    cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,)); user_id = cursor.fetchone()[0]; db_connection.commit()
    context.bot.send_message(chat_id=user_id, text=f"⏳ Sizning #{ticket_id}-raqamli murojaatingiz mutaxassis {admin_user.first_name} tomonidan ko'rib chiqilmoqda.")
    if not is_from_panel: query.answer("Murojaat qabul qilindi!")

def handle_admin_reply(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id): return
    admin_reply_text = update.message.text; replied_msg_id = update.message.reply_to_message.message_id; admin_user = update.effective_user; cursor = db_connection.cursor()
    cursor.execute("SELECT ticket_id FROM forwarded_messages WHERE message_id=? AND admin_id=?", (replied_msg_id, admin_user.id)); result = cursor.fetchone()
    if not result: return
    ticket_id = result[0]
    cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,)); user_id = cursor.fetchone()[0]
    try:
        context.bot.send_message(chat_id=user_id, text=admin_reply_text)
        admin_name = f"Admin ({admin_user.first_name})"
        cursor.execute("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text) VALUES (?, ?, ?, ?)", (ticket_id, admin_user.id, admin_name, admin_reply_text))
        try:
            context.bot.delete_message(chat_id=admin_user.id, message_id=replied_msg_id)
            context.bot.delete_message(chat_id=admin_user.id, message_id=update.message.message_id)
        except Exception as e: logger.warning(f"Admin chatini tozalashda xatolik: {e}")
        context.bot.send_message(chat_id=admin_user.id, text=f"✅ #{ticket_id} raqamli murojaatga javob yuborildi.")
        cursor.execute("UPDATE tickets SET status='closed' WHERE ticket_id=?", (ticket_id,)); db_connection.commit()
        keyboard = [[InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_5"), InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_4"), InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate_{ticket_id}_3")], [InlineKeyboardButton("⭐⭐", callback_data=f"rate_{ticket_id}_2"), InlineKeyboardButton("⭐", callback_data=f"rate_{ticket_id}_1")]]
        context.bot.send_message(chat_id=user_id, text="Bizning yordamimizdan qoniqdingizmi? Iltimos, xizmat sifatini baholang.", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        update.message.reply_text(f"❌ Xatolik: Foydalanuvchiga xabar yuborib bo'lmadi.\n\n{e}")

def rating_callback(update: Update, context: CallbackContext):
    query = update.callback_query; _, ticket_id, rating = query.data.split("_"); cursor = db_connection.cursor()
    cursor.execute("UPDATE tickets SET rating=? WHERE ticket_id=?", (int(rating), int(ticket_id))); db_connection.commit()
    query.answer("Bahoyingiz uchun rahmat!"); query.edit_message_text(f"Siz xizmatimizni {rating}⭐ ga baholadingiz. Rahmat!")

def admin_panel(update: Update, context: CallbackContext, is_edit: bool = False, page: int = 0):
    if not is_admin(update.effective_user.id): update.message.reply_text("Sizda bu buyruq uchun ruxsat yo'q."); return
    cursor = db_connection.cursor(); offset = page * PANEL_PAGE_SIZE
    cursor.execute("SELECT ticket_id, topic, created_at, user_id FROM tickets WHERE status='open' OR status='claimed' ORDER BY created_at ASC LIMIT ? OFFSET ?", (PANEL_PAGE_SIZE, offset))
    open_tickets = cursor.fetchall(); cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='open' OR status='claimed'"); total_open_tickets = cursor.fetchone()[0]
    panel_text = f"📊 <b>Admin Paneli</b>\nJavob kutayotgan murojaatlar: {total_open_tickets}\n\n"; keyboard = []
    if not open_tickets: panel_text += "Hozirda javob kutayotgan murojaatlar mavjud emas."
    else:
        for ticket_id, topic, created_at, user_id in open_tickets:
            topic_text = CONFIG['TOPICS'].get(topic, 'Noma‘lum').split()[1]; button_text = f"#{ticket_id} - {topic_text} ({created_at.split()[0]})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"panel_view_{ticket_id}_{page}")])
    pagination_buttons = []
    if page > 0: pagination_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"panel_page_{page-1}"))
    if total_open_tickets > (page + 1) * PANEL_PAGE_SIZE: pagination_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"panel_page_{page+1}"))
    if pagination_buttons: keyboard.append(pagination_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if is_edit:
        try: update.callback_query.edit_message_text(panel_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as e: logger.warning(f"Panelni tahrirlashda xatolik: {e}")
    else:
        update.message.reply_text(panel_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def panel_page_callback(update: Update, context: CallbackContext):
    query = update.callback_query; page = int(query.data.split("_")[2]); query.answer(); admin_panel(update, context, is_edit=True, page=page)

def panel_view_ticket_callback(update: Update, context: CallbackContext):
    query = update.callback_query; _, _, ticket_id, page = query.data.split("_"); ticket_id = int(ticket_id); page = int(page); cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, topic FROM tickets WHERE ticket_id=?", (ticket_id,)); ticket_data = cursor.fetchone()
    if not ticket_data: query.answer("Bu murojaat topilmadi.", show_alert=True); return
    user_id, topic = ticket_data; cursor.execute("SELECT message_text FROM messages WHERE ticket_id=? ORDER BY sent_at ASC LIMIT 1", (ticket_id,)); first_message = cursor.fetchone()[0]
    profile_text = get_user_profile_text(user_id)
    view_text = f"🔹 <b>Murojaat #{ticket_id}</b>\n<b>Mavzu:</b> {CONFIG['TOPICS'].get(topic, 'N/A')}\n\n{profile_text}\n---\n<b>Xabar:</b>\n\"{first_message}\""
    keyboard = [[InlineKeyboardButton("✅ Javob berishni boshlash", callback_data=f"claim_{ticket_id}")], [InlineKeyboardButton("⬅️ Panelga qaytish", callback_data=f"panel_page_{page}")]]
    query.answer(); query.edit_message_text(view_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def my_chats_callback(update: Update, context: CallbackContext):
    query = update.callback_query; user_id = query.from_user.id if query else update.effective_user.id
    cursor = db_connection.cursor()
    cursor.execute("SELECT ticket_id, topic, status FROM tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
    tickets = cursor.fetchall()
    if not tickets:
        if query: query.answer("Sizda hali murojaatlar mavjud emas.", show_alert=True)
        else: update.message.reply_text("Sizda hali murojaatlar mavjud emas.")
        return
    keyboard = []
    for ticket_id, topic, status in tickets:
        status_icon = "✅" if status == "closed" else "⏳"; topic_text = CONFIG['TOPICS'].get(topic, 'Noma‘lum mavzu').replace("📦 ", "").replace("⚙️ ", "").replace("🤝 ", "").replace("💡 ", "")
        button_text = f"#{ticket_id} - {topic_text} {status_icon}"; keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_ticket_{ticket_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])
    if query: query.answer(); query.edit_message_text("Murojaatlaringiz tarixi:", reply_markup=InlineKeyboardMarkup(keyboard))
    else: update.message.reply_text("Murojaatlaringiz tarixi:", reply_markup=InlineKeyboardMarkup(keyboard))

def view_ticket_callback(update: Update, context: CallbackContext):
    query = update.callback_query; ticket_id = int(query.data.split("_")[2]); cursor = db_connection.cursor()
    cursor.execute("SELECT sender_name, message_text FROM messages WHERE ticket_id=? ORDER BY sent_at ASC", (ticket_id,)); messages = cursor.fetchall()
    conversation_text = f"<b>Suhbat tarixi: Murojaat #{ticket_id}</b>\n\n"
    for sender, text in messages: conversation_text += f"<b>{sender}:</b>\n{text}\n\n"
    keyboard = [[InlineKeyboardButton("⬅️ Ro'yxatga qaytish", callback_data="my_chats")]]; query.answer()
    query.edit_message_text(conversation_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def back_to_menu_callback(update: Update, context: CallbackContext):
    show_topic_menu(update, context, update.callback_query.message.chat_id, is_edit=True); update.callback_query.answer()

# Add the show_direct_order_menu function here
def show_direct_order_menu(update: Update, context: CallbackContext):
    """Show direct order menu with categories"""
    # Get products from web application
    products = get_products_from_web()
    
    # Get unique categories
    categories = get_unique_categories(products)
    
    if not categories:
        update.message.reply_text("Hozirda katalog bo'sh. Iltimos, keyinroq qaytib ko'ring.")
        return
    
    # Create keyboard with categories
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Bosh menyuga qaytish", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Quyidagi kategoriyalardan birini tanlang:", reply_markup=reply_markup)

# --- VAKANSIYA FUNKSIYALARI ---
def vacancy_start(update: Update, context: CallbackContext):
    context.user_data['vacancy_info'] = {}; update.message.reply_text("Rezyume to'ldirishni boshladik.\n\nIltimos, to'liq ism-sharifingizni yozing:", reply_markup=ReplyKeyboardRemove()); return GET_NAME

def get_name(update: Update, context: CallbackContext):
    context.user_data['vacancy_info']['name'] = update.message.text
    keyboard = [[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]]; update.message.reply_text("Rahmat. Endi telefon raqamingizni '📞 Raqamni yuborish' tugmasi orqali yuboring.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)); return GET_PHONE

def get_phone(update: Update, context: CallbackContext):
    context.user_data['vacancy_info']['phone'] = update.message.contact.phone_number
    # -- TO'G'RILANGAN QISM --
    update.message.reply_text("Raqam qabul qilindi!", reply_markup=ReplyKeyboardRemove())
    regions = ["Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Xorazm", "Namangan", "Navoiy", "Qashqadaryo", "Samarqand", "Sirdaryo", "Surxondaryo", "Qoraqalpog'iston"]
    keyboard = [[InlineKeyboardButton(r, callback_data=f"region_{r}")] for r in regions]; update.message.reply_text("Yashash joyingizni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard)); return GET_REGION

def get_region(update: Update, context: CallbackContext):
    query = update.callback_query; context.user_data['vacancy_info']['region'] = query.data.split('_', 1)[1]; query.answer()
    query.edit_message_text("Ko'nikmalaringizni yozing (masalan: Kompyuter savodxonligi, Payvandlash, Sotuv...):"); return GET_SKILLS

def get_skills(update: Update, context: CallbackContext):
    context.user_data['vacancy_info']['skills'] = update.message.text
    update.message.reply_text("Qiziqishlaringizni yozing (masalan: Kitob o'qish, Futbol, Dasturlash...):"); return GET_INTERESTS

def get_interests(update: Update, context: CallbackContext):
    context.user_data['vacancy_info']['interests'] = update.message.text
    positions = ["Oddiy ishchi", "Omborchi", "Haydovchi", "Mebel ustasi", "Sotuv menejeri", "Buxgalter", "HR menejeri", "Bo'lim boshlig'i", "Direktor (CEO)"]
    keyboard = [[InlineKeyboardButton(p, callback_data=f"pos_{p}")] for p in positions]; update.message.reply_text("Qaysi lavozimga qiziqasiz?", reply_markup=InlineKeyboardMarkup(keyboard)); return GET_POSITION

def get_position(update: Update, context: CallbackContext):
    query = update.callback_query; context.user_data['vacancy_info']['position'] = query.data.split('_', 1)[1]; query.answer()
    statuses = ["Kambag'al", "O'rta hol", "Yaxshi", "Boy"] # Oilaviy holat deb so'ralgan edi, lekin bu yerda moddiy holat
    keyboard = [[InlineKeyboardButton(s, callback_data=f"status_{s}")] for s in statuses]; query.edit_message_text("Moddiy holatingizni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard)); return GET_STATUS

def get_status(update: Update, context: CallbackContext):
    query = update.callback_query; context.user_data['vacancy_info']['status'] = query.data.split('_', 1)[1]; query.answer()
    query.edit_message_text("Nima uchun aynan bizning kompaniyamizda ishlashni xohlaysiz? Qisqacha yozing."); return GET_REASON

def get_reason(update: Update, context: CallbackContext):
    context.user_data['vacancy_info']['reason'] = update.message.text
    update.message.reply_text("✅ Murojaatingiz qabul qilindi! Ma'lumotlaringiz kadrlar bo'limiga yuborildi. Tez orada siz bilan bog'lanamiz.", reply_markup=main_menu_keyboard())
    generate_and_send_pdf(context, update.effective_user); context.user_data.pop('vacancy_info', None); return ConversationHandler.END

def cancel_vacancy(update: Update, context: CallbackContext):
    update.message.reply_text("Rezyume to'ldirish bekor qilindi.", reply_markup=main_menu_keyboard()); context.user_data.pop('vacancy_info', None); return ConversationHandler.END

# --- 7. BOTNI ISHGA TUSHIRISH ---
def main():
    updater = Updater(CONFIG["BOT_TOKEN"], use_context=True)
    dp = updater.dispatcher

    vacancy_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^📄 Vakansiyalar$'), vacancy_start)],
        states={
            GET_NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            GET_PHONE: [MessageHandler(Filters.contact, get_phone)],
            GET_REGION: [CallbackQueryHandler(get_region, pattern="^region_")],
            GET_SKILLS: [MessageHandler(Filters.text & ~Filters.command, get_skills)],
            GET_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, get_interests)],
            GET_POSITION: [CallbackQueryHandler(get_position, pattern="^pos_")],
            GET_STATUS: [CallbackQueryHandler(get_status, pattern="^status_")],
            GET_REASON: [MessageHandler(Filters.text & ~Filters.command, get_reason)],
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('cancel', cancel_vacancy)]
    )
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex('^✍️ Murojaat yuborish$'), open_support_menu))
    dp.add_handler(MessageHandler(Filters.regex('^💬 Mening chatlarim$'), my_chats_callback))
    dp.add_handler(vacancy_conv_handler)
    dp.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    dp.add_handler(CallbackQueryHandler(topic_callback, pattern="^topic_"))
    dp.add_handler(CallbackQueryHandler(rating_callback, pattern="^rate_"))
    dp.add_handler(CallbackQueryHandler(my_chats_callback, pattern="^my_chats$"))
    dp.add_handler(CallbackQueryHandler(view_ticket_callback, pattern="^view_ticket_"))
    dp.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    dp.add_handler(CommandHandler("panel", admin_panel, filters=Filters.user(CONFIG["ADMIN_IDS"])))
    dp.add_handler(CallbackQueryHandler(panel_page_callback, pattern="^panel_page_"))
    dp.add_handler(CallbackQueryHandler(panel_view_ticket_callback, pattern="^panel_view_"))
    dp.add_handler(CallbackQueryHandler(admin_claim_callback, pattern="^claim_"))
    dp.add_handler(MessageHandler(Filters.reply & Filters.user(CONFIG["ADMIN_IDS"]), handle_admin_reply))
    # Add handler for direct order button
    dp.add_handler(MessageHandler(Filters.regex('^📦 Buyurtma berish$'), show_direct_order_menu))
    
    # Keep the existing handlers
    dp.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    dp.add_handler(CallbackQueryHandler(product_callback, pattern="^prod_"))
    dp.add_handler(CallbackQueryHandler(show_catalog_menu, pattern="^catalog_menu$"))
    
    # Update the message handler to handle catalog commands
    # This should be the last handler as it's a catch-all
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_message))
    
    updater.start_polling()
    logger.info("Bot ishga tushdi...")
    
    # Start checking for new messages
    def periodic_message_check():
        while True:
            try:
                time.sleep(15)  # Check every 15 seconds
                # Pass the updater's dispatcher to the function
                check_and_send_new_messages(updater.dispatcher)
            except Exception as e:
                logger.error(f"Error in periodic message check: {e}")
    
    message_check_thread = threading.Thread(target=periodic_message_check, name="MessageChecker")
    message_check_thread.daemon = True
    message_check_thread.start()
    
    updater.idle()

if __name__ == '__main__':
    main()

