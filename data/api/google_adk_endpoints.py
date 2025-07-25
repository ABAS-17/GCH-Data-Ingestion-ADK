# data/api/google_adk_endpoints.py (continued)
"""
Google ADK-based API endpoints for the Agentic Layer
Provides enhanced conversational AI and dashboard content generation using Google ADK
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
from data.agents.clean_google_adk_agent import city_pulse_adk_agent

logger = logging.getLogger(__name__)

# Create router for Google ADK agentic endpoints
router = APIRouter(prefix="/adk", tags=["Google ADK AI"])

# ============================================================================
# REQUEST/RESPONSE MODELS (Enhanced for ADK)
# ============================================================================

class ADKChatRequest(BaseModel):
    user_id: str = Field(..., description="User ID for personalization")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    location: Optional[Coordinates] = Field(None, description="User's current location")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    stream: bool = Field(False, description="Enable streaming response")

class ADKDashboardRequest(BaseModel):
    user_id: str = Field(..., description="User ID for personalization") 
    refresh: bool = Field(False, description="Force refresh dashboard content")
    card_types: Optional[List[str]] = Field(None, description="Specific card types to generate")
    max_cards: int = Field(4, ge=1, le=6, description="Maximum number of cards")

class ADKInsightsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    insight_type: str = Field("general", description="Type of insights")
    location: Optional[Coordinates] = Field(None, description="Specific location for insights")
    timeframe: str = Field("24h", description="Time period for analysis")
    include_predictions: bool = Field(True, description="Include predictive insights")

class ADKAgentResponse(BaseModel):
    success: bool
    response: str
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_id: str
    knowledge_used: int = 0
    tools_called: List[str] = Field(default_factory=list)
    confidence_score: float = Field(0.8, ge=0.0, le=1.0)
    timestamp: str
    agent_type: str = "adk"

class ADKDashboardResponse(BaseModel):
    success: bool
    cards: List[Dict[str, Any]]
    total_cards: int
    personalization_score: float = Field(0.8, ge=0.0, le=1.0)
    generated_at: str
    user_id: str
    agent_type: str = "adk"

class ADKInsightsResponse(BaseModel):
    success: bool
    insights: str
    insight_type: str
    data_points_used: int = 0
    confidence_score: float = Field(0.8, ge=0.0, le=1.0)
    predictions: Optional[List[Dict[str, Any]]] = None
    generated_at: str
    agent_type: str = "adk"

# ============================================================================
# GOOGLE ADK CONVERSATION ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=ADKAgentResponse)
async def chat_with_adk_agent(
    request: ADKChatRequest,
    background_tasks: BackgroundTasks
):
    """Enhanced conversational AI using Google ADK framework"""
    try:
        logger.info(f"ADK agent chat request from user {request.user_id}: {request.message}")
        
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Handle conversation with Google ADK
        result = await city_pulse_adk_agent.handle_conversation(
            user_id=request.user_id,
            message=request.message,
            location=request.location
        )
        
        # Add background task for learning and analytics
        background_tasks.add_task(
            track_adk_interaction, 
            request.user_id, 
            request.message, 
            result.get("response", ""),
            "conversation"
        )
        
        return ADKAgentResponse(
            success=True,
            response=result.get("response", ""),
            suggested_actions=result.get("suggested_actions", []),
            conversation_id=result.get("conversation_id", ""),
            knowledge_used=result.get("knowledge_used", 0),
            tools_called=result.get("tools_called", []),
            confidence_score=result.get("confidence_score", 0.8),
            timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
            agent_type="adk"
        )
        
    except Exception as e:
        logger.error(f"Error in ADK agent chat: {e}")
        raise HTTPException(status_code=500, detail=f"ADK agent chat failed: {str(e)}")

@router.post("/dashboard", response_model=ADKDashboardResponse)
async def generate_adk_dashboard(
    request: ADKDashboardRequest,
    background_tasks: BackgroundTasks
):
    """Generate personalized dashboard using Google ADK specialized agent"""
    try:
        logger.info(f"ADK dashboard generation request for user {request.user_id}")
        
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Generate dashboard content using ADK
        cards = await city_pulse_adk_agent.generate_dashboard_content(request.user_id)
        
        # Apply filters if specified
        if request.card_types:
            cards = [card for card in cards if card.get("type") in request.card_types]
        
        # Limit cards
        cards = cards[:request.max_cards]
        
        # Calculate personalization score based on user context
        personalization_score = calculate_personalization_score(cards, request.user_id)
        
        # Add background task for dashboard analytics
        background_tasks.add_task(
            track_adk_interaction,
            request.user_id,
            f"dashboard_generation_{len(cards)}_cards",
            "",
            "dashboard"
        )
        
        return ADKDashboardResponse(
            success=True,
            cards=cards,
            total_cards=len(cards),
            personalization_score=personalization_score,
            generated_at=datetime.utcnow().isoformat(),
            user_id=request.user_id,
            agent_type="adk"
        )
        
    except Exception as e:
        logger.error(f"Error generating ADK dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"ADK dashboard generation failed: {str(e)}")

@router.post("/insights", response_model=ADKInsightsResponse)
async def get_adk_insights(
    request: ADKInsightsRequest,
    background_tasks: BackgroundTasks
):
    """Get enhanced insights using Google ADK analytics agent"""
    try:
        logger.info(f"ADK insights request for user {request.user_id}, type: {request.insight_type}")
        
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Generate insights using ADK
        result = await city_pulse_adk_agent.get_personalized_insights(
            user_id=request.user_id,
            insight_type=request.insight_type
        )
        
        # Generate predictions if requested
        predictions = None
        if request.include_predictions:
            predictions = await generate_predictive_insights(
                request.user_id, 
                request.insight_type,
                request.timeframe
            )
        
        # Add background task for insights tracking
        background_tasks.add_task(
            track_adk_interaction,
            request.user_id,
            f"insights_{request.insight_type}",
            result.get("insights", ""),
            "insights"
        )
        
        return ADKInsightsResponse(
            success=True,
            insights=result.get("insights", ""),
            insight_type=result.get("insight_type", "general"),
            data_points_used=result.get("data_points_used", 0),
            confidence_score=result.get("confidence_score", 0.8),
            predictions=predictions,
            generated_at=result.get("generated_at", datetime.utcnow().isoformat()),
            agent_type="adk"
        )
        
    except Exception as e:
        logger.error(f"Error generating ADK insights: {e}")
        raise HTTPException(status_code=500, detail=f"ADK insights generation failed: {str(e)}")

# ============================================================================
# ENHANCED CONVERSATION MANAGEMENT
# ============================================================================

@router.get("/chat/{user_id}/history")
async def get_adk_conversation_history(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of messages to retrieve")
):
    """Get conversation history from ADK agent"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Get conversation history
        history = city_pulse_adk_agent.conversation_sessions.get(user_id, [])
        
        return {
            "success": True,
            "user_id": user_id,
            "conversation_history": history[-limit:],
            "total_messages": len(history),
            "agent_type": "adk",
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ADK conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.post("/chat/{user_id}/reset")
async def reset_adk_conversation(
    user_id: str = Path(..., description="User ID"),
    clear_context: bool = Query(True, description="Clear user context cache")
):
    """Reset ADK conversation and optionally clear context"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Clear conversation history
        if user_id in city_pulse_adk_agent.conversation_sessions:
            del city_pulse_adk_agent.conversation_sessions[user_id]
        
        # Clear user context cache if requested
        if clear_context and user_id in city_pulse_adk_agent.user_contexts:
            del city_pulse_adk_agent.user_contexts[user_id]
        
        return {
            "success": True,
            "message": "ADK conversation reset successfully",
            "user_id": user_id,
            "context_cleared": clear_context,
            "agent_type": "adk",
            "reset_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting ADK conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset conversation: {str(e)}")

@router.get("/dashboard/{user_id}")
async def get_adk_dashboard_for_user(
    user_id: str = Path(..., description="User ID"),
    refresh: bool = Query(False, description="Force refresh dashboard content"),
    card_types: Optional[str] = Query(None, description="Comma-separated card types"),
    max_cards: int = Query(4, ge=1, le=6, description="Maximum cards")
):
    """Get ADK dashboard content for specific user (GET convenience endpoint)"""
    try:
        card_types_list = card_types.split(",") if card_types else None
        
        request = ADKDashboardRequest(
            user_id=user_id,
            refresh=refresh,
            card_types=card_types_list,
            max_cards=max_cards
        )
        
        return await generate_adk_dashboard(request, BackgroundTasks())
        
    except Exception as e:
        logger.error(f"Error getting ADK dashboard for user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

# ============================================================================
# ADK AGENT TESTING AND DIAGNOSTICS
# ============================================================================

@router.get("/test/status")
async def test_adk_agent_status():
    """Test ADK agent status and capabilities"""
    try:
        if not city_pulse_adk_agent:
            return {
                "success": False,
                "status": "ADK agent not available",
                "adk_installed": False,
                "message": "Please install Google ADK: pip install google-adk",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "success": True,
            "status": "ADK agent operational",
            "adk_installed": True,
            "agents_available": list(city_pulse_adk_agent.agents.keys()) if hasattr(city_pulse_adk_agent, 'agents') else [],
            "session_service_active": city_pulse_adk_agent.session_service is not None,
            "runner_initialized": city_pulse_adk_agent.runner is not None,
            "message": "ADK agent is working correctly",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing ADK agent: {e}")
        return {
            "success": False,
            "status": "ADK agent error",
            "error": str(e),
            "message": "ADK agent test failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test/chat")
async def test_adk_chat():
    """Test ADK chat functionality"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Test conversation
        test_result = await city_pulse_adk_agent.handle_conversation(
            user_id="adk_test_user",
            message="How is traffic in Koramangala right now?",
            location=Coordinates(lat=12.9352, lng=77.6245)
        )
        
        return {
            "success": True,
            "test_result": test_result,
            "message": "ADK chat is working correctly",
            "agent_type": "adk",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in ADK chat test: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "ADK chat test failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test/dashboard")
async def test_adk_dashboard():
    """Test ADK dashboard generation"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        # Test dashboard generation
        test_cards = await city_pulse_adk_agent.generate_dashboard_content("adk_test_user")
        
        return {
            "success": True,
            "test_cards": test_cards,
            "cards_generated": len(test_cards),
            "message": "ADK dashboard generation working correctly",
            "agent_type": "adk",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in ADK dashboard test: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "ADK dashboard test failed",
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# ADK ANALYTICS AND MONITORING
# ============================================================================

@router.get("/analytics/usage")
async def get_adk_usage_analytics():
    """Get detailed analytics about ADK agent usage"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        total_users = len(city_pulse_adk_agent.conversation_sessions)
        total_conversations = sum(len(conv) for conv in city_pulse_adk_agent.conversation_sessions.values())
        
        # Enhanced analytics for ADK
        analytics = {
            "agent_type": "google_adk",
            "total_users_with_conversations": total_users,
            "total_conversation_messages": total_conversations,
            "average_messages_per_user": total_conversations / total_users if total_users > 0 else 0,
            "cached_user_contexts": len(city_pulse_adk_agent.user_contexts),
            "agents_available": list(city_pulse_adk_agent.agents.keys()) if hasattr(city_pulse_adk_agent, 'agents') else [],
            "session_service_active": city_pulse_adk_agent.session_service is not None,
            "runner_initialized": city_pulse_adk_agent.runner is not None,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting ADK analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/analytics/agents")
async def get_adk_agents_info():
    """Get information about available ADK agents"""
    try:
        if not city_pulse_adk_agent:
            raise HTTPException(status_code=503, detail="ADK agent not available")
        
        agents_info = {}
        if hasattr(city_pulse_adk_agent, 'agents'):
            for agent_name, agent in city_pulse_adk_agent.agents.items():
                agents_info[agent_name] = {
                    "name": agent.name if hasattr(agent, 'name') else agent_name,
                    "model": agent.model if hasattr(agent, 'model') else "unknown",
                    "description": agent.description if hasattr(agent, 'description') else "No description",
                    "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                    "tool_names": [tool.__name__ for tool in agent.tools] if hasattr(agent, 'tools') else []
                }
        
        return {
            "success": True,
            "agents_count": len(agents_info),
            "agents": agents_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ADK agents info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agents info: {str(e)}")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_personalization_score(cards: List[Dict[str, Any]], user_id: str) -> float:
    """Calculate personalization score based on card relevance"""
    try:
        if not cards:
            return 0.0
        
        # Simple scoring based on card types and confidence
        score = 0.0
        for card in cards:
            confidence = card.get("confidence", 0.8)
            priority_weight = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}.get(
                card.get("priority", "medium"), 0.6
            )
            score += confidence * priority_weight
        
        return min(score / len(cards), 1.0)
    except Exception:
        return 0.8  # Default score

async def generate_predictive_insights(user_id: str, insight_type: str, timeframe: str) -> List[Dict[str, Any]]:
    """Generate predictive insights based on historical patterns"""
    try:
        # Mock predictive insights - in production, use ML models
        predictions = [
            {
                "type": "traffic_prediction",
                "prediction": "Heavy traffic expected on ORR between 5-7 PM today",
                "confidence": 0.85,
                "timeframe": "next_6_hours",
                "recommendation": "Consider leaving early or using alternate routes"
            },
            {
                "type": "weather_prediction", 
                "prediction": "Light rainfall likely in South Bengaluru after 3 PM",
                "confidence": 0.72,
                "timeframe": "next_4_hours",
                "recommendation": "Carry umbrella if traveling outdoors"
            }
        ]
        
        # Filter by insight type
        if insight_type != "general":
            predictions = [p for p in predictions if insight_type in p["type"]]
        
        return predictions
    except Exception as e:
        logger.error(f"Error generating predictive insights: {e}")
        return []

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def track_adk_interaction(user_id: str, user_input: str, agent_output: str, interaction_type: str):
    """Background task to track ADK agent interactions"""
    try:
        logger.info(f"ADK interaction tracked - User: {user_id}, Type: {interaction_type}, Input: {len(user_input)} chars, Output: {len(agent_output)} chars")
        
        # Here you could store enhanced analytics for ADK usage
        # - Track tool usage patterns
        # - Monitor response quality
        # - Analyze user satisfaction
        # - Store for ML model training
        
    except Exception as e:
        logger.error(f"Error tracking ADK interaction: {e}")
