from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models.user import UserManager, User
from utils.telegram_service import get_telegram_service
from config.config import Config
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize user manager
user_manager = UserManager(Config.USERS_JSON)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sahifaga kirish uchun administrator huquqlari kerak.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# User loader