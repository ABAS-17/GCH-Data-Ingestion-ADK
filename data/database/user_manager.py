# data/database/user_manager.py
"""
Fixed User Manager with correct method signatures
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models.schemas import (
    User, UserProfile, UserPermissions, UserLocations, GoogleIntegrations,
    MovementPattern, TravelPreferences, LocationPreferences, GooglePlace,
    LocationData, Coordinates, EventTopic, UserContext, UserPreferences,
    UserBehaviorPatterns, InteractionSummary
)

logger = logging.getLogger(__name__)


class UserManager:
    """
    Simplified user data management with correct method signatures
    """
    
    def __init__(self):
        self._initialized = False
        
        # Firestore collections
        self.USERS_COLLECTION = "users"
        self.USER_PREFERENCES_COLLECTION = "user_preferences"
        self.USER_INTERACTIONS_COLLECTION = "user_interactions"
        self.USER_LOCATIONS_COLLECTION = "user_locations"
    
    async def initialize(self) -> bool:
        """Initialize user manager"""
        try:
            self._initialized = True
            logger.info("✅ User Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize User Manager: {e}")
            return False
    
    # =========================================================================
    # USER PROFILE MANAGEMENT
    # =========================================================================
    
    async def create_user(self, google_id: str, email: str, name: str, 
                         age: Optional[int] = None, avatar_url: Optional[str] = None,
                         initial_location: Optional[Coordinates] = None) -> User:
        """Create a new user with complete profile"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create user profile
            profile = UserProfile(
                google_id=google_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            # Create user permissions (default safe settings)
            permissions = UserPermissions(
                location_access=initial_location is not None,
                calendar_access=False,
                notification_enabled=True
            )
            
            # Create user locations if provided
            locations = UserLocations()
            if initial_location:
                current_location = LocationData(
                    lat=initial_location.lat,
                    lng=initial_location.lng,
                    timestamp=datetime.utcnow(),
                    address=None
                )
                locations.current = current_location
            
            # Create complete user object
            user = User(
                profile=profile,
                permissions=permissions,
                locations=locations
            )
            
            # Store in Firestore (mock)
            success = await self._store_user_in_firestore(user)
            if not success:
                raise Exception("Failed to store user in Firestore")
            
            # Initialize user preferences and context
            await self._initialize_user_context(user.id)
            
            logger.info(f"✅ Created new user: {user.profile.name} ({user.id})")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID with complete profile"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Mock implementation - create a sample user
            logger.info(f"Mock: Getting user {user_id}")
            
            # Return a mock user for testing
            profile = UserProfile(
                google_id=f"google_{user_id}",
                email=f"user_{user_id}@example.com",
                name=f"User {user_id}",
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            user = User(
                id=user_id,
                profile=profile,
                permissions=UserPermissions(),
                locations=UserLocations()
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            logger.info(f"Mock: Getting user by email {email}")
            return None  # Mock - return None to allow new user creation
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile information"""
        try:
            logger.info(f"Mock: Updating profile for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    # =========================================================================
    # USER LOCATION MANAGEMENT
    # =========================================================================
    
    async def update_user_location(self, user_id: str, location: Coordinates, 
                                  address: Optional[str] = None) -> bool:
        """Update user's current location"""
        try:
            logger.info(f"Mock: Updating location for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating location for user {user_id}: {e}")
            return False
    
    async def set_home_location(self, user_id: str, location: Coordinates, 
                               address: str, place_id: Optional[str] = None) -> bool:
        """Set user's home location"""
        try:
            logger.info(f"Mock: Setting home location for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting home location for user {user_id}: {e}")
            return False
    
    async def set_work_location(self, user_id: str, location: Coordinates,
                               address: str, place_id: Optional[str] = None) -> bool:
        """Set user's work location"""
        try:
            logger.info(f"Mock: Setting work location for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting work location for user {user_id}: {e}")
            return False
    
    # =========================================================================
    # USER PREFERENCES MANAGEMENT
    # =========================================================================
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user's preferences and behavioral patterns"""
        try:
            logger.info(f"Mock: Getting preferences for user {user_id}")
            return UserPreferences()
            
        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferred_topics: Optional[List[EventTopic]] = None,
                                    commute_routes: Optional[List[str]] = None,
                                    notification_times: Optional[List[str]] = None,
                                    travel_mode: Optional[str] = None) -> bool:
        """Update user preferences"""
        try:
            logger.info(f"Mock: Updating preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences for {user_id}: {e}")
            return False
    
    async def track_user_interaction(self, user_id: str, topic: EventTopic,
                                   query: str, location: Optional[Coordinates] = None) -> bool:
        """Track user interaction for learning"""
        try:
            logger.info(f"Tracked interaction: {user_id} asked about {topic.value}: {query}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")
            return False
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user insights and analytics"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return {"error": "User not found"}
            
            return {
                "user_summary": {
                    "name": user.profile.name,
                    "email": user.profile.email,
                    "member_since": user.profile.created_at.isoformat() if user.profile.created_at else None
                },
                "location_summary": {
                    "has_current_location": user.locations.current is not None,
                    "has_home_set": user.locations.home is not None,
                    "has_work_set": user.locations.work is not None
                },
                "preferences": {
                    "preferred_topics": [],
                    "location_radius": user.locations.preferences.radius_km if user.locations.preferences else 5
                },
                "behavior_patterns": {
                    "total_interactions": 0,
                    "most_asked_topics": [],
                    "frequent_locations": []
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting insights for {user_id}: {e}")
            return {"error": str(e)}
    
    async def get_users_by_location(self, center: Coordinates, radius_km: float = 5,
                                  max_users: int = 50) -> List[Dict[str, Any]]:
        """Get users within a geographic radius"""
        try:
            # Mock implementation - return sample nearby users
            return [
                {
                    "user_id": "sample_user_1",
                    "name": "Sample User 1",
                    "distance_km": 1.2,
                    "location": {"lat": center.lat + 0.01, "lng": center.lng + 0.01}
                },
                {
                    "user_id": "sample_user_2", 
                    "name": "Sample User 2",
                    "distance_km": 2.5,
                    "location": {"lat": center.lat - 0.02, "lng": center.lng + 0.01}
                }
            ]
            
        except Exception as e:
            logger.error(f"Error getting nearby users: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for user management system"""
        try:
            return {
                "overall_healthy": True,
                "user_manager_initialized": self._initialized,
                "total_users": 0,  # Mock count
                "active_users_30d": 0,  # Mock count
                "firestore_connected": True,  # Mock status
                "issues": []
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall_healthy": False,
                "error": str(e),
                "issues": [str(e)]
            }
    
    # =========================================================================
    # FIRESTORE HELPER METHODS (MOCK IMPLEMENTATIONS)
    # =========================================================================
    
    async def _store_user_in_firestore(self, user: User) -> bool:
        """Store user in Firestore (mock implementation)"""
        try:
            logger.info(f"Mock: Storing user {user.id} in Firestore")
            return True
        except Exception as e:
            logger.error(f"Error storing user: {e}")
            return False
    
    async def _initialize_user_context(self, user_id: str) -> None:
        """Initialize user context in Firestore"""
        logger.info(f"Mock: Initialized context for user {user_id}")


# Create singleton instance
user_data_manager = UserManager()
