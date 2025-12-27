#!/usr/bin/env python3
"""
Script to initialize data files if they don't exist
"""

import os
import json

def initialize_data_files():
    """Initialize data files with empty arrays if they don't exist or are invalid"""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Initialize products.json
    products_file = 'data/products.json'
    if not os.path.exists(products_file):
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"Created {products_file} with empty array")
    else:
        # Check if file is valid JSON
        try:
            with open(products_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # File is empty, initialize with empty array
                    with open(products_file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    print(f"Initialized empty {products_file} with empty array")
                else:
                    json.loads(content)  # This will raise an exception if invalid
        except (json.JSONDecodeError, FileNotFoundError):
            # File has invalid JSON, reset to empty array
            with open(products_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            print(f"Reset invalid {products_file} with empty array")
    
    # Initialize messages.json
    messages_file = 'data/messages.json'
    if not os.path.exists(messages_file):
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"Created {messages_file} with empty array")
    else:
        # Check if file is valid JSON
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # File is empty, initialize with empty array
                    with open(messages_file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    print(f"Initialized empty {messages_file} with empty array")
                else:
                    json.loads(content)  # This will raise an exception if invalid
        except (json.JSONDecodeError, FileNotFoundError):
            # File has invalid JSON, reset to empty array
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            print(f"Reset invalid {messages_file} with empty array")
    
    # Initialize users.json
    users_file = 'data/users.json'
    if not os.path.exists(users_file):
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)  # Users file uses an object, not an array
        print(f"Created {users_file} with empty object")
    else:
        # Check if file is valid JSON
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # File is empty, initialize with empty object
                    with open(users_file, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
                    print(f"Initialized empty {users_file} with empty object")
                else:
                    json.loads(content)  # This will raise an exception if invalid
        except (json.JSONDecodeError, FileNotFoundError):
            # File has invalid JSON, reset to empty object
            with open(users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            print(f"Reset invalid {users_file} with empty object")
    
    print("✅ Data files initialization completed")

if __name__ == "__main__":
    initialize_data_files()