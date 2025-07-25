# data/processors/enhanced_subcategory_processor.py
"""
Enhanced event processor with integrated subcategory classification
Replaces the basic sub_topic handling with AI-powered dynamic subcategory management
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.processors.event_processor import EventProcessor
from data.processors.subcategory_classifier import subcategory_classifier
from data.models.schemas import (
    Event, EventContent, EventTopic, EventSeverity, EventSource,
    GeographicData, LocationData, Coordinates, ImpactAnalysis,
    EventMedia, MediaAnalysis, TemporalData, EventCreateRequest
)
from data.models.subcategory_schemas import (
    ClassificationContext, SubcategoryClassificationRequest, ClassificationResult
)
from data.database.simple_firestore_client import simple_firestore_client

logger = logging.getLogger(__name__)


class EnhancedSubcategoryProcessor(EventProcessor):
    """Enhanced event processor with intelligent subcategory management"""
    
    def __init__(self):
        super().__init__()
        self.classifier = subcategory_classifier
        self.firestore_client = simple_firestore_client
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the enhanced processor"""
        try:
            if self._initialized:
                return True
            
            # Initialize Firestore client
            await self.firestore_client.initialize()
            
            # Initialize predefined subcategories if needed
            await self.classifier.initialize_predefined_subcategories()
            
            self._initialized = True
            logger.info("✅ Enhanced subcategory processor initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize enhanced processor: {e}")
            return False
    
    # =========================================================================
    # ENHANCED EVENT PROCESSING WITH SMART SUBCATEGORIES
    # =========================================================================
    
    async def process_user_report(self, event_request: EventCreateRequest, 
                                user_id: str = "anonymous") -> Event:
        """Process user report with intelligent subcategory classification"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Step 1: Build classification context
            # Handle location properly whether it's Coordinates object or dict
            if hasattr(event_request.location, 'lat'):
                # It's a Coordinates object
                lat = event_request.location.lat
                lng = event_request.location.lng
            else:
                # It's a dictionary
                lat = event_request.location['lat']
                lng = event_request.location['lng']
                
            context = ClassificationContext(
                event_title=event_request.title,
                event_description=event_request.description,
                location_context={
                    "coordinates": {
                        "lat": lat,
                        "lng": lng
                    },
                    "address": event_request.address
                }
            )
            
            # Add media analysis if available
            if event_request.media_urls:
                media_analysis = await self._analyze_event_media(event_request.media_urls)
                if media_analysis:
                    context.media_analysis = media_analysis
            
            # Step 2: Classify subcategory using AI
            classification_request = SubcategoryClassificationRequest(
                topic=event_request.topic,
                context=context,
                min_confidence_threshold=0.6
            )
            
            classification_result = await self.classifier.classify_subcategory(classification_request)
            
            # Step 3: Process the event with classified subcategory
            event = await self._create_event_with_subcategory(
                event_request, classification_result, user_id
            )
            
            logger.info(f"✅ Processed user report with subcategory: {classification_result.subcategory_name}")
            return event
            
        except Exception as e:
            logger.error(f"Error processing user report: {e}")
            # Fallback to basic processing
            return await self._create_fallback_event(event_request, user_id)
    
    async def process_ai_generated_event(self, event_data: Dict[str, Any]) -> Event:
        """Process AI-generated event from external feeds"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Extract basic event information
            topic = EventTopic(event_data.get("topic", "traffic"))
            title = event_data.get("title", "AI Generated Event")
            description = event_data.get("description", "")
            
            # Build classification context
            context = ClassificationContext(
                event_title=title,
                event_description=description,
                location_context=event_data.get("location_context"),
                user_context={"source": "ai_feed"}
            )
            
            # Classify subcategory
            classification_request = SubcategoryClassificationRequest(
                topic=topic,
                context=context,
                min_confidence_threshold=0.7  # Higher threshold for AI-generated
            )
            
            classification_result = await self.classifier.classify_subcategory(classification_request)
            
            # Create event with classified subcategory
            event = await self._create_ai_event_with_subcategory(
                event_data, classification_result
            )
            
            logger.info(f"✅ Processed AI event with subcategory: {classification_result.subcategory_name}")
            return event
            
        except Exception as e:
            logger.error(f"Error processing AI-generated event: {e}")
            raise
    
    async def _create_event_with_subcategory(self, event_request: EventCreateRequest,
                                           classification_result: ClassificationResult,
                                           user_id: str) -> Event:
        """Create event with properly classified subcategory"""
        try:
            # Handle location properly whether it's Coordinates object or dict
            if hasattr(event_request.location, 'lat'):
                # It's a Coordinates object
                lat = event_request.location.lat
                lng = event_request.location.lng
            else:
                # It's a dictionary
                lat = event_request.location['lat']
                lng = event_request.location['lng']
                
            # Create location data
            location_data = LocationData(
                lat=lat,
                lng=lng,
                timestamp=datetime.utcnow(),
                address=event_request.address
            )
            
            geographic_data = GeographicData(location=location_data)
            
            # Create event content
            content = EventContent(
                title=event_request.title,
                description=event_request.description,
                ai_summary=classification_result.reasoning
            )
            
            # Analyze impact and severity
            impact_analysis = await self._analyze_impact_with_subcategory(
                event_request, classification_result
            )
            
            # Create media analysis if URLs provided
            media = EventMedia()
            if event_request.media_urls:
                media.images = [url for url in event_request.media_urls if self._is_image_url(url)]
                media.videos = [url for url in event_request.media_urls if self._is_video_url(url)]
                
                # Analyze first media file
                if event_request.media_urls:
                    media_analysis = await self.analyze_media(event_request.media_urls[0])
                    if media_analysis:
                        media.analyzed_content = media_analysis
            
            # Create the event
            event = Event(
                topic=event_request.topic,
                sub_topic=classification_result.subcategory_name,  # Use classified subcategory
                content=content,
                geographic_data=geographic_data,
                impact_analysis=impact_analysis,
                media=media,
                source=EventSource.CITIZEN_REPORT,
                metadata={
                    "user_id": user_id,
                    "classification_confidence": classification_result.confidence_score,
                    "is_new_subcategory": classification_result.is_new_subcategory,
                    "alternative_subcategories": classification_result.alternative_suggestions,
                    "classification_reasoning": classification_result.reasoning
                }
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating event with subcategory: {e}")
            raise
    
    async def _create_ai_event_with_subcategory(self, event_data: Dict[str, Any],
                                              classification_result: ClassificationResult) -> Event:
        """Create AI-generated event with classified subcategory"""
        try:
            # Extract location data
            location_info = event_data.get("location", {})
            location_data = LocationData(
                lat=location_info.get("lat", 12.9716),
                lng=location_info.get("lng", 77.5946),
                timestamp=datetime.utcnow(),
                address=location_info.get("address")
            )
            
            geographic_data = GeographicData(location=location_data)
            
            # Create content
            content = EventContent(
                title=event_data.get("title", "AI Generated Event"),
                description=event_data.get("description", ""),
                ai_summary=classification_result.reasoning
            )
            
            # Determine severity
            severity = EventSeverity(event_data.get("severity", "medium"))
            
            # Create impact analysis
            impact_analysis = ImpactAnalysis(
                severity=severity,
                confidence_score=classification_result.confidence_score,
                affected_users_estimated=event_data.get("affected_users", 100)
            )
            
            # Create the event
            event = Event(
                topic=EventTopic(event_data.get("topic")),
                sub_topic=classification_result.subcategory_name,
                content=content,
                geographic_data=geographic_data,
                impact_analysis=impact_analysis,
                source=EventSource.API_FEED,
                metadata={
                    "source_feed": event_data.get("source", "unknown"),
                    "classification_confidence": classification_result.confidence_score,
                    "is_new_subcategory": classification_result.is_new_subcategory,
                    "ai_generated": True
                }
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating AI event with subcategory: {e}")
            raise
    
    async def _analyze_impact_with_subcategory(self, event_request: EventCreateRequest,
                                             classification_result: ClassificationResult) -> ImpactAnalysis:
        """Analyze impact considering the classified subcategory"""
        try:
            base_severity = event_request.severity
            
            # Adjust severity based on subcategory and confidence
            subcategory_severity_map = {
                # High-impact subcategories
                "accident": EventSeverity.HIGH,
                "fire": EventSeverity.CRITICAL,
                "flood": EventSeverity.HIGH,
                "power_outage": EventSeverity.MEDIUM,
                
                # Medium-impact subcategories
                "congestion": EventSeverity.MEDIUM,
                "construction": EventSeverity.LOW,
                "rain": EventSeverity.LOW,
                "cultural": EventSeverity.LOW,
                
                # Default
                "general": base_severity
            }
            
            suggested_severity = subcategory_severity_map.get(
                classification_result.subcategory_name, base_severity
            )
            
            # Use higher of user-provided or AI-suggested severity
            final_severity = max(base_severity, suggested_severity, key=lambda x: x.value)
            
            # Adjust confidence based on classification confidence
            confidence_score = min(0.95, classification_result.confidence_score + 0.1)
            
            return ImpactAnalysis(
                severity=final_severity,
                confidence_score=confidence_score,
                affected_users_estimated=self._estimate_affected_users(
                    classification_result.subcategory_name, final_severity
                )
            )
            
        except Exception as e:
            logger.error(f"Error analyzing impact: {e}")
            # Return default impact analysis
            return ImpactAnalysis(
                severity=event_request.severity,
                confidence_score=0.7,
                affected_users_estimated=50
            )
    
    def _estimate_affected_users(self, subcategory: str, severity: EventSeverity) -> int:
        """Estimate affected users based on subcategory and severity"""
        base_estimates = {
            "accident": 200,
            "congestion": 500,
            "power_outage": 1000,
            "flood": 2000,
            "fire": 100,
            "construction": 300,
            "general": 50
        }
        
        base = base_estimates.get(subcategory, 50)
        
        # Multiply by severity factor
        severity_multipliers = {
            EventSeverity.LOW: 0.5,
            EventSeverity.MEDIUM: 1.0,
            EventSeverity.HIGH: 2.0,
            EventSeverity.CRITICAL: 4.0
        }
        
        return int(base * severity_multipliers.get(severity, 1.0))
    
    async def _analyze_event_media(self, media_urls: List[str]) -> Optional[Dict[str, Any]]:
        """Analyze media for additional context"""
        try:
            if not media_urls:
                return None
            
            # Analyze first media file
            first_url = media_urls[0]
            media_type = "video" if self._is_video_url(first_url) else "image"
            
            media_analysis = await self.analyze_media(first_url, media_type)
            
            if media_analysis:
                return {
                    "description": media_analysis.gemini_description,
                    "detected_objects": media_analysis.detected_objects,
                    "visibility": media_analysis.visibility,
                    "confidence": media_analysis.confidence_score
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing event media: {e}")
            return None
    
    async def _create_fallback_event(self, event_request: EventCreateRequest, user_id: str) -> Event:
        """Create event with fallback subcategory if classification fails"""
        try:
            logger.warning("Using fallback event creation")
            
            # Use the old method as fallback
            fallback_subcategory = self._get_subtopic_fallback(event_request.topic)
            
            # Handle location properly whether it's Coordinates object or dict
            if hasattr(event_request.location, 'lat'):
                # It's a Coordinates object
                lat = event_request.location.lat
                lng = event_request.location.lng
            else:
                # It's a dictionary
                lat = event_request.location['lat']
                lng = event_request.location['lng']
            
            # Create basic event structure
            location_data = LocationData(
                lat=lat,
                lng=lng,
                timestamp=datetime.utcnow(),
                address=event_request.address
            )
            
            geographic_data = GeographicData(location=location_data)
            
            content = EventContent(
                title=event_request.title,
                description=event_request.description,
                ai_summary="Fallback processing - classification failed"
            )
            
            impact_analysis = ImpactAnalysis(
                severity=event_request.severity,
                confidence_score=0.5,  # Lower confidence for fallback
                affected_users_estimated=100
            )
            
            # Create basic media if URLs provided
            media = EventMedia()
            if event_request.media_urls:
                media.images = [url for url in event_request.media_urls if self._is_image_url(url)]
                media.videos = [url for url in event_request.media_urls if self._is_video_url(url)]
            
            event = Event(
                topic=event_request.topic,
                sub_topic=fallback_subcategory,
                content=content,
                geographic_data=geographic_data,
                impact_analysis=impact_analysis,
                media=media,
                source=EventSource.CITIZEN_REPORT,
                metadata={
                    "user_id": user_id,
                    "fallback_processing": True,
                    "classification_failed": True
                }
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error in fallback event creation: {e}")
            raise
    
    def _get_subtopic_fallback(self, topic: EventTopic) -> str:
        """Fallback method for subcategory selection (from original event_processor.py)"""
        subtopics = {
            EventTopic.TRAFFIC: ["accident", "congestion", "closure", "construction"],
            EventTopic.INFRASTRUCTURE: ["power_outage", "water_supply", "road_damage", "maintenance"],
            EventTopic.WEATHER: ["rain", "flood", "storm", "heat"],
            EventTopic.EVENTS: ["cultural", "sports", "tech", "music"],
            EventTopic.SAFETY: ["fire", "emergency", "security", "medical"]
        }
        
        import random
        return random.choice(subtopics.get(topic, ["general"]))
    
    def _is_image_url(self, url: str) -> bool:
        """Check if URL is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        return any(url.lower().endswith(ext) for ext in image_extensions)
    
    def _is_video_url(self, url: str) -> bool:
        """Check if URL is a video"""
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        return any(url.lower().endswith(ext) for ext in video_extensions)
    
    # =========================================================================
    # SUBCATEGORY MANAGEMENT API
    # =========================================================================
    
    async def get_available_subcategories(self, topic: EventTopic) -> List[Dict[str, Any]]:
        """Get all available subcategories for a topic"""
        try:
            subcategories = await self.firestore_client.get_subcategories_by_topic(topic)
            
            return [
                {
                    "id": sc.id,
                    "name": sc.name,
                    "display_name": sc.display_name,
                    "description": sc.description,
                    "usage_count": sc.metadata.usage_count,
                    "confidence": sc.metadata.avg_confidence,
                    "source": sc.source.value,
                    "status": sc.status.value
                }
                for sc in subcategories
            ]
            
        except Exception as e:
            logger.error(f"Error getting subcategories for {topic}: {e}")
            return []
    
    async def suggest_subcategories(self, topic: EventTopic, query: str) -> List[Dict[str, Any]]:
        """Suggest subcategories based on query text"""
        try:
            similar_subcategories = await self.firestore_client.search_similar_subcategories(
                topic, query, max_results=5
            )
            
            suggestions = []
            for subcategory, similarity_score in similar_subcategories:
                suggestions.append({
                    "id": subcategory.id,
                    "name": subcategory.name,
                    "display_name": subcategory.display_name,
                    "description": subcategory.description,
                    "similarity_score": similarity_score,
                    "usage_count": subcategory.metadata.usage_count
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting subcategories: {e}")
            return []
    
    async def validate_subcategory_choice(self, subcategory_id: str, user_confirmed: bool) -> bool:
        """Validate user's subcategory choice for learning"""
        try:
            return await self.firestore_client.update_subcategory_usage(
                subcategory_id, user_confirmed=user_confirmed, user_rejected=not user_confirmed
            )
            
        except Exception as e:
            logger.error(f"Error validating subcategory choice: {e}")
            return False
    
    # =========================================================================
    # ANALYTICS AND REPORTING
    # =========================================================================
    
    async def get_subcategory_analytics(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive subcategory analytics"""
        try:
            analytics = await self.firestore_client.get_subcategory_analytics()
            
            if analytics:
                return {
                    "total_subcategories": analytics.total_subcategories,
                    "by_topic": [
                        {
                            "topic": dist.topic.value,
                            "total": dist.total_subcategories,
                            "active": dist.active_subcategories,
                            "most_used": [
                                {
                                    "name": stat.subcategory_name,
                                    "usage": stat.total_usage,
                                    "confidence": stat.avg_confidence,
                                    "satisfaction": stat.user_satisfaction_rate
                                }
                                for stat in dist.most_used_subcategories
                            ]
                        }
                        for dist in analytics.by_topic
                    ],
                    "by_source": analytics.by_source,
                    "by_status": analytics.by_status,
                    "generated_at": analytics.generated_at.isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subcategory analytics: {e}")
            return None
    
    async def get_subcategory_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for subcategory classification"""
        try:
            # Get all subcategories across topics
            all_subcategories = []
            for topic in EventTopic:
                topic_subcategories = await self.firestore_client.get_subcategories_by_topic(topic)
                all_subcategories.extend(topic_subcategories)
            
            # Calculate performance metrics
            total_subcategories = len(all_subcategories)
            ai_generated = len([sc for sc in all_subcategories if sc.source.value == "ai_generated"])
            high_confidence = len([sc for sc in all_subcategories 
                                 if sc.metadata.avg_confidence and sc.metadata.avg_confidence > 0.8])
            
            # User satisfaction metrics
            total_feedback = sum(sc.metadata.user_confirmations + sc.metadata.user_rejections 
                               for sc in all_subcategories)
            total_confirmations = sum(sc.metadata.user_confirmations for sc in all_subcategories)
            
            satisfaction_rate = (total_confirmations / total_feedback) if total_feedback > 0 else 0
            
            # Most and least used
            sorted_by_usage = sorted(all_subcategories, key=lambda x: x.metadata.usage_count, reverse=True)
            
            return {
                "summary": {
                    "total_subcategories": total_subcategories,
                    "ai_generated_count": ai_generated,
                    "ai_generated_percentage": (ai_generated / total_subcategories * 100) if total_subcategories > 0 else 0,
                    "high_confidence_count": high_confidence,
                    "overall_satisfaction_rate": satisfaction_rate,
                    "total_user_feedback": total_feedback
                },
                "most_used": [
                    {
                        "name": sc.name,
                        "topic": sc.topic.value,
                        "usage_count": sc.metadata.usage_count,
                        "avg_confidence": sc.metadata.avg_confidence,
                        "source": sc.source.value
                    }
                    for sc in sorted_by_usage[:10]
                ],
                "least_used": [
                    {
                        "name": sc.name,
                        "topic": sc.topic.value,
                        "usage_count": sc.metadata.usage_count,
                        "source": sc.source.value
                    }
                    for sc in sorted_by_usage[-5:] if sc.metadata.usage_count == 0
                ],
                "needs_review": [
                    {
                        "name": sc.name,
                        "topic": sc.topic.value,
                        "reason": "Low confidence" if (sc.metadata.avg_confidence and sc.metadata.avg_confidence < 0.5) else "High rejection rate"
                    }
                    for sc in all_subcategories
                    if (sc.metadata.avg_confidence and sc.metadata.avg_confidence < 0.5) or
                       (sc.metadata.user_rejections > sc.metadata.user_confirmations and sc.metadata.user_rejections > 0)
                ],
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    # =========================================================================
    # HEALTH CHECK AND MAINTENANCE
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the enhanced processor"""
        try:
            health_status = {
                "enhanced_processor": True,
                "firestore_client": await self.firestore_client.health_check(),
                "subcategory_classifier": await self.classifier.health_check(),
                "total_subcategories": 0,
                "issues": []
            }
            
            # Count total subcategories
            try:
                total = 0
                for topic in EventTopic:
                    subcategories = await self.firestore_client.get_subcategories_by_topic(topic)
                    total += len(subcategories)
                health_status["total_subcategories"] = total
            except Exception as e:
                health_status["issues"].append(f"Could not count subcategories: {str(e)}")
            
            # Check if predefined subcategories exist
            try:
                traffic_subcategories = await self.firestore_client.get_subcategories_by_topic(EventTopic.TRAFFIC)
                if len(traffic_subcategories) == 0:
                    health_status["issues"].append("No predefined subcategories found - may need initialization")
            except Exception as e:
                health_status["issues"].append(f"Could not check predefined subcategories: {str(e)}")
            
            health_status["overall_healthy"] = (
                health_status["firestore_client"] and 
                health_status["subcategory_classifier"] and
                len(health_status["issues"]) == 0
            )
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "enhanced_processor": False,
                "overall_healthy": False,
                "error": str(e)
            }


# Singleton instance
enhanced_subcategory_processor = EnhancedSubcategoryProcessor()
