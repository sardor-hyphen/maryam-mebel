# PythonAnywhere Deployment Instructions

## WSGI Configuration

1. Create or update your WSGI file at `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Change to the project directory
os.chdir(project_home)

# Import flask app but need to call it "application" for WSGI to work
from app import app as application
```

2. Make sure to replace `yourusername` with your actual PythonAnywhere username and adjust the path to match your actual project location.

## Environment Variables

Set the following environment variables in your PythonAnywhere dashboard:

1. Go to the "Web" tab
2. Click on your web app
3. Scroll down to "Environment variables"
4. Add the following variables:

```
BOT_TOKEN=8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc
TELEGRAM_WEBHOOK_URL=https://yourusername.pythonanywhere.com/telegram-webhook
ADMIN_USERNAME=admin
ADMIN_PASSWORD=maryam2025
ADMIN_IDS=5559190705,5399658464
```

## Data Files Initialization

Before running the application, make sure to initialize the data files:

1. Open a Bash console in PythonAnywhere
2. Navigate to your project directory:
   ```bash
   cd /home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend
   ```

3. Run the data initialization script:
   ```bash
   python initialize_data.py
   ```

This will create the necessary data files (`data/products.json`, `data/messages.json`, and `data/users.json`) if they don't exist or are invalid.

If the script doesn't work properly, you can manually create the files:
- `data/products.json` should contain: `[]`
- `data/messages.json` should contain: `[]`
- `data/users.json` should contain: `{}`

## Setting up the Telegram Webhook

You have two options to set up the Telegram webhook:

### Option 1: Manual setup using PythonAnywhere console

1. Open a Bash console in PythonAnywhere
2. Navigate to your project directory:
   ```bash
   cd /home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend
   ```

3. Run the webhook setup command:
   ```bash
   python app.py webhook
   ```

### Option 2: Automatic setup in WSGI file

Uncomment the webhook setup section in your WSGI file:

```python
# For Telegram bot webhook setup (optional - can be done manually too)
try:
    from app import setup_telegram_webhook, BOT_TOKEN
    import os
    
    # Get the webhook URL from environment or use default
    webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://yourusername.pythonanywhere.com/telegram-webhook')
    
    # Set up the webhook
    setup_telegram_webhook(BOT_TOKEN, webhook_url)
    print("Telegram webhook setup completed")
except Exception as e:
    print(f"Error setting up Telegram webhook: {e}")
```

## Testing the Telegram Bot

To test if the Telegram bot is working properly:

1. Open a Bash console in PythonAnywhere
2. Navigate to your project directory:
   ```bash
   cd /home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend
   ```

3. Run the diagnostic script:
   ```bash
   python check_telegram_webhook.py
   ```

4. For a more comprehensive test:
   ```bash
   python test_telegram_bot.py
   ```

5. To interactively set up the webhook:
   ```bash
   python test_telegram_bot.py setup
   ```

## Favicon

The application now includes a favicon.ico file generated from the logo.png file. The favicon is served at `/favicon.ico` and should automatically be used by browsers.

If you want to update the favicon:
1. Replace `static/logo.png` with your new logo
2. Run the favicon generation script:
   ```bash
   python generate_favicon.py
   ```

## Troubleshooting

### Common Issues:

1. **ModuleNotFoundError: No module named 'app'**
   - Check that your project_home path in the WSGI file is correct
   - Make sure the path points to the directory containing app.py
   - Verify that the directory structure is correct

2. **Import errors**
   - Ensure all required packages are installed in your PythonAnywhere virtual environment:
     ```bash
     pip install -r requirements.txt
     ```

3. **Telegram webhook issues**
   - Verify that your webhook URL is correct and accessible
   - Check that the Telegram bot token is correct
   - Make sure the webhook route `/telegram-webhook` is properly defined in app.py
   - Run the diagnostic scripts to check webhook status

4. **Favicon not showing**
   - Make sure `static/favicon.ico` exists
   - Check that the favicon route is defined in app.py
   - Clear your browser cache

5. **JSON Decode Errors (Expecting value: line 1 column 1 (char 0))**
   - Run the data initialization script to fix empty or invalid JSON files:
     ```bash
     python initialize_data.py
     ```
   - This will create valid empty JSON arrays in `data/products.json` and `data/messages.json`
   - If the script doesn't work, manually create the files with:
     - `data/products.json`: `[]`
     - `data/messages.json`: `[]`
     - `data/users.json`: `{}`

### Telegram Bot Troubleshooting:

1. **Bot not responding to messages**
   - Check webhook status with `python check_telegram_webhook.py`
   - Ensure the webhook URL is accessible from the internet
   - Verify the bot token is correct
   - Check PythonAnywhere error logs for webhook endpoint errors

2. **Webhook not set**
   - Run `python app.py webhook` to set the webhook
   - Or use the interactive setup: `python test_telegram_bot.py setup`

3. **Webhook URL not accessible**
   - Ensure your PythonAnywhere web app is running
   - Check that the `/telegram-webhook` route is defined in app.py
   - Verify the URL format is correct (should end with `/telegram-webhook`)

### Path Debugging:

If you're having issues with paths, you can add debugging to your WSGI file:

```python
import sys
import os

print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Project home:", '/home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend')

# List files in project directory
try:
    print("Files in project directory:", os.listdir('/home/yourusername/mysite/maryam-mebel/MARYAM MEBEL/backend'))
except Exception as e:
    print("Error listing directory:", e)
```

## File Structure

Make sure your file structure looks like this:

```
/home/yourusername/mysite/
└── maryam-mebel/
    └── MARYAM MEBEL/
        ├── backend/
        │   ├── app.py
        │   ├── wsgi.py
        │   ├── .env
        │   ├── requirements.txt
        │   ├── static/
        │   │   ├── favicon.ico
        │   │   ├── logo.png
        │   │   └── ...
        │   ├── data/
        │   │   ├── products.json
        │   │   ├── messages.json
        │   │   └── users.json
        │   └── ...
        ├── maryam bot/
        │   └── bot.py
        └── requirements.txt
```

## Database Setup

Make sure the Telegram bot database file is accessible:

1. The database file should be at: `maryam bot/support_bot.db`
2. Ensure the path in app.py correctly points to this file:
   ```python
   bot_db_path = os.path.join(os.path.dirname(__file__), '..', 'maryam bot', 'support_bot.db')
   ```