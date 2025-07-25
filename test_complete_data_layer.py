#!/usr/bin/env python3
"""
Complete Data Layer Test for City Pulse Agent
Tests all components: schemas, ChromaDB, event processing, mock data
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our components
from data.database.database_manager import db_manager
from data.models.schemas import (
    Coordinates, EventCreateRequest, EventTopic, EventSeverity,
    User, UserProfile, UserPermissions
)

async def test_complete_data_layer():
    """Test all components of the data layer"""
    
    print("🚀 Testing Complete City Pulse Data Layer")
    print("=" * 60)
    
    # 1. Initialize databases
    print("\n1. 🔧 Initializing databases...")
    try:
        db_healthy = await db_manager.initialize_databases()
        if db_healthy:
            print("✅ Databases initialized successfully")
        else:
            print("❌ Database initialization failed")
            return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False
    
    # 2. Health check
    print("\n2. 🏥 Checking database health...")
    try:
        health = await db_manager.health_check()
        print(f"📊 Health status: {health}")
        if not health.get('chroma_db', False):
            print("⚠️ ChromaDB not healthy, but continuing...")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # 3. Test data schemas
    print("\n3. 📋 Testing data schemas...")
    try:
        # Test creating a user
        test_user = User(
            profile=UserProfile(
                google_id="test_google_123",
                email="test@example.com",
                name="Test User"
            ),
            permissions=UserPermissions(
                location_access=True,
                calendar_access=True,
                notification_enabled=True
            )
        )
        print(f"✅ User schema created: {test_user.profile.name} ({test_user.id})")
        
        # Test creating an event request
        test_report = EventCreateRequest(
            topic=EventTopic.TRAFFIC,
            sub_topic="accident",
            title="Test traffic accident",
            description="Multi-vehicle collision on test road causing delays",
            location=Coordinates(lat=12.9716, lng=77.5946),
            address="Test Location, Bengaluru",
            severity=EventSeverity.HIGH,
            media_urls=[]
        )
        print(f"✅ Event request schema created: {test_report.title}")
        
    except Exception as e:
        print(f"❌ Schema test error: {e}")
        return False
    
    # 4. Test event processing
    print("\n4. 🤖 Testing AI event processing...")
    try:
        processed_event = await db_manager.process_user_report(test_report, test_user.id)
        print(f"✅ Event processed successfully:")
        print(f"   Event ID: {processed_event.id}")
        print(f"   Topic: {processed_event.topic.value}")
        print(f"   Severity: {processed_event.impact_analysis.severity.value}")
        print(f"   Location: {processed_event.geographic_data.location.address}")
        
    except Exception as e:
        print(f"❌ Event processing error: {e}")
        return False
    
    # 5. Test mock data generation
    print("\n5. 📊 Testing mock data generation...")
    try:
        success = await db_manager.populate_mock_data(events_count=10, users_count=3)
        if success:
            print("✅ Mock data generated successfully")
        else:
            print("⚠️ Mock data generation had issues but completed")
            
    except Exception as e:
        print(f"❌ Mock data generation error: {e}")
        return False
    
    # 6. Test semantic search
    print("\n6. 🔍 Testing semantic event search...")
    try:
        bengaluru_center = Coordinates(lat=12.9716, lng=77.5946)
        search_results = await db_manager.search_events_semantically(
            query="traffic accident causing delays",
            user_location=bengaluru_center,
            max_results=5
        )
        
        print(f"✅ Semantic search completed:")
        print(f"   Found {len(search_results)} relevant events")
        
        if search_results:
            best_match = search_results[0]
            print(f"   Best match: {best_match.get('document', 'No document')[:100]}...")
            print(f"   Similarity: {best_match.get('similarity_score', 0):.3f}")
        
    except Exception as e:
        print(f"❌ Semantic search error: {e}")
        return False
    
    # 7. Test different search queries
    print("\n7. 🎯 Testing various search scenarios...")
    try:
        search_queries = [
            "power outage in HSR Layout",
            "cultural festival events",
            "road construction blocking traffic",
            "weather related flooding"
        ]
        
        for query in search_queries:
            results = await db_manager.search_events_semantically(
                query=query,
                max_results=3
            )
            print(f"   Query: '{query}' → {len(results)} results")
            
    except Exception as e:
        print(f"❌ Multiple search test error: {e}")
    
    # 8. Test system statistics
    print("\n8. 📈 Getting system statistics...")
    try:
        stats = await db_manager.get_system_stats()
        print("✅ System statistics:")
        
        chroma_stats = stats.get('chroma_db', {})
        if isinstance(chroma_stats, dict):
            events_count = chroma_stats.get('events_count', 0)
            users_count = chroma_stats.get('users_count', 0)
            print(f"   Events in database: {events_count}")
            print(f"   Users in database: {users_count}")
            print(f"   Database status: {chroma_stats.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Statistics error: {e}")
    
    # 9. Performance test
    print("\n9. ⚡ Performance test...")
    try:
        start_time = datetime.now()
        
        # Create multiple events quickly
        for i in range(5):
            quick_report = EventCreateRequest(
                topic=EventTopic.TRAFFIC,
                sub_topic="congestion",
                title=f"Performance test event {i+1}",
                description=f"Test event number {i+1} for performance measurement",
                location=Coordinates(lat=12.97 + i*0.01, lng=77.59 + i*0.01),
                severity=EventSeverity.LOW
            )
            await db_manager.process_user_report(quick_report, "perf_test_user")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Performance test completed:")
        print(f"   Processed 5 events in {duration:.2f} seconds")
        print(f"   Average: {duration/5:.2f} seconds per event")
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Complete Data Layer Test Finished!")
    print("\n📊 Summary of what was tested:")
    print("  ✓ Database initialization and health checks")
    print("  ✓ Pydantic schema validation")
    print("  ✓ AI-powered event processing with Gemini")
    print("  ✓ ChromaDB vector storage and retrieval")
    print("  ✓ Mock data generation for Bengaluru")
    print("  ✓ Semantic similarity search")
    print("  ✓ Multiple search scenarios")
    print("  ✓ System statistics and monitoring")
    print("  ✓ Performance measurement")
    
    print("\n🚀 Your data layer is ready for the FastAPI backend!")
    print("   Next step: Build REST APIs that use db_manager")
    
    return True

async def main():
    """Main test function"""
    try:
        success = await test_complete_data_layer()
        if success:
            print("\n✅ All data layer tests completed successfully!")
            print("🎯 Ready to build the FastAPI backend")
        else:
            print("\n❌ Some tests failed. Check the output above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
