#!/usr/bin/env python3
"""
Test script to verify image processing functionality
"""

import os
import sys
from io import BytesIO

def test_pillow_import():
    """Test if Pillow is properly installed"""
    try:
        from PIL import Image
        print("✅ Pillow (PIL) imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Pillow import failed: {e}")
        print("Run: pip install Pillow")
        return False

def test_image_operations():
    """Test basic image operations"""
    try:
        from PIL import Image
        
        # Create a test image
        test_img = Image.new('RGB', (100, 100), color='red')
        print("✅ Image creation successful")
        
        # Test format conversions
        formats = ['JPEG', 'PNG', 'WEBP']
        for fmt in formats:
            try:
                output = BytesIO()
                if fmt == 'JPEG':
                    test_img.save(output, format=fmt, quality=95)
                elif fmt == 'WEBP':
                    test_img.save(output, format=fmt, quality=95, method=6)
                else:
                    test_img.save(output, format=fmt)
                print(f"✅ {fmt} conversion successful")
            except Exception as e:
                print(f"❌ {fmt} conversion failed: {e}")
        
        # Test compression
        large_img = Image.new('RGB', (2000, 2000), color='blue')
        compressed_img = large_img.resize((1000, 1000), Image.Resampling.LANCZOS)
        output = BytesIO()
        compressed_img.save(output, format='JPEG', quality=70, optimize=True)
        print("✅ Image compression successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Image operations failed: {e}")
        return False

def test_transparency_handling():
    """Test transparency handling"""
    try:
        from PIL import Image
        
        # Create RGBA image with transparency
        rgba_img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        
        # Convert to RGB with white background
        background = Image.new('RGB', rgba_img.size, (255, 255, 255))
        background.paste(rgba_img, mask=rgba_img.split()[-1])
        
        output = BytesIO()
        background.save(output, format='JPEG', quality=95)
        print("✅ Transparency handling successful")
        return True
        
    except Exception as e:
        print(f"❌ Transparency handling failed: {e}")
        return False

def main():
    print("🔍 Testing RupaGanti Image Processing...")
    print("=" * 50)
    
    success = True
    
    # Test Pillow import
    if not test_pillow_import():
        success = False
    
    # Test image operations
    if not test_image_operations():
        success = False
    
    # Test transparency handling
    if not test_transparency_handling():
        success = False
    
    print("=" * 50)
    if success:
        print("🎉 All image processing tests passed!")
        print("Your RupaGanti bot should work correctly for image conversion and compression.")
    else:
        print("⚠️  Some tests failed. Please install missing dependencies:")
        print("pip install Pillow")
    
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()