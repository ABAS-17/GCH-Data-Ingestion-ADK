#!/usr/bin/env python3
"""
City Pulse Agent - FastAPI Backend
Complete REST API for smart city incident reporting and management
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
from datetime import datetime, timedelta
import json
import io
import sys
import os
import time
from functools import lru_cache

# Add data layer to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our data layer
from data.database.database_manager import db_manager
from data.processors.enhanced_event_processor import enhanced_processor
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
from data.api.subcategory_endpoints import router as subcategory_router
from data.database.storage_client import storage_client
from data.models.schemas import (
    Event, User, EventCreateRequest, EventTopic, EventSeverity,
    Coordinates, ChatRequest, ChatResponse
)
from data.models.media_schemas import (
    MediaFile, EnhancedEventCreateRequest, MediaUploadResponse,
    MediaAnalysisResponse, IncidentReport, IncidentReportStatus,
    ChatWithMediaRequest, EnhancedChatResponse
)
from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="City Pulse Agent API",
    description="AI-powered smart city incident reporting and management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API routers
app.include_router(subcategory_router)

# Import and add user management router
from data.api.user_endpoints import router as user_router
app.include_router(user_router)

# Security
security = HTTPBearer(auto_error=False)

# Simple cache for dashboard cards
dashboard_cache = {}
CACHE_DURATION = 300  # 5 minutes

# ============================================================================
# STARTUP AND HEALTH CHECK
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize databases and services on startup"""
    logger.info("🚀 Starting City Pulse Agent API...")
    
    # Initialize databases
    db_healthy = await db_manager.initialize_databases()
    if not db_healthy:
        logger.error("❌ Database initialization failed")
        raise RuntimeError("Database initialization failed")
    
    # Initialize enhanced subcategory processor
    subcategory_healthy = await enhanced_subcategory_processor.initialize()
    if not subcategory_healthy:
        logger.warning("⚠️ Subcategory processor initialization failed - using fallback")
    
    logger.info("✅ City Pulse Agent API started successfully")

@app.get("/health", tags=["System"])
async def health_check():
    """System health check"""
    try:
        health = await db_manager.health_check()
        stats = await db_manager.get_system_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": health,
            "stats": stats,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/", tags=["System"])
