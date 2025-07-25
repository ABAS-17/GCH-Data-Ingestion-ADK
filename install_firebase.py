#!/usr/bin/env python3
"""
Install missing dependencies for media capabilities
"""

import subprocess
import sys

def install_firebase_dependencies():
    """Install Firebase and other missing dependencies"""
    
    print("📦 Installing Firebase and media dependencies...")
    
    packages = [
        'firebase-admin',
        'google-cloud-storage', 
        'pillow',  # For image processing
        'python-multipart'  # For file uploads
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    print("\n🎉 All dependencies installed!")
    return True

if __name__ == "__main__":
    success = install_firebase_dependencies()
    if success:
        print("\n🚀 Now run: python3 quick_media_test.py")
    else:
        print("\n❌ Installation failed")
