# data/api/agentic_endpoints.py
"""
API endpoints for the Agentic Layer
Provides conversational AI and dashboard content generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pydantic import BaseModel, Field

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models.schemas import Coordinates
from data.agents.city_pulse_agentic_layer import city_pulse_agent

logger = logging.getLogger(__name__)

# Create router for agentic endpoints
router = APIRouter(prefix="/agent", tags=["Agentic AI"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentChatRequest(BaseModel):
    user_id: str = Field(..., description="User ID for personalization")
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    location: Optional[Coordinates] = Field(None, description="User's current location")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session context")

class DashboardRequest(BaseModel):
    user_id: str = Field(..., description="User ID for personalization")
    refresh: bool = Field(False, description="Force refresh dashboard content")

class InsightsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    insight_type: str = Field("general", description="Type of insights (general, traffic, weather, events)")
    location: Optional[Coordinates] = Field(None, description="Specific location for insights")

class AgentResponse(BaseModel):
    success: bool
    response: str
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_id: str
    knowledge_used: int = 0
    timestamp: str

class DashboardResponse(BaseModel):
    success: bool
    cards: List[Dict[str, Any]]
    total_cards: int
    generated_at: str
    user_id: str

class InsightsResponse(BaseModel):
    success: bool
    insights: str
    insight_type: str
    data_points_used: int = 0
    generated_at: str

# ============================================================================
# AGENTIC CONVERSATION ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentChatRequest,
    background_tasks: BackgroundTasks
):
    """Conversational AI interface - handles user questions and provides intelligent responses"""
    try:
        logger.info(f"Agent chat request from user {request.user_id}: {request.message}")
        
        # Handle conversation with the agentic layer
        result = await city_pulse_agent.handle_conversation(
            user_id=request.user_id,
            message=request.message,
            location=request.location
        )
        
        # Add background task to learn from interaction
        background_tasks.add_task(
            track_agent_interaction, 
            request.user_id, 
            request.message, 
            result.get("response", "")
        )
        
        return AgentResponse(
            success=True,
            response=result.get("response", ""),
            suggested_actions=result.get("suggested_actions", []),
            conversation_id=result.get("conversation_id", ""),
            knowledge_used=result.get("knowledge_used", 0),
            timestamp=result.get("timestamp", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error in agent chat: {e}")
        raise HTTPException(status_code=500, detail=f"Agent chat failed: {str(e)}")

@router.post("/dashboard", response_model=DashboardResponse)
async def generate_dashboard(
    request: DashboardRequest,
    background_tasks: BackgroundTasks
):
    """Generate personalized dashboard cards for user"""
    try:
        logger.info(f"Dashboard generation request for user {request.user_id}")
        
        # Generate dashboard content using agentic layer
        cards = await city_pulse_agent.generate_dashboard_content(request.user_id)
        
        # Add background task to track dashboard usage
        background_tasks.add_task(track_dashboard_generation, request.user_id, len(cards))
        
        return DashboardResponse(
            success=True,
            cards=cards,
            total_cards=len(cards),
            generated_at=datetime.utcnow().isoformat(),
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

@router.post("/insights", response_model=InsightsResponse)
async def get_personalized_insights(
    request: InsightsRequest
):
    """Get personalized insights based on user context and city data"""
    try:
        logger.info(f"Insights request for user {request.user_id}, type: {request.insight_type}")
        
        # Generate insights using agentic layer
        result = await city_pulse_agent.get_personalized_insights(
            user_id=request.user_id,
            insight_type=request.insight_type
        )
        
        return InsightsResponse(
            success=True,
            insights=result.get("insights", ""),
            insight_type=result.get("insight_type", "general"),
            data_points_used=result.get("data_points_used", 0),
            generated_at=result.get("generated_at", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")

# ============================================================================
# CONVENIENCE ENDPOINTS
# ============================================================================

@router.get("/chat/{user_id}/history")
async def get_conversation_history(
    user_id: str = Path(..., description="User ID")
):
    """Get conversation history for user"""
    try:
        # Get conversation history from agent
        history = city_pulse_agent.conversation_sessions.get(user_id, [])
        
        return {
            "success": True,
            "user_id": user_id,
            "conversation_history": history[-10:],  # Last 10 messages
            "total_messages": len(history),
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.post("/chat/{user_id}/reset")
async def reset_conversation(
    user_id: str = Path(..., description="User ID")
):
    """Reset conversation history for user"""
    try:
        # Clear conversation history
        if user_id in city_pulse_agent.conversation_sessions:
            del city_pulse_agent.conversation_sessions[user_id]
        
        # Clear user context cache
        if user_id in city_pulse_agent.user_contexts:
            del city_pulse_agent.user_contexts[user_id]
        
        return {
            "success": True,
            "message": "Conversation reset successfully",
            "user_id": user_id,
            "reset_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset conversation: {str(e)}")

@router.get("/dashboard/{user_id}")
async def get_dashboard_for_user(
    user_id: str = Path(..., description="User ID"),
    refresh: bool = Query(False, description="Force refresh dashboard content")
):
    """Get dashboard content for specific user (GET convenience endpoint)"""
    try:
        request = DashboardRequest(user_id=user_id, refresh=refresh)
        return await generate_dashboard(request, BackgroundTasks())
        
    except Exception as e:
        logger.error(f"Error getting dashboard for user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

# ============================================================================
# QUICK TESTING ENDPOINTS
# ============================================================================

@router.get("/test/chat")
async def test_chat_endpoint():
    """Test endpoint for quick agent functionality check"""
    try:
        # Test with a sample user
        test_result = await city_pulse_agent.handle_conversation(
            user_id="test_user",
            message="Hello, how is traffic in Bengaluru?",
            location=Coordinates(lat=12.9716, lng=77.5946)
        )
        
        return {
            "success": True,
            "test_result": test_result,
            "message": "Agent is working correctly",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test chat: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Agent test failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test/dashboard")
async def test_dashboard_endpoint():
    """Test endpoint for dashboard generation"""
    try:
        # Test dashboard generation
        test_cards = await city_pulse_agent.generate_dashboard_content("test_user")
        
        return {
            "success": True,
            "test_cards": test_cards,
            "cards_generated": len(test_cards),
            "message": "Dashboard generation working correctly",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test dashboard: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Dashboard test failed",
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/usage")
async def get_agent_usage_analytics():
    """Get analytics about agent usage"""
    try:
        total_users = len(city_pulse_agent.conversation_sessions)
        total_conversations = sum(len(conv) for conv in city_pulse_agent.conversation_sessions.values())
        
        analytics = {
            "total_users_with_conversations": total_users,
            "total_conversation_messages": total_conversations,
            "average_messages_per_user": total_conversations / total_users if total_users > 0 else 0,
            "cached_user_contexts": len(city_pulse_agent.user_contexts),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def track_agent_interaction(user_id: str, user_message: str, agent_response: str):
    """Background task to track agent interactions for learning"""
    try:
        logger.info(f"Tracking interaction for user {user_id}: {len(user_message)} chars in, {len(agent_response)} chars out")
        # Here you could store interaction data for learning purposes
        
    except Exception as e:
        logger.error(f"Error tracking interaction: {e}")

async def track_dashboard_generation(user_id: str, cards_count: int):
    """Background task to track dashboard generation"""
    try:
        logger.info(f"Dashboard generated for user {user_id}: {cards_count} cards")
        # Here you could store dashboard analytics
        
    except Exception as e:
        logger.error(f"Error tracking dashboard generation: {e}")
