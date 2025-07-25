# data/api/user_endpoints.py
"""
API endpoints for user management
Provides REST API for user CRUD, preferences, and analytics
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pydantic import BaseModel, Field

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models.schemas import (
    User, EventTopic, Coordinates, TravelPreferences
)
from data.database.user_manager import user_data_manager

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Create router for user endpoints
router = APIRouter(prefix="/users", tags=["Users"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateUserRequest(BaseModel):
    google_id: str = Field(..., description="Google OAuth ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User's full name")
    age: Optional[int] = Field(None, ge=13, le=120, description="User's age")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    initial_location: Optional[Coordinates] = Field(None, description="Initial user location")

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, description="Updated name")
    age: Optional[int] = Field(None, ge=13, le=120, description="Updated age")
    avatar_url: Optional[str] = Field(None, description="Updated avatar URL")

class UpdateLocationRequest(BaseModel):
    location: Coordinates = Field(..., description="New location coordinates")
    address: Optional[str] = Field(None, description="Human-readable address")

class SetHomeWorkRequest(BaseModel):
    location: Coordinates = Field(..., description="Location coordinates")
    address: str = Field(..., description="Address")
    place_id: Optional[str] = Field(None, description="Google Place ID")

class UpdatePreferencesRequest(BaseModel):
    preferred_topics: Optional[List[EventTopic]] = Field(None, description="Topics of interest")
    commute_routes: Optional[List[str]] = Field(None, description="Regular commute routes")
    notification_times: Optional[List[str]] = Field(None, description="Preferred notification times")
    travel_mode: Optional[str] = Field(None, description="Preferred travel mode")

class UserResponse(BaseModel):
    success: bool
    user: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class UserListResponse(BaseModel):
    success: bool
    users: List[Dict[str, Any]]
    total_count: int
    message: Optional[str] = None

# ============================================================================
# USER CRUD ENDPOINTS
# ============================================================================

@router.post("/", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    background_tasks: BackgroundTasks
):
    """Create a new user profile"""
    try:
        # Check if user already exists
        existing_user = await user_data_manager.get_user_by_email(request.email)
        if existing_user:
            return UserResponse(
                success=False,
                message=f"User with email {request.email} already exists"
            )
        
        # Create new user
        user = await user_data_manager.create_user(
            google_id=request.google_id,
            email=request.email,
            name=request.name,
            age=request.age,
            avatar_url=request.avatar_url,
            initial_location=request.initial_location
        )
        
        return UserResponse(
            success=True,
            user=user.dict(),
            message="User created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(..., description="User ID")
):
    """Get user profile by ID"""
    try:
        user = await user_data_manager.get_user(user_id)
        
        if not user:
            return UserResponse(
                success=False,
                message="User not found"
            )
        
        return UserResponse(
            success=True,
            user=user.dict(),
            message="User retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.get("/email/{email}")
async def get_user_by_email(
    email: str = Path(..., description="User email address")
):
    """Get user profile by email"""
    try:
        user = await user_data_manager.get_user_by_email(email)
        
        if not user:
            return UserResponse(
                success=False,
                message="User not found"
            )
        
        return UserResponse(
            success=True,
            user=user.dict(),
            message="User retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.put("/{user_id}/profile", response_model=UserResponse)
async def update_user_profile(
    request: UpdateProfileRequest,
    user_id: str = Path(..., description="User ID")
):
    """Update user profile information"""
    try:
        updates = {}
        if request.name:
            updates['name'] = request.name
        if request.age:
            updates['age'] = request.age
        if request.avatar_url:
            updates['avatar_url'] = request.avatar_url
        
        success = await user_data_manager.update_user_profile(user_id, updates)
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to update user profile"
            )
        
        # Get updated user
        user = await user_data_manager.get_user(user_id)
        
        return UserResponse(
            success=True,
            user=user.dict() if user else None,
            message="Profile updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error updating user profile {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

# ============================================================================
# LOCATION MANAGEMENT ENDPOINTS
# ============================================================================

@router.put("/{user_id}/location", response_model=UserResponse)
async def update_user_location(
    request: UpdateLocationRequest,
    user_id: str = Path(..., description="User ID")
):
    """Update user's current location"""
    try:
        success = await user_data_manager.update_user_location(
            user_id=user_id,
            location=request.location,
            address=request.address
        )
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to update user location"
            )
        
        return UserResponse(
            success=True,
            message="Location updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error updating location for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")

