#!/usr/bin/env python3
"""
Installation and Test Script for City Pulse Agent
"""

import subprocess
import sys
import os

def install_packages():
    """Install required packages"""
    packages = [
        'python-dotenv',
        'google-generativeai', 
        'chromadb',
        'pydantic',
        'firebase-admin'
    ]
    
    print("📦 Installing required packages...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")

def test_api_keys():
    """Test if API keys work"""
    print("\n🔑 Testing API Keys...")
    
    # Set your credentials
    os.environ['GEMINI_API_KEY'] = 'AIzaSyBCAAnb93XEN8jdnLYBUyUvU_ub6BX4U3E'
    os.environ['FIREBASE_PROJECT_ID'] = 'hack-4ad75'
    
    # Test Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say hello")
        print("✅ Gemini API working!")
        print(f"   Response: {response.text[:50]}...")
    except Exception as e:
        print(f"❌ Gemini API failed: {e}")
    
    # Test ChromaDB
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./test_chroma")
        collection = client.get_or_create_collection("test")
        collection.add(documents=["test"], ids=["1"])
        print("✅ ChromaDB working!")
    except Exception as e:
        print(f"❌ ChromaDB failed: {e}")

def main():
    print("🚀 City Pulse Agent Setup")
    print("=" * 40)
    
    print("Current directory:", os.getcwd())
    print("Python executable:", sys.executable)
    
    install_packages()
    test_api_keys()
    
    print("\n" + "=" * 40)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. If tests passed, your APIs are working")
    print("2. You can now build the full data layer")
    print("3. Run this script with: python3 install_and_test.py")

if __name__ == "__main__":
    main()
