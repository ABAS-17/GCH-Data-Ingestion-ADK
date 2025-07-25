#!/usr/bin/env python3
"""
Simple test to verify your API keys work
Run this first before setting up the full data layer
"""

import os
import sys
import importlib

# Set your credentials directly
os.environ['GEMINI_API_KEY'] = 'AIzaSyBCAAnb93XEN8jdnLYBUyUvU_ub6BX4U3E'
os.environ['FIREBASE_PROJECT_ID'] = 'hack-4ad75'

def test_gemini_api():
   """Test if Gemini API key works"""
   try:
       import google.generativeai as genai
       
       # Configure Gemini
       genai.configure(api_key=os.environ['GEMINI_API_KEY'])
       
       # Try to generate content
       model = genai.GenerativeModel('gemini-1.5-flash')
       response = model.generate_content("Hello, classify this as a greeting.")
       
       print("✅ Gemini API working!")
       print(f"   Response: {response.text[:100]}...")
       return True
       
   except Exception as e:
       print(f"❌ Gemini API failed: {e}")
       return False

def test_chroma_db():
   """Test if ChromaDB works locally"""
   try:
       import chromadb
       
       # Create a test client
       client = chromadb.PersistentClient(path="./test_chroma")
       collection = client.get_or_create_collection("test")
       
       # Add a test document
       collection.add(
           documents=["Traffic jam on ORR"],
           ids=["test1"]
       )
       
       # Query it
       results = collection.query(
           query_texts=["traffic congestion"],
           n_results=1
       )
       
       print("✅ ChromaDB working!")
       print(f"   Found: {results['documents'][0][0]}")
       return True
       
   except Exception as e:
       print(f"❌ ChromaDB failed: {e}")
       return False

def main():
   print("🧪 Quick API Test")
   print("=" * 30)
   
   # Check Python packages
   required_packages = ['google.generativeai', 'chromadb']
   missing_packages = []
   
   for package in required_packages:
       try:
           importlib.import_module(package)
           print(f"✅ {package} installed")
       except ImportError:
           missing_packages.append(package)
           print(f"❌ {package} missing")
   
   if missing_packages:
       print(f"\n📦 Install missing packages:")
       print(f"pip install {' '.join(missing_packages)}")
       return
   
   print("\n🔑 Testing API Keys...")
   
   # Test APIs
   gemini_works = test_gemini_api()
   chroma_works = test_chroma_db()
   
   print("\n" + "=" * 30)
   if gemini_works and chroma_works:
       print("🎉 All tests passed!")
       print("Your setup is ready for the full data layer.")
   else:
       print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
   main()