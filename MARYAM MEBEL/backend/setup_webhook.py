#!/usr/bin/env python3
"""
Script to set up Telegram webhook for PythonAnywhere deployment
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def setup_webhook():
    """Set up the Telegram webhook"""
    try:
        # Import the webhook setup function
        from app import setup_telegram_webhook
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get configuration from environment variables
        bot_token = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')
        webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL', '')
        
        if not webhook_url:
            print("Error: TELEGRAM_WEBHOOK_URL environment variable not set")
            print("Please set it to your PythonAnywhere URL + /telegram-webhook")
            print("Example: https://yourusername.pythonanywhere.com/telegram-webhook")
            return False
        
        print(f"Setting up Telegram webhook...")
        print(f"Bot Token: {bot_token[:10]}...")
        print(f"Webhook URL: {webhook_url}")
        
        result = setup_telegram_webhook(bot_token, webhook_url)
        
        if result:
            print("✅ Telegram webhook setup successful!")
            return True
        else:
            print("❌ Failed to set up Telegram webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up Telegram webhook: {e}")
        return False

def remove_webhook():
    """Remove the Telegram webhook"""
    try:
        # Import the webhook removal function
        from app import remove_telegram_webhook
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get configuration from environment variables
        bot_token = os.environ.get('BOT_TOKEN', '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc')
        
        print(f"Removing Telegram webhook...")
        print(f"Bot Token: {bot_token[:10]}...")
        
        result = remove_telegram_webhook(bot_token)
        
        if result:
            print("✅ Telegram webhook removed successfully!")
            return True
        else:
            print("❌ Failed to remove Telegram webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error removing Telegram webhook: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'remove':
        remove_webhook()
    else:
        setup_webhook()