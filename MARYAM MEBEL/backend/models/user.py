import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid

class User(UserMixin):
    def __init__(self, username, email, telegram_username, first_name='', last_name='', password_hash=None, is_admin=False):
        self.id = str(uuid.uuid4())
        self.username = username
        self.email = email
        self.telegram_username = telegram_username
        self.first_name = first_name
        self.last_name = last_name
        self.password_hash = password_hash
        self.is_admin = is_admin
        self._is_active = True
        self.is_verified = False
        self.created_at = datetime.now().isoformat()
        self.last_login = None
    
    @property
    def is_active(self):
        """Return True if the user is active, required by Flask-Login"""
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        """Set the user's active status, required by Flask-Login"""
        self._is_active = value
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'telegram_username': self.telegram_username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'is_active': self._is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    @classmethod
    def from_dict(cls, data):
        user = cls(
            username=data['username'],
            email=data['email'],
            telegram_username=data['telegram_username'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            password_hash=data['password_hash'],
            is_admin=data.get('is_admin', False)
        )
        user.id = data['id']
        user.is_active = data.get('is_active', True)
        user.is_verified = data.get('is_verified', False)
        user.created_at = data.get('created_at', datetime.now().isoformat())
        user.last_login = data.get('last_login')
        return user

class UserManager:
    def __init__(self, json_file):
        self.json_file = json_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.json_file):
            os.makedirs(os.path.dirname(self.json_file), exist_ok=True)
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def load_users(self):
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [User.from_dict(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_users(self, users):
        data = [user.to_dict() for user in users]
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_user(self, user):
        users = self.load_users()
        users.append(user)
        self.save_users(users)
        return user
    
    def get_user_by_id(self, user_id):
        users = self.load_users()
        for user in users:
            if user.id == user_id:
                return user
        return None
    
    def get_user_by_username(self, username):
        users = self.load_users()
        for user in users:
            if user.username.lower() == username.lower():
                return user
        return None
    
    def get_user_by_email(self, email):
        users = self.load_users()
        for user in users:
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_user_by_telegram(self, telegram_username):
        users = self.load_users()
        # Normalize the search term by removing @ if present
        search_term = telegram_username.lstrip('@').lower()
        for user in users:
            # Normalize stored telegram username by removing @ if present
            stored_username = user.telegram_username.lstrip('@').lower() if user.telegram_username else ''
            if stored_username == search_term:
                return user
        return None
    
    def update_user(self, user):
        users = self.load_users()
        for i, u in enumerate(users):
            if u.id == user.id:
                users[i] = user
                break
        self.save_users(users)
        return user
    
    def username_exists(self, username):
        return self.get_user_by_username(username) is not None
    
    def email_exists(self, email):
        return self.get_user_by_email(email) is not None
    
    def telegram_exists(self, telegram_username):
        return self.get_user_by_telegram(telegram_username) is not None
    
    def save_user(self, user):
        """Save/update a single user"""
        return self.update_user(user)
    
    def delete_user(self, user_id):
        """Delete user by ID"""
        users = self.load_users()
        users = [user for user in users if user.id != user_id]
        self.save_users(users)
        return True

