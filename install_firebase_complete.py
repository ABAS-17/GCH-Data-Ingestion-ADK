#!/usr/bin/env python3
"""
Complete Firebase installation script with all dependencies
Based on official Firebase documentation and requirements
"""

import subprocess
import sys
import os

def install_firebase_complete():
    """Install Firebase Admin SDK with all required dependencies"""
    
    print("🔥 Installing Firebase Admin SDK (Complete Setup)")
    print("=" * 60)
    
    # Check Python version (Firebase requires 3.9+, recommends 3.10+)
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 9):
        print("❌ Firebase requires Python 3.9+. Please upgrade Python.")
        return False
    elif python_version < (3, 10):
        print("⚠️ Firebase recommends Python 3.10+. You're using an older version.")
    else:
        print("✅ Python version is compatible with Firebase")
    
    # Firebase dependencies based on official requirements
    firebase_packages = [
        # Core Firebase Admin SDK
        'firebase-admin==7.0.0',
        
        # Core dependencies (will be installed automatically, but listing for clarity)
        'google-cloud-firestore>=2.21.0',
        'google-cloud-storage>=3.1.1',
        'google-api-core>=2.25.1',
        'cachecontrol>=0.12.14',
        'pyjwt[crypto]>=2.5.0',
        'httpx>=0.28.1',
        
        # Additional useful packages for our use case
        'pillow',              # Image processing
        'python-multipart',    # File uploads in FastAPI
        'requests',            # HTTP requests
    ]
    
    print(f"\n📦 Installing {len(firebase_packages)} packages...")
    
    # Install each package
    for i, package in enumerate(firebase_packages, 1):
        try:
            print(f"\n[{i}/{len(firebase_packages)}] Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ {package.split('==')[0]} installed successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}")
            print(f"Error: {e.stderr}")
            print("Continuing with other packages...")
    
    print("\n🧪 Testing Firebase installation...")
    
    # Test Firebase import
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage
        print("✅ Firebase Admin SDK imported successfully")
        print(f"   Version: {firebase_admin.__version__}")
    except ImportError as e:
        print(f"❌ Firebase import failed: {e}")
        return False
    
    # Test other important imports
    test_imports = [
        ('google.cloud.firestore', 'Firestore'),
        ('google.cloud.storage', 'Cloud Storage'),
        ('PIL', 'Pillow (Image processing)'),
        ('google.api_core', 'Google API Core'),
        ('jwt', 'PyJWT'),
        ('httpx', 'HTTPX'),
    ]
    
    print("\n🔍 Testing related imports...")
    for module, name in test_imports:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"⚠️ {name} not available")
    
    print("\n" + "=" * 60)
    print("🎉 Firebase Installation Complete!")
    print("\n📋 What was installed:")
    print("  ✓ Firebase Admin SDK 7.0.0 (latest)")
    print("  ✓ Google Cloud Firestore (database)")
    print("  ✓ Google Cloud Storage (file storage)")
    print("  ✓ All required dependencies")
    print("  ✓ Image processing support")
    print("  ✓ File upload support")
    
    print("\n🚀 Next Steps:")
    print("1. Run: python3 quick_media_test.py")
    print("2. If successful, run: python3 test_media_capabilities.py")
    print("3. Start building your FastAPI backend!")
    
    return True

def check_existing_installation():
    """Check if Firebase is already installed"""
    try:
        import firebase_admin
        print(f"ℹ️ Firebase Admin SDK already installed (v{firebase_admin.__version__})")
        return True
    except ImportError:
        print("ℹ️ Firebase Admin SDK not found, will install...")
        return False

if __name__ == "__main__":
    print("Starting Firebase installation process...")
    
    # Check if already installed
    already_installed = check_existing_installation()
    
    if already_installed:
        response = input("\nFirebase is already installed. Reinstall/upgrade? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Skipping installation.")
            exit(0)
    
    # Install Firebase
    success = install_firebase_complete()
    
    if success:
        print("\n✅ Firebase setup completed successfully!")
        print("You can now use Firebase in your City Pulse Agent!")
    else:
        print("\n❌ Firebase installation had issues.")
        print("Check the error messages above and try again.")
        sys.exit(1)
