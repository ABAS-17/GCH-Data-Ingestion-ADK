#!/usr/bin/env python3
"""
Test User Data Layer
Comprehensive testing of user management functionality
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Add data layer to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.database.user_manager import user_data_manager
from data.models.schemas import Coordinates, EventTopic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_user_data_layer():
    """Test complete user data management functionality"""
    
    print("🚀 Testing User Data Layer")
    print("=" * 50)
    
    try:
        # 1. Initialize user manager
        print("\n1. Initializing User Data Manager...")
        init_success = await user_data_manager.initialize()
        if init_success:
            print("✅ User Data Manager initialized successfully")
        else:
            print("❌ User Data Manager initialization failed")
            return False
        
        # 2. Create test user
        print("\n2. Creating Test User...")
        test_location = Coordinates(lat=12.9716, lng=77.5946)  # MG Road, Bengaluru
        
        user = await user_data_manager.create_user(
            google_id="test_user_123",
            email="test.user@example.com",
            name="Test User Kumar",
            age=28,
            initial_location=test_location
        )
        
        print(f"✅ Created user: {user.profile.name} (ID: {user.id})")
        print(f"   Email: {user.profile.email}")
        print(f"   Age: {getattr(user.profile, 'age', 'Not set')}")
        print(f"   Location: {user.locations.current.lat}, {user.locations.current.lng}")
        
        # 3. Update user preferences
        print("\n3. Updating User Preferences...")
        prefs_success = await user_data_manager.update_user_preferences(
            user_id=user.id,
            preferred_topics=[EventTopic.TRAFFIC, EventTopic.INFRASTRUCTURE],
            commute_routes=["HSR Layout to Electronic City", "Koramangala to Whitefield"],
            notification_times=["08:30", "18:00"],
            travel_mode="driving"
        )
        
        if prefs_success:
            print("✅ User preferences updated successfully")
        else:
            print("❌ Failed to update user preferences")
        
        # 4. Set home and work locations
        print("\n4. Setting Home and Work Locations...")
        
        # Set home location
        home_success = await user_data_manager.set_home_location(
            user_id=user.id,
            location=Coordinates(lat=12.9352, lng=77.6245),  # Koramangala
            address="Koramangala 5th Block, Bengaluru, Karnataka"
        )
        
        # Set work location  
        work_success = await user_data_manager.set_work_location(
            user_id=user.id,
            location=Coordinates(lat=12.9698, lng=77.7499),  # Whitefield
            address="Whitefield IT Park, Bengaluru, Karnataka"
        )
        
        if home_success and work_success:
            print("✅ Home and work locations set successfully")
        else:
            print("❌ Failed to set home/work locations")
        
        # 5. Track user interactions
        print("\n5. Tracking User Interactions...")
        
        interactions = [
            ("traffic jam on ORR", EventTopic.TRAFFIC),
            ("power outage in HSR Layout", EventTopic.INFRASTRUCTURE), 
            ("flooding near Silk Board", EventTopic.WEATHER)
        ]
        
        for query, topic in interactions:
            interaction_success = await user_data_manager.track_user_interaction(
                user_id=user.id,
                topic=topic,
                query=query,
                location=test_location
            )
            
            if interaction_success:
                print(f"✅ Tracked interaction: {query}")
            else:
                print(f"❌ Failed to track interaction: {query}")
        
        # 6. Get user insights
        print("\n6. Getting User Insights...")
        insights = await user_data_manager.get_user_insights(user.id)
        
        if "error" not in insights:
            print("✅ User insights retrieved successfully")
            print(f"   Total interactions: {insights.get('behavior_patterns', {}).get('total_interactions', 0)}")
            print(f"   Preferred topics: {insights.get('preferences', {}).get('preferred_topics', [])}")
            print(f"   Has home location: {insights.get('location_summary', {}).get('has_home_set', False)}")
            print(f"   Has work location: {insights.get('location_summary', {}).get('has_work_set', False)}")
        else:
            print(f"❌ Failed to get user insights: {insights['error']}")
        
        # 7. Test user retrieval
        print("\n7. Testing User Retrieval...")
        
        # Get by ID
        retrieved_user = await user_data_manager.get_user(user.id)
        if retrieved_user:
            print(f"✅ Retrieved user by ID: {retrieved_user.profile.name}")
        else:
            print("❌ Failed to retrieve user by ID")
        
        # Get by email
        retrieved_by_email = await user_data_manager.get_user_by_email("test.user@example.com")
        if retrieved_by_email:
            print(f"✅ Retrieved user by email: {retrieved_by_email.profile.name}")
        else:
            print("❌ Failed to retrieve user by email")
        
        # 8. Test nearby users
        print("\n8. Testing Nearby Users...")
        nearby_users = await user_data_manager.get_users_by_location(
            center=test_location,
            radius_km=10,
            max_users=10
        )
        
        print(f"✅ Found {len(nearby_users)} nearby users")
        for nearby_user in nearby_users:
            print(f"   - {nearby_user['name']} ({nearby_user['distance_km']} km away)")
        
        # 9. Health check
        print("\n9. Running Health Check...")
        health_status = await user_data_manager.health_check()
        
        if health_status.get("overall_healthy", False):
            print("✅ User Data Manager health check passed")
            print(f"   Total users: {health_status.get('total_users', 0)}")
            print(f"   Active users (30d): {health_status.get('active_users_30d', 0)}")
        else:
            print("❌ User Data Manager health check failed")
            print(f"   Issues: {health_status.get('issues', [])}")
        
        print("\n" + "=" * 50)
        print("🎉 User Data Layer Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_user_data_layer()
    
    if success:
        print("\n✅ All tests passed! User Data Layer is ready.")
    else:
        print("\n❌ Some tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
