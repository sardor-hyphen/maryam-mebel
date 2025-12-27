#!/usr/bin/env python3
"""
Script to generate favicon.ico from logo.png
"""

import os
from PIL import Image

def generate_favicon():
    """Generate favicon.ico from logo.png"""
    try:
        # Define paths
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
        favicon_path = os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')
        
        # Check if logo.png exists
        if not os.path.exists(logo_path):
            print(f"Error: logo.png not found at {logo_path}")
            return False
        
        # Open the logo image
        img = Image.open(logo_path)
        
        # Convert to RGBA if necessary
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize to favicon sizes (16x16, 32x32, 48x48)
        sizes = [(16, 16), (32, 32), (48, 48)]
        icons = []
        
        for size in sizes:
            resized_img = img.resize(size, Image.Resampling.LANCZOS)
            icons.append(resized_img)
        
        # Save as favicon.ico with multiple sizes
        icons[0].save(
            favicon_path,
            format='ICO',
            sizes=[(16, 16), (32, 32), (48, 48)],
            append_images=icons[1:]
        )
        
        print(f"✅ Favicon generated successfully at {favicon_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating favicon: {e}")
        return False

if __name__ == "__main__":
    generate_favicon()