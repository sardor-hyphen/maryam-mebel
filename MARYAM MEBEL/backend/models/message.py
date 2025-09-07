import json
import os
from datetime import datetime

class Message:
    def __init__(self, name, phone, email, message_text):
        self.name = name
        self.phone = phone
        self.email = email
        self.message_text = message_text
        self.timestamp = datetime.now().isoformat()
        self.read = False
        self.id = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'message': self.message_text,
            'timestamp': self.timestamp,
            'read': self.read
        }
    
    @classmethod
    def from_dict(cls, data):
        message = cls(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email', ''),
            message_text=data['message']
        )
        message.id = data.get('id')
        message.timestamp = data.get('timestamp', datetime.now().isoformat())
        message.read = data.get('read', False)
        return message

class MessageManager:
    def __init__(self, json_file):
        self.json_file = json_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.json_file):
            os.makedirs(os.path.dirname(self.json_file), exist_ok=True)
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def load_messages(self):
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Message.from_dict(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_messages(self, messages):
        data = [message.to_dict() for message in messages]
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_message(self, message):
        messages = self.load_messages()
        message.id = len(messages) + 1
        messages.append(message)
        self.save_messages(messages)
        return message
    
    def mark_as_read(self, message_id):
        messages = self.load_messages()
        for message in messages:
            if message.id == message_id:
                message.read = True
                break
        self.save_messages(messages)
    
    def get_unread_count(self):
        messages = self.load_messages()
        return len([m for m in messages if not m.read])