async def root():
    """API welcome message"""
    return {
        "message": "🏙️ City Pulse Agent API",
        "description": "AI-powered smart city incident reporting",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

# ============================================================================
# EVENT MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/events", response_model=Dict[str, Any], tags=["Events"])
async def create_event(
    event_request: EventCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "anonymous"
):
    """Create a new event from citizen report"""
    try:
        # Process the user report using enhanced subcategory processor
        event = await enhanced_subcategory_processor.process_user_report(event_request, user_id)
        
        # IMMEDIATELY add to ChromaDB for search indexing
        try:
            from data.database.chroma_client import chroma_client
            indexing_success = await chroma_client.add_event(event)
            if indexing_success:
                logger.info(f"✅ Event {event.id} successfully indexed in ChromaDB")
            else:
                logger.warning(f"⚠️ Failed to index event {event.id} in ChromaDB")
        except Exception as e:
            logger.error(f"❌ Error indexing event {event.id}: {e}")
        
        # Add background task for additional processing
        background_tasks.add_task(post_process_event, event.id)
        
        return {
            "success": True,
            "event_id": event.id,
            "message": "Event created successfully",
            "event": {
                "id": event.id,
                "title": event.content.title,
                "topic": event.topic.value,
                "severity": event.impact_analysis.severity.value,
                "location": {
                    "lat": event.geographic_data.location.lat,
                    "lng": event.geographic_data.location.lng,
                    "address": event.geographic_data.location.address
                },
                "created_at": event.temporal_data.created_at.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")

@app.post("/events/enhanced", response_model=Dict[str, Any], tags=["Events"])
async def create_enhanced_event(
    enhanced_request: EnhancedEventCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "anonymous"
):
    """Create event with comprehensive media support"""
    try:
        # Convert to basic request for processing
        location_data = enhanced_request.location
        if hasattr(location_data, 'lat') and hasattr(location_data, 'lng'):
            location_dict = {"lat": location_data.lat, "lng": location_data.lng}
        else:
            location_dict = location_data
            
        basic_request = EventCreateRequest(
            topic=enhanced_request.topic,
            sub_topic=enhanced_request.sub_topic,
            title=enhanced_request.title,
            description=enhanced_request.description,
            location=location_dict,
            address=enhanced_request.address,
            severity=enhanced_request.severity,
            media_urls=enhanced_request.media_urls
        )
        
        # Process media files if provided
        uploaded_urls = []
        if enhanced_request.media_files:
            for media_file in enhanced_request.media_files:
                if media_file.data:
                    url = await storage_client.upload_media(
                        media_file.data,
                        media_file.filename,
                        media_file.content_type,
                        user_id,
                        f"temp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    if url:
                        uploaded_urls.append(url)
        
        # Add uploaded URLs to media URLs
        basic_request.media_urls.extend(uploaded_urls)
        
        # Create the event
        event = await db_manager.process_user_report(basic_request, user_id)
        
        # IMMEDIATELY add to ChromaDB for search indexing
        try:
            from data.database.chroma_client import chroma_client
            indexing_success = await chroma_client.add_event(event)
            if indexing_success:
                logger.info(f"✅ Enhanced event {event.id} successfully indexed in ChromaDB")
            else:
                logger.warning(f"⚠️ Failed to index enhanced event {event.id} in ChromaDB")
        except Exception as e:
            logger.error(f"❌ Error indexing enhanced event {event.id}: {e}")
        
        # Enhanced processing with media analysis
        if uploaded_urls:
            background_tasks.add_task(analyze_event_media, event.id, uploaded_urls)
        
        return {
            "success": True,
            "event_id": event.id,
            "message": "Enhanced event created successfully",
            "media_uploaded": len(uploaded_urls),
            "event": {
                "id": event.id,
                "title": event.content.title,
                "topic": event.topic.value,
                "severity": event.impact_analysis.severity.value,
                "media_count": len(uploaded_urls),
                "created_at": event.temporal_data.created_at.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error creating enhanced event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create enhanced event: {str(e)}")

@app.get("/events/search", tags=["Events"])
async def search_events(
    query: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 5,
    topic: Optional[EventTopic] = None,
    severity: Optional[EventSeverity] = None,
    max_results: int = 10
):
    """Search events using semantic similarity"""
    try:
        user_location = Coordinates(lat=lat, lng=lng) if lat and lng else None
        
        results = await db_manager.search_events_semantically(
            query=query,
            user_location=user_location,
            max_results=max_results
        )
        
        # Filter by topic and severity if specified
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})
            
            # Apply filters
            if topic and metadata.get("topic") != topic.value:
                continue
            if severity and metadata.get("severity") != severity.value:
                continue
                
            filtered_results.append({
                "event_id": result["event_id"],
                "title": result["document"].split(".")[0] if result["document"] else "Unknown",
                "similarity_score": result["similarity_score"],
                "topic": metadata.get("topic"),
                "severity": metadata.get("severity"),
                "location": {
                    "lat": metadata.get("latitude"),
                    "lng": metadata.get("longitude")
                },
                "distance_km": result.get("distance_km"),
                "created_at": metadata.get("created_at")
            })
        
        return {
            "success": True,
            "query": query,
            "total_results": len(filtered_results),
            "results": filtered_results[:max_results]
        }
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/events/nearby", tags=["Events"])
async def get_nearby_events(
    lat: float,
    lng: float,
    radius_km: float = 5,
    topic: Optional[EventTopic] = None,
    max_results: int = 20
):
    """Get events near a specific location"""
    try:
        # Use semantic search with location-based query
        location_query = f"events near location {lat},{lng}"
        user_location = Coordinates(lat=lat, lng=lng)
        
        results = await db_manager.search_events_semantically(
            query=location_query,
            user_location=user_location,
            max_results=max_results
        )
        
        nearby_events = []
        for result in results:
            if result.get("distance_km", float('inf')) <= radius_km:
                metadata = result.get("metadata", {})
                
                # Apply topic filter
                if topic and metadata.get("topic") != topic.value:
                    continue
                
                nearby_events.append({
                    "event_id": result["event_id"],
                    "topic": metadata.get("topic"),
                    "severity": metadata.get("severity"),
                    "distance_km": round(result.get("distance_km", 0), 2),
                    "confidence_score": metadata.get("confidence_score", 0),
                    "created_at": metadata.get("created_at"),
                    "location": {
                        "lat": metadata.get("latitude"),
                        "lng": metadata.get("longitude")
                    }
                })
        
        return {
            "success": True,
            "center_location": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "total_events": len(nearby_events),
            "events": nearby_events
        }
    except Exception as e:
        logger.error(f"Error getting nearby events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nearby events: {str(e)}")

# ============================================================================
# MEDIA MANAGEMENT ENDPOINTS  
# ============================================================================

@app.post("/media/upload", response_model=MediaUploadResponse, tags=["Media"])
async def upload_media(
    files: List[UploadFile] = File(...),
    user_id: str = Form("anonymous"),
    event_id: str = Form(None)
):
    """Upload multiple media files"""
    try:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files allowed")
        
        uploaded_files = []
        failed_files = []
        storage_urls = []
        
        for file in files:
            try:
                # Validate file
                if file.size > 50 * 1024 * 1024:  # 50MB limit
                    failed_files.append({
                        "filename": file.filename,
                        "error": "File too large (max 50MB)"
                    })
                    continue
                
                # Read file data
                file_data = await file.read()
                
                # Upload to storage
                storage_url = await storage_client.upload_media(
                    file_data,
                    file.filename,
                    file.content_type,
                    user_id,
                    event_id or f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                )
                
                if storage_url:
                    uploaded_files.append({
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "size_bytes": file.size,
                        "storage_url": storage_url
                    })
                    storage_urls.append(storage_url)
                else:
                    failed_files.append({
                        "filename": file.filename,
                        "error": "Upload failed"
                    })
                    
            except Exception as e:
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return MediaUploadResponse(
            success=len(uploaded_files) > 0,
            uploaded_files=uploaded_files,
            failed_files=failed_files,
            total_uploaded=len(uploaded_files),
            storage_urls=storage_urls
        )
        
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/media/analyze", response_model=MediaAnalysisResponse, tags=["Media"])
async def analyze_media(
    media_url: str,
    media_type: str = "image"
):
    """Analyze uploaded media using AI"""
    try:
        start_time = datetime.utcnow()
        
        # Perform comprehensive media analysis
        analysis = await enhanced_processor.analyze_media_comprehensive(media_url, media_type)
        
        if not analysis:
            raise HTTPException(status_code=400, detail="Failed to analyze media")
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return MediaAnalysisResponse(
            media_url=media_url,
            media_type=media_type,
            analysis_results={
                "description": analysis.gemini_description,
                "detected_objects": analysis.detected_objects,
                "visibility": analysis.visibility,
                "weather_impact": analysis.weather_impact
            },
            confidence_score=analysis.confidence_score,
            processing_time_ms=int(processing_time)
        )
        
    except Exception as e:
        logger.error(f"Error analyzing media: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/media/formats", tags=["Media"])
async def get_supported_formats():
    """Get supported media formats and limits"""
    try:
        formats = storage_client.get_supported_formats()
        return {
            "success": True,
            "formats": formats,
            "upload_endpoint": "/media/upload",
            "analysis_endpoint": "/media/analyze"
        }
    except Exception as e:
        logger.error(f"Error getting formats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get formats")

# ============================================================================
# CHAT AND CONVERSATION ENDPOINTS
# ============================================================================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_agent(chat_request: ChatRequest):
    """Chat with the City Pulse Agent"""
    try:
        user_message = chat_request.message.lower()
        response_text = ""
        suggestions = []
        referenced_events = []
        
        # Basic intent recognition
        if any(word in user_message for word in ["traffic", "jam", "congestion"]):
            response_text = "I can help you with traffic information. Let me search for current traffic conditions in your area."
            suggestions = ["Show traffic near me", "Alternative routes", "Report traffic issue"]
            
            # Search for traffic events
            if chat_request.location:
                traffic_events = await db_manager.search_events_semantically(
                    query="traffic congestion",
                    user_location=chat_request.location,
                    max_results=3
                )
                referenced_events = [event["event_id"] for event in traffic_events]
        
        elif any(word in user_message for word in ["flood", "water", "rain"]):
            response_text = "I can provide information about flooding and weather conditions. Are you experiencing waterlogging in your area?"
            suggestions = ["Report flooding", "Check weather alerts", "Safe routes"]
            
        elif any(word in user_message for word in ["power", "electricity", "outage"]):
            response_text = "I can help with power outage information. Let me check for electrical issues in your area."
            suggestions = ["Report power outage", "Check restoration time", "Emergency contacts"]
            
        else:
            response_text = "I'm here to help with city-related issues like traffic, infrastructure problems, weather conditions, and safety concerns. What can I assist you with?"
            suggestions = ["Report an incident", "Search nearby events", "Get traffic updates", "Check weather alerts"]
        
        return ChatResponse(
            message_id=f"msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            response=response_text,
            suggestions=suggestions,
            referenced_events=referenced_events
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/chat/enhanced", response_model=EnhancedChatResponse, tags=["Chat"])
async def enhanced_chat_with_media(chat_request: ChatWithMediaRequest):
    """Enhanced chat with media context support"""
    try:
        response_text = f"I received your message: '{chat_request.message}'"
        media_insights = None
        
        # If media references provided, analyze them
        if chat_request.media_references and chat_request.include_media_analysis:
            media_insights = {}
            for media_url in chat_request.media_references[:3]:  # Limit to 3 for demo
                media_type = "video" if media_url.endswith(('.mp4', '.avi', '.mov')) else "image"
                analysis = await enhanced_processor.analyze_media_comprehensive(media_url, media_type)
                
                if analysis:
                    media_insights[media_url] = {
                        "description": analysis.gemini_description,
                        "objects": analysis.detected_objects[:5],
                        "confidence": analysis.confidence_score
                    }
        
        return EnhancedChatResponse(
            message_id=f"enhanced_msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            response=response_text,
            suggestions=["Tell me more", "Show similar incidents", "Get help"],
            referenced_events=[],
            media_insights=media_insights
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced chat: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced chat failed: {str(e)}")

# ============================================================================
# ANALYTICS AND INSIGHTS ENDPOINTS
# ============================================================================

@app.get("/analytics/overview", tags=["Analytics"])
async def get_analytics_overview(
    timeframe: str = "24h",  # 1h, 24h, 7d, 30d
    location_filter: Optional[str] = None
):
    """Get system analytics overview"""
    try:
        stats = await db_manager.get_system_stats()
        
        # Mock analytics data - in production, calculate from real data
        overview = {
            "timeframe": timeframe,
            "total_events": stats.get("chroma_db", {}).get("events_count", 0),
            "active_users": stats.get("chroma_db", {}).get("users_count", 0),
            "events_by_topic": {
                "traffic": 45,
                "infrastructure": 23,
                "weather": 12,
                "events": 8,
                "safety": 5
            },
            "severity_distribution": {
                "low": 35,
                "medium": 40,
                "high": 20,
                "critical": 5
            },
            "top_locations": [
                {"area": "HSR Layout", "event_count": 15},
                {"area": "Koramangala", "event_count": 12},
                {"area": "Whitefield", "event_count": 10},
                {"area": "Electronic City", "event_count": 8},
                {"area": "Indiranagar", "event_count": 7}
            ],
            "response_metrics": {
                "avg_processing_time_ms": 850,
                "avg_search_time_ms": 120,
                "system_uptime": "99.8%"
            }
        }
        
        return {
            "success": True,
            "analytics": overview,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

@app.get("/analytics/heatmap", tags=["Analytics"])
async def get_incident_heatmap(
    topic: Optional[EventTopic] = None,
    severity: Optional[EventSeverity] = None,
    timeframe: str = "24h"
):
    """Get incident heatmap data for visualization"""
    try:
        # Mock heatmap data - in production, aggregate real incident locations
        heatmap_points = [
            {"lat": 12.9716, "lng": 77.5946, "intensity": 0.8, "count": 12},  # MG Road
            {"lat": 12.9352, "lng": 77.6245, "intensity": 0.6, "count": 8},   # Koramangala
            {"lat": 12.9116, "lng": 77.6370, "intensity": 0.7, "count": 10},  # HSR Layout
            {"lat": 12.9698, "lng": 77.7499, "intensity": 0.5, "count": 6},   # Whitefield
            {"lat": 12.8456, "lng": 77.6603, "intensity": 0.4, "count": 5},   # Electronic City
        ]
        
        return {
            "success": True,
            "heatmap_data": heatmap_points,
            "filters": {
                "topic": topic.value if topic else "all",
                "severity": severity.value if severity else "all",
                "timeframe": timeframe
            },
            "total_points": len(heatmap_points)
        }
        
    except Exception as e:
        logger.error(f"Error getting heatmap: {e}")
        raise HTTPException(status_code=500, detail="Failed to get heatmap data")

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def post_process_event(event_id: str):
    """Background task for additional event processing"""
    try:
        logger.info(f"Post-processing event: {event_id}")
        await asyncio.sleep(1)  # Simulate processing time
        logger.info(f"Post-processing completed for event: {event_id}")
        logger.warning(f"⚠️  Event {event_id} NOT indexed in ChromaDB - search will not find it!")
        
    except Exception as e:
        logger.error(f"Error in post-processing event {event_id}: {e}")

async def analyze_event_media(event_id: str, media_urls: List[str]):
    """Background task for analyzing event media"""
    try:
        logger.info(f"Analyzing media for event: {event_id}")
        
        for url in media_urls:
            media_type = "video" if url.endswith(('.mp4', '.avi', '.mov')) else "image"
            analysis = await enhanced_processor.analyze_media_comprehensive(url, media_type)
            
            if analysis:
                logger.info(f"Media analysis completed: {url}")
            else:
                logger.warning(f"Media analysis failed: {url}")
        
        logger.info(f"Media analysis completed for event: {event_id}")
    except Exception as e:
        logger.error(f"Error analyzing media for event {event_id}: {e}")

# ============================================================================
# DEMO AND TESTING ENDPOINTS
# ============================================================================

@app.post("/demo/populate", tags=["Demo"])
async def populate_demo_data(
    events_count: int = 50,
    users_count: int = 10
):
    """Populate database with demo data for testing"""
    try:
        success = await db_manager.populate_mock_data(events_count, users_count)
        
        if success:
            return {
                "success": True,
                "message": f"Demo data populated: {events_count} events, {users_count} users",
                "events_count": events_count,
                "users_count": users_count
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to populate demo data")
            
    except Exception as e:
        logger.error(f"Error populating demo data: {e}")
        raise HTTPException(status_code=500, detail=f"Demo data population failed: {str(e)}")

@app.get("/demo/test-scenarios", tags=["Demo"])
async def get_test_scenarios():
    """Get predefined test scenarios for demo"""
    scenarios = [
        {
            "id": "traffic_accident",
            "title": "Traffic Accident Demo",
            "description": "Multi-vehicle collision with photo evidence",
            "location": {"lat": 12.9716, "lng": 77.5946},
            "topic": "traffic",
            "severity": "high",
            "demo_query": "traffic accident ORR junction"
        },
        {
            "id": "flooding_report",
            "title": "Flooding Incident Demo", 
            "description": "Heavy waterlogging with video documentation",
            "location": {"lat": 12.9352, "lng": 77.6245},
            "topic": "weather",
            "severity": "critical",
            "demo_query": "flooding waterlogging Koramangala"
        },
        {
            "id": "power_outage",
            "title": "Power Outage Demo",
            "description": "Electricity supply disruption in residential area",
            "location": {"lat": 12.9116, "lng": 77.6370},
            "topic": "infrastructure", 
            "severity": "medium",
            "demo_query": "power outage HSR Layout"
        }
    ]
    
    return {
        "success": True,
        "scenarios": scenarios,
        "usage": "Use these scenarios to test different API endpoints"
    }

# ============================================================================
# DASHBOARD MODELS AND HELPERS
# ============================================================================

class DashboardCard(BaseModel):
    """Dashboard card model"""
    id: str
    type: str  # infrastructure_alert, traffic_alert, weather_warning, event_recommendation
    priority: str  # low, medium, high, critical
    title: str
    summary: str
    action: str
    confidence: float
    expires_at: str
    created_at: str
    user_id: str
    event_id: Optional[str] = None
    distance_km: Optional[float] = None
    expandable: Optional[bool] = False
    expansion_url: Optional[str] = None
    synthesis_meta: Optional[Dict[str, Any]] = None
    expanded_details: Optional[Dict[str, Any]] = None

async def get_cached_dashboard_cards(user_id: str, lat: float = None, lng: float = None):
    """Get dashboard cards with simple caching"""
    cache_key = f"{user_id}_{lat}_{lng}"
    current_time = time.time()
    
    # Check cache
    if cache_key in dashboard_cache:
        cached_data, timestamp = dashboard_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION:
            logger.info(f"Returning cached dashboard for {user_id}")
            return cached_data
    
    # Generate fresh data
    cards = await generate_user_dashboard_cards(user_id, lat, lng)
    
    # Cache it
    dashboard_cache[cache_key] = (cards, current_time)
    
    # Clean old cache entries (simple cleanup)
    if len(dashboard_cache) > 100:
        oldest_keys = sorted(dashboard_cache.keys(), key=lambda k: dashboard_cache[k][1])[:20]
        for old_key in oldest_keys:
            del dashboard_cache[old_key]
    
    return cards

async def synthesize_dashboard_cards(raw_events: List[Dict], user_id: str, user_location: Coordinates = None) -> List[DashboardCard]:
    """AI-powered synthesis of multiple events into intelligent summary cards"""
    
    if not raw_events:
        return []
    
    try:
        # Group events by topic for intelligent synthesis
        events_by_topic = {}
        for event in raw_events:
            topic = event.get("metadata", {}).get("topic", "general")
            if topic not in events_by_topic:
                events_by_topic[topic] = []
            events_by_topic[topic].append(event)
        
        synthesized_cards = []
        
        for topic, topic_events in events_by_topic.items():
            if len(topic_events) == 1:
                # Single event - create individual card
                event = topic_events[0]
                card = await create_individual_card(event, user_id)
                synthesized_cards.append(card)
            else:
                # Multiple events - synthesize using AI
                synthesized_card = await create_synthesized_card(topic, topic_events, user_id, user_location)
                synthesized_cards.append(synthesized_card)
        
        return synthesized_cards
        
    except Exception as e:
        logger.error(f"Error synthesizing dashboard cards: {e}")
        return []

async def create_synthesized_card(topic: str, events: List[Dict], user_id: str, user_location: Coordinates = None) -> DashboardCard:
    """Create AI-synthesized card from multiple events of the same topic"""
    
    try:
        # Prepare event details for AI synthesis
        event_summaries = []
        total_distance = 0
        max_severity = "low"
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        
        for event in events:
            metadata = event.get("metadata", {})
            distance = event.get("distance_km", 0)
            severity = metadata.get("severity", "low")
            
            # Track highest severity
            if severity_order.get(severity, 0) > severity_order.get(max_severity, 0):
                max_severity = severity
            
            total_distance += distance
            
            distance_text = f"{distance:.1f}km" if distance >= 1 else f"{int(distance*1000)}m"
            event_summaries.append({
                "title": event["document"][:50] + "..." if len(event["document"]) > 50 else event["document"],
                "distance": distance_text,
                "severity": severity,
                "similarity": event.get("similarity_score", 0)
            })
        
        avg_distance = total_distance / len(events)
        
        # Create AI prompt for synthesis
        synthesis_prompt = f"""
        You are an AI assistant helping to create a smart city dashboard card. 
        
        Synthesize these {len(events)} {topic} incidents into ONE intelligent summary card for a user in Bengaluru:
        
        Events to synthesize:
        {json.dumps(event_summaries, indent=2)}
        
        User context:
        - Location: HSR Layout area, Bengaluru  
        - Average distance to incidents: {avg_distance:.1f}km
        - Highest severity: {max_severity}
        
        Create a synthesis that:
        1. Summarizes the overall {topic} situation in their area
        2. Highlights the most important impact to the user
        3. Provides ONE clear actionable recommendation
        4. Mentions the number of incidents and closest distance
        5. Uses a conversational, helpful tone
        
        Respond in JSON format:
        {{
            "title": "Concise title (max 60 chars)",
            "summary": "2-3 sentence synthesis of the situation and impact", 
            "action": "Single clear recommendation",
            "key_insight": "Most important thing the user should know"
        }}
        
        Examples:
        - For traffic: "3 Traffic Incidents in Your Area" 
        - For infrastructure: "Infrastructure Issues Affecting Your Area"
        - For weather: "Weather Conditions Impacting You"
        """
        
        # Get AI synthesis
        try:
            response = enhanced_subcategory_processor.model.generate_content(synthesis_prompt)
            ai_synthesis = json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"Error creating synthesized card: {e}")
            # Fallback if AI response isn't proper JSON
            ai_synthesis = {
                "title": f"{len(events)} {topic.title()} Incidents in Your Area",
                "summary": f"Multiple {topic} incidents detected within {avg_distance:.1f}km of your location. Highest severity: {max_severity}.",
                "action": f"Monitor {topic} conditions and plan accordingly.",
                "key_insight": f"Stay informed about ongoing {topic} situations."
            }
        
        # Determine card priority based on synthesis
        if max_severity == "critical" or len(events) >= 3:
            priority = "high"
        elif max_severity == "high" or len(events) >= 2:
            priority = "medium"
        else:
            priority = "low"
        
        # Create the synthesized card
        synthesized_card = DashboardCard(
            id=f"synthesis_{topic}_{user_id}",
            type=f"{topic}_synthesis",
            priority=priority,
            title=ai_synthesis["title"],
            summary=ai_synthesis["summary"],
            action=ai_synthesis["action"],
            confidence=0.9,  # High confidence in AI synthesis
            expires_at=(datetime.utcnow() + timedelta(hours=12)).isoformat(),
            created_at=datetime.utcnow().isoformat(),
            user_id=user_id,
            event_id=f"synthesis_{len(events)}_events",
            distance_km=round(avg_distance, 1),
            expandable=True,
            synthesis_meta={
                "event_count": len(events),
                "topic": topic,
                "max_severity": max_severity,
                "avg_distance_km": round(avg_distance, 1),
                "key_insight": ai_synthesis["key_insight"],
                "individual_events": event_summaries
            }
        )
        
        return synthesized_card
        
    except Exception as e:
        logger.error(f"Error creating synthesized card: {e}")
        # Return fallback card
        return DashboardCard(
            id=f"fallback_{topic}_{user_id}",
            type=f"{topic}_alert",
            priority="medium",
            title=f"{len(events)} {topic.title()} Incidents",
            summary=f"Multiple {topic} incidents in your area require attention.",
            action="Check individual incidents for details.",
            confidence=0.5,
            expires_at=(datetime.utcnow() + timedelta(hours=6)).isoformat(),
            created_at=datetime.utcnow().isoformat(),
            user_id=user_id,
            distance_km=0
        )

async def create_individual_card(event: Dict, user_id: str) -> DashboardCard:
    """Create card for single event"""
    metadata = event.get("metadata", {})
    distance = event.get("distance_km", 0)
    topic = metadata.get("topic", "")
    severity = metadata.get("severity", "medium")
    
    # Create personalized message
    distance_text = f"{distance:.1f}km away" if distance >= 1 else f"{int(distance*1000)}m away"
    
    if topic == "infrastructure" and "water" in event["document"].lower():
        summary = f"Water infrastructure issue {distance_text}. This may affect your water supply."
        action = "Check water pressure and consider storing water if needed."
    elif topic == "traffic":
        summary = f"Traffic incident {distance_text}. May impact your commute."
        action = "Consider alternative routes or adjust departure time."
    else:
        summary = f"{topic.title()} incident {distance_text}. Severity: {severity}"
        action = "Stay informed and take necessary precautions."
    
    return DashboardCard(
        id=f"event_{event['event_id']}",
        type=f"{topic}_alert",
        priority=severity,
        title=event["document"][:60] + "..." if len(event["document"]) > 60 else event["document"],
        summary=summary,
        action=action,
        confidence=event.get("similarity_score", 0.7),
        expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
        created_at=datetime.utcnow().isoformat(),
        user_id=user_id,
        event_id=event["event_id"],
        distance_km=distance
    )

async def generate_user_dashboard_cards(user_id: str, lat: float = None, lng: float = None) -> List[DashboardCard]:
    """Generate personalized dashboard cards for user based on real events and context"""
    cards = []
    
    try:
        # If location provided, find nearby events
        if lat and lng:
            user_location = Coordinates(lat=lat, lng=lng)
            
            # Search for nearby events using ChromaDB (same as agent)
            nearby_events = await db_manager.search_events_semantically(
                query="infrastructure traffic safety weather incidents",
                user_location=user_location,
                max_results=15
            )
            
            # Filter events within 5km
            relevant_events = [
                event for event in nearby_events 
                if event.get("distance_km", 0) <= 5
            ]
            
            if relevant_events:
                # Use AI synthesis to create intelligent summary cards
                cards = await synthesize_dashboard_cards(relevant_events, user_id, user_location)
            
        # Add default cards if no nearby events
        if not cards:
            # General status cards
            cards.extend([
                DashboardCard(
                    id=f"weather_{user_id}",
                    type="weather_status",
                    priority="low",
                    title="All Clear in Your Area",
                    summary="No active incidents detected. Weather is pleasant, traffic is flowing normally.",
                    action="Enjoy your day! We'll notify you of any updates.",
                    confidence=0.9,
                    expires_at=(datetime.utcnow() + timedelta(hours=6)).isoformat(),
                    created_at=datetime.utcnow().isoformat(),
                    user_id=user_id
                )
            ])
        
        # Sort cards by priority and distance
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        cards.sort(key=lambda x: (priority_order.get(x.priority, 3), x.distance_km or 999))
        
        return cards[:4]  # Return top 4 synthesized cards
        
    except Exception as e:
        logger.error(f"Error generating dashboard cards: {e}")
        # Return fallback card
        return [
            DashboardCard(
                id=f"error_{user_id}",
                type="system_status",
                priority="low",
                title="Dashboard Loading",
                summary="Loading personalized updates for your area...",
                action="Please refresh if this persists.",
                confidence=1.0,
                expires_at=(datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                created_at=datetime.utcnow().isoformat(),
                user_id=user_id
            )
        ]

# ============================================================================
# ON-DEMAND DASHBOARD ENDPOINTS (NO STREAMING)
# ============================================================================

@app.get("/dashboard/{user_id}")
async def get_user_dashboard(user_id: str, lat: Optional[float] = None, lng: Optional[float] = None):
    """Get current dashboard state with optional caching"""
    try:
        # Add simple timestamp-based caching (5-minute buckets)
        current_time = datetime.utcnow()
        cache_bucket = int(current_time.timestamp() // 300)  # 5-minute cache
        
        # Get cached or fresh cards
        cards = await get_cached_dashboard_cards(user_id, lat, lng)
        
        # Add expansion info to synthesized cards
        response_cards = []
        for card in cards:
            card_dict = card.dict()
            if card.synthesis_meta:
                card_dict["expandable"] = True
                card_dict["expansion_url"] = f"/dashboard/{user_id}/expand/{card.id}?lat={lat}&lng={lng}"
            else:
                card_dict["expandable"] = False
            response_cards.append(card_dict)
        
        return {
            "success": True,
            "cards": response_cards,
            "total_cards": len(cards),
            "generated_at": current_time.isoformat(),
            "user_id": user_id,
            "update_type": "on_demand",
            "cache_bucket": cache_bucket,
            "ai_synthesis": "enabled"
        }
    except Exception as e:
        logger.error(f"Error generating dashboard for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")

@app.post("/dashboard/{user_id}/refresh")
async def refresh_dashboard(user_id: str, lat: Optional[float] = None, lng: Optional[float] = None):
    """Force refresh dashboard with fresh AI synthesis"""
    try:
        logger.info(f"Manual dashboard refresh requested for user {user_id}")
        
        # Clear cache for this user
        cache_key = f"{user_id}_{lat}_{lng}"
        if cache_key in dashboard_cache:
            del dashboard_cache[cache_key]
        
        # Always generate fresh content (bypass any caching)
        cards = await generate_user_dashboard_cards(user_id, lat, lng)
        
        response_cards = []
        for card in cards:
            card_dict = card.dict()
            if card.synthesis_meta:
                card_dict["expandable"] = True
                card_dict["expansion_url"] = f"/dashboard/{user_id}/expand/{card.id}?lat={lat}&lng={lng}"
            response_cards.append(card_dict)
        
        return {
            "success": True,
            "cards": response_cards,
            "total_cards": len(cards),
            "refreshed_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "update_type": "manual_refresh"
        }
    except Exception as e:
        logger.error(f"Error refreshing dashboard for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh dashboard: {str(e)}")

@app.get("/dashboard/{user_id}/status")
async def get_dashboard_status(user_id: str, lat: Optional[float] = None, lng: Optional[float] = None):
    """Quick dashboard status without AI synthesis"""
    try:
        if lat and lng:
            user_location = Coordinates(lat=lat, lng=lng)
            
            # Get raw events without AI synthesis
            nearby_events = await db_manager.search_events_semantically(
                query="infrastructure traffic safety weather incidents",
                user_location=user_location,
                max_results=10
            )
            
            # Simple count-based status (no AI)
            relevant_events = [e for e in nearby_events if e.get("distance_km", 0) <= 5]
            
            status = {
                "total_nearby_events": len(relevant_events),
                "high_priority_events": len([e for e in relevant_events if e.get("metadata", {}).get("severity") in ["high", "critical"]]),
                "topics_with_events": list(set([e.get("metadata", {}).get("topic") for e in relevant_events if e.get("metadata", {}).get("topic")])),
                "last_updated": datetime.utcnow().isoformat(),
                "needs_attention": len([e for e in relevant_events if e.get("metadata", {}).get("severity") in ["high", "critical"]]) > 0
            }
        else:
            status = {
                "total_nearby_events": 0,
                "high_priority_events": 0,
                "topics_with_events": [],
                "last_updated": datetime.utcnow().isoformat(),
                "needs_attention": False,
                "message": "Location required for status check"
            }
        
        return {
            "success": True,
            "status": status,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error getting dashboard status for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@app.get("/dashboard/{user_id}/expand/{card_id}")
async def expand_dashboard_card(user_id: str, card_id: str, lat: Optional[float] = None, lng: Optional[float] = None):
    """Expand a synthesized dashboard card to show individual events"""
    try:
        # Extract topic from card_id (format: synthesis_traffic_user_id)
        if not card_id.startswith("synthesis_"):
            raise HTTPException(status_code=400, detail="Card is not expandable")
        
        parts = card_id.split("_")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid card ID format")
        
        topic = parts[1]  # Extract topic (traffic, infrastructure, etc.)
        
        if lat and lng:
            user_location = Coordinates(lat=lat, lng=lng)
            
            # Get events for this specific topic
            nearby_events = await db_manager.search_events_semantically(
                query=f"{topic} incidents events",
                user_location=user_location,
                max_results=20
            )
            
            # Filter for the specific topic and within 5km
            topic_events = [
                event for event in nearby_events 
                if (event.get("metadata", {}).get("topic") == topic and 
                    event.get("distance_km", 0) <= 5)
            ]
            
            # Create individual detailed cards
            detailed_cards = []
            for event in topic_events:
                detailed_card = await create_individual_card(event, user_id)
                
                # Add extra detail for expansion
                detailed_card.expanded_details = {
                    "full_description": event["document"],
                    "event_id": event["event_id"],
                    "similarity_score": round(event.get("similarity_score", 0) * 100),
                    "created_timestamp": event.get("metadata", {}).get("created_at"),
                    "severity": event.get("metadata", {}).get("severity"),
                    "exact_distance": f"{event.get('distance_km', 0):.2f} km"
                }
                
                detailed_cards.append(detailed_card)
            
            return {
                "success": True,
                "expanded_topic": topic,
                "total_events": len(detailed_cards),
                "user_id": user_id,
                "individual_events": [card.dict() for card in detailed_cards],
                "summary": f"Showing {len(detailed_cards)} individual {topic} incidents in your area",
                "generated_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Location required for expansion")
            
    except Exception as e:
        logger.error(f"Error expanding dashboard card {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to expand card: {str(e)}")

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Import and add agentic layer router
from data.api.agentic_endpoints import router as agentic_router
app.include_router(agentic_router)
# Add Google ADK router after agentic router
from data.api.google_adk_endpoints import router as adk_router
app.include_router(adk_router)