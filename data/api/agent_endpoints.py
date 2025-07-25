# data/api/agent_endpoints.py
"""
API endpoints for the Enhanced City Pulse Agent
Provides conversational AI interface with user awareness and personalization
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pydantic import BaseModel, Field
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models.schemas import Coordinates, EventTopic
from data.agents.enhanced_city_agent import enhanced_city_pulse_agent

logger = logging.getLogger(__name__)

# Create router for agent endpoints
router = APIRouter(prefix="/agent", tags=["Enhanced Agent"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentQueryRequest(BaseModel):
    user_id: str = Field(..., description="User ID for personalization")
    message: str = Field(..., min_length=1, max_length=1000, description="User message/query")
    location: Optional[Coordinates] = Field(None, description="User's current location")
    media_references: List[str] = Field(default_factory=list, description="URLs of uploaded media")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session context")
    include_proactive: bool = Field(True, description="Include proactive suggestions")

class PersonalizedChatRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="Chat message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")
    location: Optional[Coordinates] = Field(None, description="Current location")
    context_window: int = Field(5, ge=1, le=20, description="Number of previous messages to consider")

class AgentResponse(BaseModel):
    success: bool
    response: Dict[str, Any]
    personalization: Dict[str, Any] = Field(default_factory=dict)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    user_insights: Optional[Dict[str, Any]] = None
    timestamp: str

class ConversationResponse(BaseModel):
    success: bool
    message_id: str
    response: str
    suggestions: List[str] = Field(default_factory=list)
    action_buttons: List[Dict[str, Any]] = Field(default_factory=list)
    relevant_events: List[Dict[str, Any]] = Field(default_factory=list)
    personalized: bool = True
    confidence: float
    timestamp: str


# ============================================================================
# CORE AGENT ENDPOINTS
# ============================================================================

@router.post("/query", response_model=AgentResponse)
async def process_agent_query(
    request: AgentQueryRequest,
    background_tasks: BackgroundTasks
):
    """
    Main agent endpoint - processes user queries with full personalization
    """
    try:
        # Process the query through enhanced agent
        agent_result = await enhanced_city_pulse_agent.process_user_query(
            user_id=request.user_id,
            message=request.message,
            location=request.location,
            media_references=request.media_references,
            session_context=request.session_context
        )
        
        # Extract personalization info
        personalization = {
            "applied": agent_result.get("personalization_applied", False),
            "user_preferences_used": bool(agent_result.get("context_used", {}).get("user_profile")),
            "location_aware": bool(request.location),
            "conversation_context": len(agent_result.get("context_used", {}).get("conversation_history", [])),
            "knowledge_base_results": len(agent_result.get("context_used", {}).get("relevant_events", []))
        }
        
        # Add background task for learning
        if agent_result.get("learning_insights"):
            background_tasks.add_task(
                process_learning_insights, 
                request.user_id, 
                agent_result["learning_insights"]
            )
        
        return AgentResponse(
            success=True,
            response=agent_result["response"],
            personalization=personalization,
            suggestions=agent_result.get("proactive_suggestions", []),
            user_insights=agent_result.get("learning_insights"),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing agent query: {e}")
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")


@router.post("/chat", response_model=ConversationResponse)
async def personalized_chat(
    request: PersonalizedChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Conversational chat endpoint with user awareness and context
    """
    try:
        # Process through enhanced agent
        agent_result = await enhanced_city_pulse_agent.process_user_query(
            user_id=request.user_id,
            message=request.message,
            location=request.location
        )
        
        response_data = agent_result.get("response", {})
        
        # Generate message ID
        message_id = f"msg_{request.user_id[:8]}_{int(datetime.utcnow().timestamp())}"
        
        return ConversationResponse(
            success=True,
            message_id=message_id,
            response=response_data.get("main_message", "I'm here to help!"),
            suggestions=response_data.get("suggestions", []),
            action_buttons=response_data.get("action_buttons", []),
            relevant_events=response_data.get("relevant_events", []),
            personalized=agent_result.get("personalization_applied", True),
            confidence=response_data.get("confidence_level", 0.8),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in personalized chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/suggestions/{user_id}")
async def get_proactive_suggestions(
    user_id: str = Path(..., description="User ID"),
    location_lat: Optional[float] = Query(None, description="Current latitude"),
    location_lng: Optional[float] = Query(None, description="Current longitude"),
    max_suggestions: int = Query(5, ge=1, le=10, description="Maximum suggestions")
):
    """
    Get proactive suggestions based on user context and current conditions
    """
    try:
        location = None
        if location_lat and location_lng:
            location = Coordinates(lat=location_lat, lng=location_lng)
        
        # Get user for context
        from data.database.user_manager import user_data_manager
        user = await user_data_manager.get_user(user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "User not found"
                }
            )
        
        # Generate suggestions
        suggestions = await enhanced_city_pulse_agent._generate_user_aware_suggestions(
            user=user,
            intent_analysis={"topic_category": "general", "urgency_level": "low"},
            location=location
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "suggestions": suggestions[:max_suggestions],
            "location_context": bool(location),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting proactive suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


# ============================================================================
# SPECIALIZED AGENT CAPABILITIES
# ============================================================================

@router.post("/commute-planning")
async def get_personalized_commute_plan(
    user_id: str = Query(..., description="User ID"),
    destination: Optional[str] = Query(None, description="Destination override"),
    departure_time: Optional[str] = Query(None, description="Preferred departure time"),
    travel_mode: Optional[str] = Query(None, description="Travel mode override")
):
    """
    Get personalized commute planning with real-time conditions
    """
    try:
        # Get user data
        from data.database.user_manager import user_data_manager
        user = await user_data_manager.get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build commute query
        if destination:
            commute_message = f"Plan my commute to {destination}"
        elif user.locations.work:
            commute_message = f"Plan my commute to work at {user.locations.work.formatted_address}"
        else:
            commute_message = "Help me plan my commute"
        
        if departure_time:
            commute_message += f" departing at {departure_time}"
        
        # Process through agent
        agent_result = await enhanced_city_pulse_agent.process_user_query(
            user_id=user_id,
            message=commute_message,
            location=user.locations.current
        )
        
        return {
            "success": True,
            "commute_plan": agent_result["response"],
            "real_time_conditions": agent_result.get("context_used", {}).get("relevant_events", []),
            "personalized": True,
            "user_preferences_applied": True
        }
        
    except Exception as e:
        logger.error(f"Error in commute planning: {e}")
        raise HTTPException(status_code=500, detail=f"Commute planning failed: {str(e)}")


@router.post("/local-recommendations")
async def get_local_recommendations(
    user_id: str = Query(..., description="User ID"),
    category: Optional[EventTopic] = Query(None, description="Specific category"),
    radius_km: float = Query(5, ge=1, le=20, description="Search radius"),
    time_filter: Optional[str] = Query(None, description="Time filter (now, today, weekend)")
):
    """
    Get personalized local recommendations based on user preferences and location
    """
    try:
        # Get user data
        from data.database.user_manager import user_data_manager
        user = await user_data_manager.get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build recommendation query
        query_parts = ["recommendations"]
        
        if category:
            query_parts.append(category.value)
        
        if time_filter:
            query_parts.append(time_filter)
        
        recommendation_message = f"Show me {' '.join(query_parts)} in my area"
        
        # Process through agent
        agent_result = await enhanced_city_pulse_agent.process_user_query(
            user_id=user_id,
            message=recommendation_message,
            location=user.locations.current
        )
        
        return {
            "success": True,
            "recommendations": agent_result["response"],
            "personalization": {
                "user_preferences_matched": True,
                "location_based": bool(user.locations.current),
                "category_filter": category.value if category else "all",
                "radius_km": radius_km
            },
            "relevant_events": agent_result.get("context_used", {}).get("relevant_events", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting local recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


# ============================================================================
# AGENT ANALYTICS AND INSIGHTS
# ============================================================================

@router.get("/analytics/{user_id}")
async def get_user_agent_analytics(
    user_id: str = Path(..., description="User ID"),
    timeframe: str = Query("30d", description="Analytics timeframe")
):
    """
    Get analytics about user's interactions with the agent
    """
    try:
        # Get conversation history
        conversation_memory = enhanced_city_pulse_agent.conversation_memory.get(user_id, [])
        
        # Calculate interaction statistics
        total_interactions = len(conversation_memory)
        recent_interactions = [
            msg for msg in conversation_memory
            if datetime.fromisoformat(msg["timestamp"]) > datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ]
        
        # Analyze interaction patterns
        topics_discussed = {}
        for msg in conversation_memory:
            intent = msg.get("intent", {})
            topic = intent.get("topic_category", "general")
            topics_discussed[topic] = topics_discussed.get(topic, 0) + 1
        
        analytics = {
            "user_id": user_id,
            "timeframe": timeframe,
            "interaction_stats": {
                "total_interactions": total_interactions,
                "interactions_today": len(recent_interactions),
                "avg_interactions_per_day": total_interactions / 30 if total_interactions > 0 else 0
            },
            "topic_distribution": topics_discussed,
            "most_discussed_topic": max(topics_discussed.items(), key=lambda x: x[1])[0] if topics_discussed else None,
            "personalization_metrics": {
                "location_aware_queries": len([msg for msg in conversation_memory if msg.get("location")]),
                "context_aware_responses": len([msg for msg in conversation_memory if msg.get("user_context")])
            },
            "response_quality": {
                "avg_confidence": sum(msg.get("response_quality", 0.5) for msg in conversation_memory) / max(total_interactions, 1),
                "high_confidence_responses": len([msg for msg in conversation_memory if msg.get("response_quality", 0) > 0.8])
            }
        }
        
        return {
            "success": True,
            "analytics": analytics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user agent analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


@router.get("/health")
async def agent_health_check():
    """Health check for the enhanced agent system"""
    try:
        # Check if agent is initialized
        agent_healthy = bool(enhanced_city_pulse_agent.model)
        
        # Check data layer connections
        from data.database.user_manager import user_data_manager
        from data.database.database_manager import db_manager
        
        user_manager_healthy = await user_data_manager.health_check()
        db_manager_healthy = await db_manager.health_check()
        
        health_status = {
            "agent_initialized": agent_healthy,
            "user_manager": user_manager_healthy.get("overall_healthy", False),
            "knowledge_base": db_manager_healthy.get("chroma_db", False),
            "active_sessions": len(enhanced_city_pulse_agent.active_sessions),
            "conversation_memory_users": len(enhanced_city_pulse_agent.conversation_memory),
            "personalization_cache_size": len(enhanced_city_pulse_agent.personalization_cache)
        }
        
        overall_healthy = all([
            agent_healthy,
            user_manager_healthy.get("overall_healthy", False),
            db_manager_healthy.get("chroma_db", False)
        ])
        
        status_code = 200 if overall_healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": overall_healthy,
                "health_status": health_status,
                "overall_healthy": overall_healthy,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def process_learning_insights(user_id: str, insights: Dict[str, Any]):
    """Background task to process learning insights for user personalization"""
    try:
        logger.info(f"Processing learning insights for user {user_id}")
        
        # Update user preferences based on insights
        if insights.get("preference_learning", {}).get("suggested_new_topic"):
            from data.database.user_manager import user_data_manager
            suggested_topic = insights["preference_learning"]["suggested_new_topic"]
            confidence = insights["preference_learning"]["confidence"]
            
            if confidence > 0.8:  # High confidence threshold
                await user_data_manager.add_preferred_topic(user_id, EventTopic(suggested_topic))
                logger.info(f"Added new preferred topic '{suggested_topic}' for user {user_id}")
        
        # Update behavioral patterns
        if insights.get("behavioral_patterns", {}).get("recurring_intent"):
            # Could update user context or trigger proactive suggestions
            pass
        
        logger.info(f"Completed processing learning insights for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing learning insights: {e}")
