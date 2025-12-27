# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.

import sys
import os

# Add your project directory to the sys.path
# Adjust this path to match your actual PythonAnywhere username and project location
project_home = '/home/sardor1ubaydiy/mysite/maryam-mebel/MARYAM MEBEL/backend'

# If the above path doesn't work, try this simpler path:
# project_home = '/home/sardor1ubaydiy/mysite'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Change to the project directory
os.chdir(project_home)

# Import flask app but need to call it "application" for WSGI to work
from app import app as application

# For Telegram bot webhook setup (optional - can be done manually too)
# Uncomment the following lines if you want to automatically set up the webhook on startup
"""
try:
    from app import setup_telegram_webhook, BOT_TOKEN
    import os
    
    # Get the webhook URL from environment or use default
    webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://sardor1ubaydiy.pythonanywhere.com/telegram-webhook')
    
    # Set up the webhook
    setup_telegram_webhook(BOT_TOKEN, webhook_url)
    print("Telegram webhook setup completed")
except Exception as e:
    print(f"Error setting up Telegram webhook: {e}")
"""