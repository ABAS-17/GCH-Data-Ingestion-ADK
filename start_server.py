#!/usr/bin/env python3
"""
City Pulse Agent - Server Startup Script
Quick startup with health checks and demo data
"""

import subprocess
import sys
import os
import time
import requests
import asyncio
from datetime import datetime

def install_missing_dependencies():
    """Install any missing FastAPI dependencies"""
    required_packages = [
        'fastapi==0.104.1',
        'uvicorn==0.24.0',
        'python-multipart==0.0.6',
        'aiohttp==3.9.0'  # For API testing
    ]
    
    print("📦 Checking FastAPI dependencies...")
    for package in required_packages:
        try:
            package_name = package.split('==')[0]
            __import__(package_name.replace('-', '_'))
            print(f"✅ {package_name}")
        except ImportError:
            print(f"📥 Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ {package} installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")

def check_data_layer():
    """Quick check if data layer is working"""
    print("\n🔧 Checking data layer...")
    try:
        # Add current directory to path
        sys.path.append(os.getcwd())
        
        # Test imports
        from data.database.database_manager import db_manager
        from data.processors.enhanced_event_processor import enhanced_processor
        print("✅ Data layer imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Data layer check failed: {e}")
        return False

def wait_for_server(url="http://localhost:8000", timeout=30):
    """Wait for server to start"""
    print(f"\n⏳ Waiting for server at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(2)
    
    print("❌ Server startup timeout")
    return False

async def populate_demo_data():
    """Populate with demo data after server starts"""
    try:
        print("\n🎭 Populating demo data...")
        
        # Use aiohttp for async request
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/demo/populate",
                json={"events_count": 25, "users_count": 5}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Demo data populated: {result.get('events_count')} events")
                else:
                    print(f"⚠️ Demo data population failed: {response.status}")
    except Exception as e:
        print(f"⚠️ Could not populate demo data: {e}")

def main():
    """Main startup function"""
    print("🏙️ City Pulse Agent - Server Startup")
    print("=" * 45)
    print(f"📅 Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ main.py not found. Make sure you're in the project directory.")
        sys.exit(1)
    
    # Install dependencies
    install_missing_dependencies()
    
    # Check data layer
    if not check_data_layer():
        print("\n💡 Try running: python3 test_complete_data_layer.py")
        sys.exit(1)
    
    print("\n🚀 Starting FastAPI server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Alternative docs: http://localhost:8000/redoc")
    print("\n🛑 Press Ctrl+C to stop the server")
    print("-" * 45)
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000", 
            "--reload",
            "--log-level", "info"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check if port 8000 is already in use")
        print("2. Run: python3 test_complete_data_layer.py")
        print("3. Check the logs above for specific errors")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
