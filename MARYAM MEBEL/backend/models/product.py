import json
import os
from datetime import datetime
import uuid

class Product:
    def __init__(self, name, slug, description, category, material, year, warranty, includes, price, main_image='', gallery_images=None, discount=0, is_active=True, id=None, ratings=None):
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.slug = slug
        self.description = description
        self.category = category
        self.material = material
        self.year = year
        self.warranty = warranty
        self.includes = includes
        self.main_image = main_image
        self.gallery_images = gallery_images or []
        self.created_at = datetime.now().isoformat()
        self.price = price
        self.discount = discount
        self.is_active = is_active
        self.ratings = ratings or []  # List to store user ratings
    
    def to_dict(self):
        return {
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'material': self.material,
            'year': self.year,
            'warranty': self.warranty,
            'includes': self.includes,
            'price': self.price,
            'discount': self.discount,
            'main_image': self.main_image,
            'gallery_images': self.gallery_images,
            'created_at': self.created_at,
            'id': self.id,
            'is_active': self.is_active,
            'ratings': self.ratings  # Include ratings in dictionary
        }
    
    @classmethod
    def from_dict(cls, data):
        product = cls(
            name=data['name'],
            slug=data['slug'],
            description=data['description'],
            category=data['category'],
            material=data['material'],
            year=data['year'],
            warranty=data['warranty'],
            includes=data['includes'],
            main_image=data.get('main_image', ''),
            gallery_images=data.get('gallery_images', []),
            price=data.get('price', 0),
            discount=data.get('discount', 0),
            is_active=data.get('is_active', True),
            id=data.get('id') if data.get('id') else str(uuid.uuid4()),
            ratings=data.get('ratings', [])  # Get ratings from data
        )
        product.created_at = data.get('created_at', datetime.now().isoformat())
        return product

class ProductManager:
    def __init__(self, json_file):
        self.json_file = json_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.json_file):
            os.makedirs(os.path.dirname(self.json_file), exist_ok=True)
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def load_products(self):
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Product.from_dict(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_products(self, products):
        data = [product.to_dict() for product in products]
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_product(self, product):
        products = self.load_products()
        products.append(product)
        self.save_products(products)
    
    def update_product(self, product_id, updated_product):
        """Update an existing product by ID"""
        products = self.load_products()
        for i, product in enumerate(products):
            if product.id == product_id:
                products[i] = updated_product
                self.save_products(products)
                return True
        return False
    
    def delete_product(self, product_id):
        """Delete a product by ID"""
        products = self.load_products()
        updated_products = [p for p in products if p.id != product_id]
        if len(updated_products) != len(products):
            self.save_products(updated_products)
            return True
        return False
    
    def get_product_by_id(self, product_id):
        """Get a product by its ID"""
        products = self.load_products()
        for product in products:
            if product.id == product_id:
                return product
        return None
    
    def get_product_by_slug(self, slug):
        products = self.load_products()
        for product in products:
            if product.slug == slug:
                return product
        return None
    
    def get_products_by_category(self, category):
        products = self.load_products()
        if category == 'all':
            return products
        return [p for p in products if p.category == category]
