#!/usr/bin/env python3
"""
Script to check Telegram library installation
"""

def check_telegram_libraries():
    """Check if Telegram libraries are properly installed"""
    print("Checking Telegram library installation...")
    
    # Check main imports
    try:
        import telegram
        print("✅ telegram module available")
    except ImportError as e:
        print(f"❌ telegram module: {e}")
        return
    
    try:
        from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
        print("✅ Required telegram classes available")
    except ImportError as e:
        print(f"❌ Required telegram classes: {e}")
    
    try:
        from telegram.ext import Dispatcher
        print("✅ telegram.ext.Dispatcher available")
    except ImportError as e:
        print(f"❌ telegram.ext.Dispatcher: {e}")

if __name__ == "__main__":
    check_telegram_libraries()