#!/usr/bin/env python3
"""
Firebase Service Account Setup Guide
Helps you get and configure the Firebase service account key
"""

import os
import json
from pathlib import Path

def check_service_account_setup():
    """Check if service account is properly set up"""
    
    print("🔑 Firebase Service Account Setup Guide")
    print("=" * 50)
    
    # Check if credentials file exists
    credentials_path = "/Users/ab/city_pulse_test/.credentials/firebase-service-account.json"
    
    if os.path.exists(credentials_path):
        print("✅ Service account file found!")
        
        # Validate the JSON file
        try:
            with open(credentials_path, 'r') as f:
                service_account = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in service_account]
            
            if missing_fields:
                print(f"❌ Invalid service account file. Missing fields: {', '.join(missing_fields)}")
                return False
            
            print(f"✅ Service account valid for project: {service_account['project_id']}")
            print(f"✅ Client email: {service_account['client_email']}")
            
            # Check if project ID matches
            from dotenv import load_dotenv
            load_dotenv()
            env_project_id = os.getenv('FIREBASE_PROJECT_ID')
            
            if service_account['project_id'] == env_project_id:
                print(f"✅ Project ID matches .env file: {env_project_id}")
                return True
            else:
                print(f"❌ Project ID mismatch:")
                print(f"   Service account: {service_account['project_id']}")
                print(f"   .env file: {env_project_id}")
                return False
                
        except json.JSONDecodeError:
            print("❌ Service account file is not valid JSON")
            return False
        except Exception as e:
            print(f"❌ Error reading service account file: {e}")
            return False
    
    else:
        print("❌ Service account file not found")
        print("\n🔧 Follow these steps to get your service account key:")
        print_setup_instructions()
        return False

def print_setup_instructions():
    """Print detailed setup instructions"""
    
    print("\n📋 STEP-BY-STEP INSTRUCTIONS:")
    print("=" * 50)
    
    print("\n1️⃣ Go to Firebase Console:")
    print("   https://console.firebase.google.com/")
    
    print("\n2️⃣ Select your project:")
    print("   Click on 'hack-4ad75' (your project)")
    
    print("\n3️⃣ Open Project Settings:")
    print("   Click the ⚙️ gear icon next to 'Project Overview'")
    print("   Select 'Project settings'")
    
    print("\n4️⃣ Go to Service Accounts:")
    print("   Click the 'Service accounts' tab")
    
    print("\n5️⃣ Generate Private Key:")
    print("   Find the service account ending with '@hack-4ad75.iam.gserviceaccount.com'")
    print("   Click 'Generate new private key'")
    print("   Click 'Generate key' in the dialog")
    
    print("\n6️⃣ Download & Move the file:")
    print("   A JSON file will download to your Downloads folder")
    print("   Move it using this command:")
    print(f"   mv ~/Downloads/hack-4ad75-firebase-adminsdk-*.json /Users/ab/city_pulse_test/.credentials/firebase-service-account.json")
    
    print("\n7️⃣ Verify Setup:")
    print("   Run this script again: python check_firebase_setup.py")
    
    print("\n⚠️  SECURITY NOTE:")
    print("   - Never commit the service account key to version control")
    print("   - The .credentials/ folder is already in .gitignore")
    print("   - Keep this file secure and private")

def test_firebase_connection():
    """Test Firebase connection with service account"""
    
    print("\n🔌 Testing Firebase Connection...")
    
    try:
        # Set environment variable
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/Users/ab/city_pulse_test/.credentials/firebase-service-account.json"
        
        # Test Firestore connection
        from google.cloud import firestore
        
        db = firestore.Client()
        
        # Try a simple operation
        test_collection = db.collection('test_connection')
        test_doc = test_collection.document('test')
        test_doc.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
        
        # Read it back
        doc = test_doc.get()
        if doc.exists:
            print("✅ Firestore connection successful!")
            
            # Clean up test document
            test_doc.delete()
            print("✅ Test document cleaned up")
            
            return True
        else:
            print("❌ Could not write to Firestore")
            return False
            
    except ImportError:
        print("❌ google-cloud-firestore not installed")
        print("   Run: pip install google-cloud-firestore")
        return False
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        print("\n💡 Common issues:")
        print("   - Check if service account file exists and is valid")
        print("   - Ensure Firestore is enabled in Firebase Console")
        print("   - Verify internet connection")
        print("   - Check if service account has Firestore permissions")
        return False

def main():
    """Main function"""
    
    # Check setup
    setup_ok = check_service_account_setup()
    
    if setup_ok:
        # Test connection
        connection_ok = test_firebase_connection()
        
        if connection_ok:
            print("\n🎉 SUCCESS!")
            print("=" * 50)
            print("✅ Firebase service account is properly configured")
            print("✅ Firestore connection is working")
            print("✅ You can now run the subcategory system setup:")
            print("   python setup_subcategory_system.py")
        else:
            print("\n❌ Setup complete but connection failed")
            print("Check the error messages above and try again")
    else:
        print("\n⏳ Setup incomplete")
        print("Follow the instructions above to complete setup")

if __name__ == "__main__":
    main()