@router.put("/{user_id}/home", response_model=UserResponse)
async def set_home_location(
    request: SetHomeWorkRequest,
    user_id: str = Path(..., description="User ID")
):
    """Set user's home location"""
    try:
        success = await user_data_manager.set_home_location(
            user_id=user_id,
            location=request.location,
            address=request.address,
            place_id=request.place_id
        )
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to set home location"
            )
        
        return UserResponse(
            success=True,
            message="Home location set successfully"
        )
        
    except Exception as e:
        logger.error(f"Error setting home location for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set home location: {str(e)}")

@router.put("/{user_id}/work", response_model=UserResponse)
async def set_work_location(
    request: SetHomeWorkRequest,
    user_id: str = Path(..., description="User ID")
):
    """Set user's work location"""
    try:
        success = await user_data_manager.set_work_location(
            user_id=user_id,
            location=request.location,
            address=request.address,
            place_id=request.place_id
        )
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to set work location"
            )
        
        return UserResponse(
            success=True,
            message="Work location set successfully"
        )
        
    except Exception as e:
        logger.error(f"Error setting work location for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set work location: {str(e)}")

# ============================================================================
# PREFERENCES MANAGEMENT ENDPOINTS
# ============================================================================

@router.put("/{user_id}/preferences", response_model=UserResponse)
async def update_user_preferences(
    request: UpdatePreferencesRequest,
    user_id: str = Path(..., description="User ID")
):
    """Update user preferences and interests"""
    try:
        success = await user_data_manager.update_user_preferences(
            user_id=user_id,
            preferred_topics=request.preferred_topics,
            commute_routes=request.commute_routes,
            notification_times=request.notification_times,
            travel_mode=request.travel_mode
        )
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to update user preferences"
            )
        
        return UserResponse(
            success=True,
            message="Preferences updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

@router.post("/{user_id}/interactions", response_model=UserResponse)
async def track_user_interaction(
    user_id: str = Path(..., description="User ID"),
    topic: EventTopic = Query(..., description="Interaction topic"),
    query: str = Query(..., description="User query"),
    lat: Optional[float] = Query(None, description="User latitude"),
    lng: Optional[float] = Query(None, description="User longitude")
):
    """Track user interaction for behavioral learning"""
    try:
        location = None
        if lat and lng:
            location = Coordinates(lat=lat, lng=lng)
        
        success = await user_data_manager.track_user_interaction(
            user_id=user_id,
            topic=topic,
            query=query,
            location=location
        )
        
        if not success:
            return UserResponse(
                success=False,
                message="Failed to track user interaction"
            )
        
        return UserResponse(
            success=True,
            message="Interaction tracked successfully"
        )
        
    except Exception as e:
        logger.error(f"Error tracking interaction for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track interaction: {str(e)}")

# ============================================================================
# ANALYTICS AND INSIGHTS ENDPOINTS
# ============================================================================

@router.get("/{user_id}/insights")
async def get_user_insights(
    user_id: str = Path(..., description="User ID")
):
    """Get comprehensive user insights and analytics"""
    try:
        insights = await user_data_manager.get_user_insights(user_id)
        
        if "error" in insights:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": insights["error"]
                }
            )
        
        return {
            "success": True,
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting insights for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")

@router.get("/nearby")
async def get_nearby_users(
    lat: float = Query(..., description="Center latitude"),
    lng: float = Query(..., description="Center longitude"), 
    radius_km: float = Query(5, ge=1, le=50, description="Search radius in km"),
    max_users: int = Query(50, ge=1, le=200, description="Maximum users to return")
):
    """Get users within a geographic radius"""
    try:
        center = Coordinates(lat=lat, lng=lng)
        
        nearby_users = await user_data_manager.get_users_by_location(
            center=center,
            radius_km=radius_km,
            max_users=max_users
        )
        
        return {
            "success": True,
            "center_location": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "total_users": len(nearby_users),
            "users": nearby_users
        }
        
    except Exception as e:
        logger.error(f"Error getting nearby users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nearby users: {str(e)}")

# ============================================================================
# ADMIN AND SYSTEM ENDPOINTS
# ============================================================================

@router.get("/admin/stats")
async def get_user_system_stats():
    """Get system-wide user statistics (admin only)"""
    try:
        health_status = await user_data_manager.health_check()
        
        stats = {
            "system_health": health_status,
            "user_metrics": {
                "total_users": health_status.get("total_users", 0),
                "active_users_30d": health_status.get("active_users_30d", 0),
                "users_with_location": 0,
                "users_with_preferences": 0,
                "avg_interactions_per_user": 0
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting user system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/health")
async def user_system_health_check():
    """Health check for user management system"""
    try:
        health_status = await user_data_manager.health_check()
        
        status_code = 200 if health_status.get("overall_healthy", False) else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": health_status.get("overall_healthy", False),
                "health_status": health_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"User system health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ============================================================================
# DEMO AND TESTING ENDPOINTS
# ============================================================================

@router.post("/demo/create-sample-users")
async def create_sample_users(
    count: int = Query(5, ge=1, le=20, description="Number of sample users to create")
):
    """Create sample users for testing and demo purposes"""
    try:
        sample_users = []
        
        # Sample user data for Bengaluru
        sample_data = [
            {
                "name": "Arjun Kumar", 
                "email": "arjun.kumar@example.com",
                "age": 28,
                "location": Coordinates(lat=12.9716, lng=77.5946),  # MG Road
                "topics": [EventTopic.TRAFFIC, EventTopic.INFRASTRUCTURE]
            },
            {
                "name": "Priya Sharma", 
                "email": "priya.sharma@example.com", 
                "age": 25,
                "location": Coordinates(lat=12.9352, lng=77.6245),  # Koramangala
                "topics": [EventTopic.EVENTS, EventTopic.WEATHER]
            },
            {
                "name": "Rahul Reddy", 
                "email": "rahul.reddy@example.com",
                "age": 32,
                "location": Coordinates(lat=12.9116, lng=77.6370),  # HSR Layout  
                "topics": [EventTopic.TRAFFIC, EventTopic.SAFETY]
            },
            {
                "name": "Meera Patel", 
                "email": "meera.patel@example.com",
                "age": 29,
                "location": Coordinates(lat=12.9698, lng=77.7499),  # Whitefield
                "topics": [EventTopic.INFRASTRUCTURE, EventTopic.EVENTS]
            },
            {
                "name": "Vikram Singh", 
                "email": "vikram.singh@example.com",
                "age": 35,
                "location": Coordinates(lat=12.8456, lng=77.6603),  # Electronic City
                "topics": [EventTopic.TRAFFIC, EventTopic.WEATHER]
            }
        ]
        
        for i in range(min(count, len(sample_data))):
            data = sample_data[i]
            
            # Create user
            user = await user_data_manager.create_user(
                google_id=f"demo_user_{i+1}",
                email=data["email"],
                name=data["name"],
                age=data["age"],
                initial_location=data["location"]
            )
            
            # Set preferences
            await user_data_manager.update_user_preferences(
                user_id=user.id,
                preferred_topics=data["topics"],
                travel_mode="driving"
            )
            
            sample_users.append({
                "user_id": user.id,
                "name": data["name"],
                "email": data["email"],
                "location": {"lat": data["location"].lat, "lng": data["location"].lng}
            })
        
        return {
            "success": True,
            "message": f"Created {len(sample_users)} sample users",
            "users": sample_users
        }
        
    except Exception as e:
        logger.error(f"Error creating sample users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create sample users: {str(e)}")
