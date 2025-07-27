"""
Authentication endpoints for user registration and login
"""

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Import our auth models and database
from auth_models import UserRegisterRequest, UserLoginRequest, UserResponse, AuthToken
from auth_database import auth_db

logger = logging.getLogger(__name__)

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security
security = HTTPBearer(auto_error=False)

# ============================================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from token"""
    if not credentials:
        return None
    
    token_result = await auth_db.verify_token(credentials.credentials)
    if not token_result["success"]:
        return None
    
    return {
        "user_id": token_result["user_id"],
        "username": token_result["username"],
        "email": token_result["email"]
    }

async def require_auth(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require authentication for protected endpoints"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register", response_model=UserResponse)
async def register_user(request: UserRegisterRequest, background_tasks: BackgroundTasks):
    """Register a new user account"""
    try:
        logger.info(f"🔐 Registration attempt for: {request.username} ({request.email})")
        
        # Register user in database
        result = await auth_db.register_user(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        if not result["success"]:
            logger.warning(f"❌ Registration failed for {request.username}: {result['message']}")
            raise HTTPException(status_code=400, detail=result["message"])
        
        # Schedule cleanup task
        background_tasks.add_task(auth_db.cleanup_expired_tokens)
        
        logger.info(f"✅ User registered successfully: {request.username}")
        
        return UserResponse(
            success=True,
            message="User registered successfully! You can now login.",
            user_id=result["user_id"],
            username=result["username"],
            email=result["email"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=UserResponse)
async def login_user(request: UserLoginRequest, background_tasks: BackgroundTasks):
    """Login user and return authentication token"""
    try:
        logger.info(f"🔐 Login attempt for: {request.email}")
        
        # Attempt login
        result = await auth_db.login_user(
            email=request.email,
            password=request.password
        )
        
        if not result["success"]:
            logger.warning(f"❌ Login failed for {request.email}: {result['message']}")
            raise HTTPException(status_code=401, detail=result["message"])
        
        # Schedule cleanup task
        background_tasks.add_task(auth_db.cleanup_expired_tokens)
        
        logger.info(f"✅ User logged in successfully: {result['username']}")
        
        return UserResponse(
            success=True,
            message="Login successful!",
            user_id=result["user_id"],
            username=result["username"],
            email=result["email"],
            token=result["token"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user by invalidating their token"""
    try:
        if not credentials:
            raise HTTPException(status_code=401, detail="No token provided")
        
        result = await auth_db.logout_user(credentials.credentials)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        logger.info("✅ User logged out successfully")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get current authenticated user information"""
    try:
        return {
            "success": True,
            "user": {
                "user_id": current_user["user_id"],
                "username": current_user["username"],
                "email": current_user["email"]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")

@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify if the provided token is valid"""
    try:
        if not credentials:
            raise HTTPException(status_code=401, detail="No token provided")
        
        result = await auth_db.verify_token(credentials.credentials)
        
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result["message"])
        
        return {
            "success": True,
            "message": "Token is valid",
            "user": {
                "user_id": result["user_id"],
                "username": result["username"],
                "email": result["email"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(status_code=500, detail="Token verification failed")

# ============================================================================
# PROTECTED DEMO ENDPOINTS
# ============================================================================

@router.get("/protected")
async def protected_endpoint(current_user: Dict[str, Any] = Depends(require_auth)):
    """Example protected endpoint that requires authentication"""
    return {
        "success": True,
        "message": f"Hello {current_user['username']}! This is a protected endpoint.",
        "user_info": current_user,
        "server_time": datetime.utcnow().isoformat()
    }

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/stats")
async def get_auth_stats():
    """Get authentication system statistics"""
    try:
        stats = await auth_db.get_user_stats()
        
        return {
            "success": True,
            "stats": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting auth stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get authentication statistics")

@router.post("/cleanup")
async def cleanup_expired_tokens():
    """Manual cleanup of expired tokens"""
    try:
        await auth_db.cleanup_expired_tokens()
        
        return {
            "success": True,
            "message": "Expired tokens cleaned up successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up tokens: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def auth_health_check():
    """Health check for authentication system"""
    try:
        # Test database connection
        stats = await auth_db.get_user_stats()
        
        return {
            "success": True,
            "message": "Authentication system is healthy",
            "database_connected": True,
            "user_count": stats.get("total_users", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Auth health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"Authentication system unhealthy: {str(e)}"
        )