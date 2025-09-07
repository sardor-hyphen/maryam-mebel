import sqlite3
import os
from datetime import datetime

def send_order_notification_to_telegram(order_data):
    """
    Send order notification to Telegram bot by inserting directly into its database.
    
    Args:
        order_data (dict): Dictionary containing order information
            - name (str): Customer name
            - phone (str): Customer phone number
            - email (str): Customer email (optional)
            - message (str): Order message
            - product_name (str): Product name (optional)
            - product_slug (str): Product slug (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Path to the Telegram bot database
        bot_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'maryam bot', 'support_bot.db')
        
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
        message_text = f"📦 YANGI BUYURTMA\n\n"
        message_text += f"Ism: {order_data.get('name', 'Noma\'lum')}\n"
        message_text += f"Telefon: {order_data.get('phone', 'Noma\'lum')}\n"
        
        if order_data.get('email'):
            message_text += f"Email: {order_data.get('email')}\n"
        
        if order_data.get('product_name'):
            message_text += f"Mahsulot: {order_data.get('product_name')}\n"
        
        message_text += f"\nXabar: {order_data.get('message', '')}"
        
        # Insert the message
        cursor.execute(
            "INSERT INTO messages (ticket_id, sender_id, sender_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, 0, "Mijoz", message_text, datetime.now().isoformat())
        )
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error sending order notification to Telegram bot: {e}")
        return False