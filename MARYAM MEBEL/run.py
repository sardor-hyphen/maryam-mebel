#!/usr/bin/env python3
"""
Run script for MARYAM MEBEL application.
This script starts both the Flask web application and the Telegram bot.
"""

import os
import sys
import subprocess
import threading
import time

def run_flask_app():
    """Run the Flask web application"""
    try:
        # Change to backend directory
        os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))
        print("Starting Flask web application...")
        # Run the Flask app
        subprocess.run([sys.executable, 'app.py'])
    except Exception as e:
        print(f"Error running Flask app: {e}")

def run_telegram_bot():
    """Run the Telegram bot"""
    try:
        # Change to maryam bot directory
        os.chdir(os.path.join(os.path.dirname(__file__), 'maryam bot'))
        print("Starting Telegram bot...")
        # Run the Telegram bot
        subprocess.run([sys.executable, 'bot.py'])
    except Exception as e:
        print(f"Error running Telegram bot: {e}")

def main():
    """Main function to run both applications"""
    print("Starting MARYAM MEBEL application...")

    # Save the original directory
    original_dir = os.getcwd()

    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Give Flask app time to start
    print("Waiting for Flask app to start...")
    time.sleep(3)

    # Change back to original directory
    os.chdir(original_dir)

    # Start Telegram bot in a separate thread
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    print("Both applications started. Press Ctrl+C to stop.")

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down applications...")
        sys.exit(0)

if __name__ == "__main__":
    main()