#!/usr/bin/env python3
"""
Setup script for Enhanced Subcategory Management System
Installs dependencies, configures Firestore, and initializes the system
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def install_dependencies():
    """Install required Python packages"""
    logger.info("📦 Installing required dependencies...")
    
    required_packages = [
        "google-cloud-firestore>=2.11.0",
        "google-cloud-storage>=2.8.0",
        "google-api-core>=2.11.0",
        "firebase-admin>=6.1.0"
    ]
    
    for package in required_packages:
        try:
            logger.info(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install {package}: {e}")
            return False
    
    return True


def update_requirements_txt():
    """Update requirements.txt with new dependencies"""
    logger.info("📝 Updating requirements.txt...")
    
    new_requirements = [
        "google-cloud-firestore>=2.11.0",
        "google-cloud-storage>=2.8.0", 
        "google-api-core>=2.11.0",
        "firebase-admin>=6.1.0"
    ]
    
    requirements_file = Path("requirements.txt")
    
    try:
        # Read existing requirements
        existing_requirements = []
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                existing_requirements = f.read().splitlines()
        
        # Add new requirements if not already present
        updated_requirements = existing_requirements.copy()
        for req in new_requirements:
            package_name = req.split('>=')[0].split('==')[0]
            if not any(package_name in line for line in existing_requirements):
                updated_requirements.append(req)
                logger.info(f"✅ Added {req} to requirements.txt")
        
        # Write updated requirements
        with open(requirements_file, 'w') as f:
            f.write('\n'.join(updated_requirements))
            f.write('\n')
        
        logger.info("✅ requirements.txt updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update requirements.txt: {e}")
        return False


def check_env_configuration():
    """Check and guide Firestore environment configuration"""
    logger.info("⚙️ Checking environment configuration...")
    
    required_env_vars = [
        "FIREBASE_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS", 
        "GEMINI_API_KEY"
    ]
    
    missing_vars = []
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        logger.warning("⚠️ .env file not found")
        return False
    
    # Read .env file
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    for var in required_env_vars:
        if f"{var}=" not in env_content or f"{var}=" in env_content and not env_content.split(f"{var}=")[1].split('\n')[0].strip():
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("\n" + "="*60)
        print("🔧 CONFIGURATION REQUIRED")
        print("="*60)
        print("Please add the following to your .env file:")
        print()
        
        for var in missing_vars:
            if var == "FIREBASE_PROJECT_ID":
                print(f"{var}=your-firebase-project-id")
                print("   # Get this from Firebase Console > Project Settings")
            elif var == "GOOGLE_APPLICATION_CREDENTIALS":
                print(f"{var}=/path/to/your/firebase-service-account-key.json")
                print("   # Download from Firebase Console > Project Settings > Service Accounts")
            elif var == "GEMINI_API_KEY":
                print(f"{var}=your-gemini-api-key")
                print("   # Get this from Google AI Studio")
            print()
        
        print("Then run this setup script again.")
        print("="*60)
        return False
    
    logger.info("✅ Environment configuration looks good")
    return True


def test_firestore_connection():
    """Test Firestore connection"""
    logger.info("🔌 Testing Firestore connection...")
    
    try:
        # Import and test the Firestore client
        from data.database.firestore_client import firestore_subcategory_client
        import asyncio
        
        async def test_connection():
            success = await firestore_subcategory_client.initialize()
            return success
        
        success = asyncio.run(test_connection())
        
        if success:
            logger.info("✅ Firestore connection successful")
            return True
        else:
            logger.error("❌ Firestore connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Firestore connection test failed: {e}")
        return False


def initialize_subcategory_system():
    """Initialize the subcategory system with predefined data"""
    logger.info("🚀 Initializing subcategory system...")
    
    try:
        from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
        import asyncio
        
        async def initialize_system():
            # Initialize the enhanced processor
            init_success = await enhanced_subcategory_processor.initialize()
            if not init_success:
                return False
            
            # Check if we need to initialize predefined subcategories
            from data.models.schemas import EventTopic
            from data.database.firestore_client import firestore_subcategory_client
            
            traffic_subcategories = await firestore_subcategory_client.get_subcategories_by_topic(EventTopic.TRAFFIC)
            
            if len(traffic_subcategories) == 0:
                logger.info("🔧 Initializing predefined subcategories...")
                # Initialize predefined subcategories
                init_subcategories = await enhanced_subcategory_processor.classifier.initialize_predefined_subcategories()
                
                if init_subcategories:
                    logger.info("✅ Predefined subcategories initialized")
                else:
                    logger.warning("⚠️ Failed to initialize predefined subcategories")
            else:
                logger.info(f"✅ Found {len(traffic_subcategories)} existing subcategories for traffic topic")
            
            return True
        
        success = asyncio.run(initialize_system())
        
        if success:
            logger.info("✅ Subcategory system initialized successfully")
            return True
        else:
            logger.error("❌ Subcategory system initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ System initialization failed: {e}")
        return False


def run_system_test():
    """Run a quick system test"""
    logger.info("🧪 Running system test...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "test_subcategory_system.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("✅ System test passed")
            return True
        else:
            logger.warning(f"⚠️ System test failed with return code {result.returncode}")
            logger.info("Output:", result.stdout)
            logger.error("Errors:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ System test timed out (may still be working)")
        return True
    except Exception as e:
        logger.error(f"❌ System test failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Enhanced Subcategory Management System Setup")
    print("=" * 60)
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return 1
    
    # Step 2: Update requirements.txt
    if not update_requirements_txt():
        print("⚠️ Failed to update requirements.txt (continuing anyway)")
    
    # Step 3: Check environment configuration
    if not check_env_configuration():
        print("❌ Environment configuration incomplete")
        return 1
    
    # Step 4: Test Firestore connection
    if not test_firestore_connection():
        print("❌ Firestore connection failed")
        print("\n💡 Tips:")
        print("   - Ensure FIREBASE_PROJECT_ID is correct")
        print("   - Verify service account key file exists and is readable")
        print("   - Check network connectivity")
        return 1
    
    # Step 5: Initialize subcategory system
    if not initialize_subcategory_system():
        print("❌ System initialization failed")
        return 1
    
    # Step 6: Run system test
    print("\n🧪 Running comprehensive system test...")
    if not run_system_test():
        print("⚠️ System test had issues (check logs for details)")
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("✅ Enhanced Subcategory Management System is ready to use")
    print()
    print("🔧 Key features enabled:")
    print("   • AI-powered subcategory classification")
    print("   • Firestore persistence with atomic operations")
    print("   • Dynamic subcategory creation")
    print("   • Comprehensive analytics and reporting")
    print("   • Enhanced event processing")
    print()
    print("🚀 You can now:")
    print("   • Start the API server: python main.py")
    print("   • Run tests: python test_subcategory_system.py")
    print("   • Use the new /subcategories/* API endpoints")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
