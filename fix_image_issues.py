#!/usr/bin/env python3
"""
Fix common image processing issues in RupaGanti bot
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_and_fix_dependencies():
    """Check and fix missing dependencies"""
    required_packages = [
        "pyTelegramBotAPI==4.14.0",
        "Pillow==10.1.0", 
        "cryptography==41.0.7",
        "PyMuPDF==1.23.8",
        "python-docx==1.1.0",
        "reportlab==4.0.7"
    ]
    
    print("🔧 Checking and fixing dependencies...")
    
    for package in required_packages:
        package_name = package.split("==")[0]
        try:
            __import__(package_name.replace("-", "_").lower())
            print(f"✅ {package_name} is installed")
        except ImportError:
            print(f"❌ {package_name} missing, installing...")
            if install_package(package):
                print(f"✅ {package_name} installed successfully")
            else:
                print(f"❌ Failed to install {package_name}")

def fix_pillow_issues():
    """Fix common Pillow issues"""
    print("\n🖼️  Fixing Pillow issues...")
    
    try:
        from PIL import Image
        print("✅ Pillow imported successfully")
        
        # Test WebP support
        try:
            test_img = Image.new('RGB', (10, 10), 'red')
            from io import BytesIO
            output = BytesIO()
            test_img.save(output, format='WEBP')
            print("✅ WebP support working")
        except Exception as e:
            print(f"⚠️  WebP support issue: {e}")
            print("Consider reinstalling Pillow with WebP support")
            
    except ImportError:
        print("❌ Pillow not found, installing...")
        if install_package("Pillow==10.1.0"):
            print("✅ Pillow installed")
        else:
            print("❌ Failed to install Pillow")

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    dirs = ["files", "temp"]
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✅ Created {dir_name} directory")
        else:
            print(f"✅ {dir_name} directory exists")

def main():
    print("🚀 RupaGanti Bot - Image Processing Fix")
    print("=" * 50)
    
    # Fix dependencies
    check_and_fix_dependencies()
    
    # Fix Pillow issues
    fix_pillow_issues()
    
    # Create directories
    create_directories()
    
    print("\n" + "=" * 50)
    print("🎉 Fix completed!")
    print("\nNext steps:")
    print("1. Run: python test_image_processing.py")
    print("2. If tests pass, run: python rupaganti_bot.py")
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()