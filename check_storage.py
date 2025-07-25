#!/usr/bin/env python3
"""
Check Firebase storage to see where incidents are stored
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime

# Set up environment
os.environ['GEMINI_API_KEY'] = 'AIzaSyBCAAnb93XEN8jdnLYBUyUvU_ub6BX4U3E'
os.environ['FIREBASE_PROJECT_ID'] = 'hack-4ad75'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config

async def check_firebase_storage():
    """Check what's stored in Firebase collections"""
    print("🔍 Checking Firebase Firestore Storage")
    print("=" * 50)
    
    try:
        from data.database.simple_firestore_client import SimpleFirestoreClient
        
        # Initialize Firestore client
        firestore_client = SimpleFirestoreClient()
        await firestore_client.initialize()
        
        # Check each collection
        collections_to_check = [
            config.EVENTS_COLLECTION,      # global_events
            config.USERS_COLLECTION,       # users  
            config.CONVERSATIONS_COLLECTION, # user_conversations
            config.DASHBOARDS_COLLECTION,   # user_dashboards
            config.REPORTS_COLLECTION       # user_reports
        ]
        
        for collection_name in collections_to_check:
            print(f"\n📁 Collection: {collection_name}")
            try:
                # Get all documents in collection
                docs = await firestore_client.get_all_documents(collection_name)
                print(f"   Document count: {len(docs)}")
                
                if docs:
                    print(f"   Sample document IDs: {list(docs.keys())[:5]}")
                    
                    # Show first document structure
                    first_doc = list(docs.values())[0]
                    print(f"   Sample fields: {list(first_doc.keys())}")
                    
                    # If it's events, show more details
                    if collection_name == config.EVENTS_COLLECTION:
                        print(f"   📋 Event Details:")
                        for doc_id, doc_data in list(docs.items())[:3]:
                            title = doc_data.get('title', 'No title')
                            topic = doc_data.get('topic', 'Unknown')
                            created = doc_data.get('created_at', 'Unknown')
                            print(f"      • {doc_id}: {title} ({topic}) - {created}")
                else:
                    print(f"   ⚠️ Collection is empty")
                    
            except Exception as e:
                print(f"   ❌ Error accessing {collection_name}: {e}")
        
        print(f"\n" + "=" * 50)
        print("🎯 SUMMARY:")
        print("Current storage situation:")
        print("• 📊 ChromaDB: Events stored for vector search")
        print("• 🔥 Firebase: Check results above")
        print("• 💾 Primary storage: Appears to be ChromaDB only")
        
    except Exception as e:
        print(f"❌ Error checking Firebase: {e}")
        return False

async def check_chromadb_storage():
    """Check what's in ChromaDB"""
    print("\n🗄️ Checking ChromaDB Storage")
    print("=" * 30)
    
    try:
        from data.database.chroma_client import chroma_client
        
        # Get collection stats
        stats = await chroma_client.get_collection_stats()
        print(f"ChromaDB Stats: {stats}")
        
        # Check if we can find our recent events
        print(f"Events in ChromaDB: {stats.get('events_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")
        return False

async def main():
    """Run storage check"""
    print("🚀 CITY PULSE - STORAGE INVESTIGATION")
    print("=" * 60)
    
    # Check Firebase storage
    await check_firebase_storage()
    
    # Check ChromaDB storage  
    await check_chromadb_storage()
    
    print(f"\n💡 CONCLUSION:")
    print("Based on the code review, events are currently:")
    print("1. ✅ Stored in ChromaDB for semantic search (working)")
    print("2. ❓ May or may not be in Firebase Firestore")
    print("3. 🔧 Need to verify if dual storage is working")
    
    print(f"\nTo find your incidents, check:")
    print(f"• ChromaDB collection: {config.CHROMA_COLLECTION_EVENTS}")
    print(f"• Firebase collection: {config.EVENTS_COLLECTION}")

if __name__ == "__main__":
    asyncio.run(main())
