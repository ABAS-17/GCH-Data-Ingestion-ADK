# data/api/subcategory_endpoints.py
"""
API endpoints for subcategory management
Provides REST API for subcategory CRUD, analytics, and classification
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models.schemas import EventTopic
from data.models.subcategory_schemas import (
    Subcategory, CreateSubcategoryRequest, UpdateSubcategoryRequest,
    SubcategorySearchRequest, SubcategoryResponse, SubcategoryListResponse,
    ClassificationResponse, SubcategoryClassificationRequest, ClassificationContext
)
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
from data.database.simple_firestore_client import simple_firestore_client

logger = logging.getLogger(__name__)

# Create router for subcategory endpoints
router = APIRouter(prefix="/subcategories", tags=["Subcategories"])


# ============================================================================
# SUBCATEGORY CRUD ENDPOINTS
# ============================================================================

@router.get("/", response_model=SubcategoryListResponse)
async def get_subcategories(
    topic: Optional[EventTopic] = Query(None, description="Filter by topic"),
    status: Optional[str] = Query(None, description="Filter by status"),
    include_usage_stats: bool = Query(False, description="Include usage statistics"),
    max_results: int = Query(100, ge=1, le=500, description="Maximum results to return")
):
    """Get all subcategories with optional filtering"""
    try:
        if topic:
            # Get subcategories for specific topic
            subcategories = await enhanced_subcategory_processor.get_available_subcategories(topic)
            
            # Filter by status if provided
            if status:
                subcategories = [sc for sc in subcategories if sc.get("status") == status]
            
            # Convert to Subcategory objects for response
            subcategory_objects = []
            for sc_data in subcategories:
                try:
                    subcategory = await simple_firestore_client.get_subcategory(sc_data["id"])
                    if subcategory:
                        subcategory_objects.append(subcategory)
                except Exception as e:
                    logger.warning(f"Could not fetch subcategory {sc_data['id']}: {e}")
            
            return SubcategoryListResponse(
                success=True,
                subcategories=subcategory_objects[:max_results],
                total_count=len(subcategory_objects),
                filtered_count=len(subcategory_objects)
            )
        else:
            # Get all subcategories across all topics
            all_subcategories = []
            for topic_enum in EventTopic:
                topic_subcategories = await simple_firestore_client.get_subcategories_by_topic(topic_enum)
                all_subcategories.extend(topic_subcategories)
            
            # Apply status filter if provided
            if status:
                all_subcategories = [sc for sc in all_subcategories if sc.status.value == status]
            
            return SubcategoryListResponse(
                success=True,
                subcategories=all_subcategories[:max_results],
                total_count=len(all_subcategories),
                filtered_count=len(all_subcategories)
            )
    
    except Exception as e:
        logger.error(f"Error getting subcategories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subcategories: {str(e)}")


@router.post("/classify", response_model=ClassificationResponse)
async def classify_subcategory(
    request: dict
):
    """Classify subcategory for given event details"""
    try:
        topic = EventTopic(request.get("topic"))
        title = request.get("title")
        description = request.get("description")
        force_create_new = request.get("force_create_new", False)
        min_confidence = request.get("min_confidence", 0.7)
        location_lat = request.get("location_lat")
        location_lng = request.get("location_lng")
        address = request.get("address")
        
        # Build classification context
        context = ClassificationContext(
            event_title=title,
            event_description=description
        )
        
        # Add location context if provided
        if location_lat and location_lng:
            context.location_context = {
                "coordinates": {"lat": location_lat, "lng": location_lng},
                "address": address
            }
        
        # Create classification request
        classification_request = SubcategoryClassificationRequest(
            topic=topic,
            context=context,
            force_create_new=force_create_new,
            min_confidence_threshold=min_confidence
        )
        
        # Perform classification
        result = await enhanced_subcategory_processor.classifier.classify_subcategory(
            classification_request
        )
        
        # Get the subcategory object
        subcategory = None
        if result.new_subcategory_id:
            subcategory = await simple_firestore_client.get_subcategory(result.new_subcategory_id)
        else:
            # Find existing subcategory
            subcategory = await simple_firestore_client._find_subcategory_by_name_or_alias(
                topic, result.subcategory_name
            )
        
        return ClassificationResponse(
            success=True,
            result=result,
            subcategory=subcategory,
            message="Classification completed successfully"
        )
    
    except Exception as e:
        logger.error(f"Error in subcategory classification: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.get("/health")
async def subcategory_health_check():
    """Health check for subcategory management system"""
    try:
        health_status = await enhanced_subcategory_processor.health_check()
        
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
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
