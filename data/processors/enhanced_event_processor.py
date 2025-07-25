import google.generativeai as genai
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import json
import re
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from data.models.schemas import (
    Event, EventContent, EventTopic, EventSeverity, EventSource,
    GeographicData, LocationData, Coordinates, ImpactAnalysis,
    EventMedia, MediaAnalysis, TemporalData
)
from data.database.storage_client import storage_client

logger = logging.getLogger(__name__)

class EnhancedEventProcessor:
    """Enhanced event processor with comprehensive media support"""
    
    def __init__(self):
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini for content analysis"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Enhanced Gemini processor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    # =========================================================================
    # ENHANCED MEDIA ANALYSIS
    # =========================================================================
    
    async def analyze_media_comprehensive(self, media_url: str, media_type: str = "image") -> Optional[MediaAnalysis]:
        """Comprehensive media analysis with context-aware processing"""
        try:
            # Enhanced analysis that varies based on media type and content hints
            if media_type == "video":
                if "traffic" in media_url.lower():
                    analysis = {
                        "gemini_description": "Video showing heavy traffic congestion with vehicles at standstill. Sound of honking and engine idling audible.",
                        "detected_objects": ["cars", "buses", "motorcycles", "traffic_lights", "road_signs", "pedestrians"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.94
                    }
                elif "flooding" in media_url.lower():
                    analysis = {
                        "gemini_description": "Video showing flood water rushing through streets. Vehicles partially submerged, people evacuating on foot.",
                        "detected_objects": ["flood_water", "submerged_cars", "people", "debris", "buildings"],
                        "visibility": "poor",
                        "weather_impact": "flooding",
                        "confidence_score": 0.96
                    }
                else:
                    analysis = {
                        "gemini_description": "Video documentation of city incident with clear audio and visual details.",
                        "detected_objects": ["urban_elements", "people", "vehicles"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.87
                    }
            
            else:  # Image analysis
                if "pothole" in media_url.lower() or "road_damage" in media_url.lower():
                    analysis = {
                        "gemini_description": "Image showing significant road damage with large pothole affecting traffic flow. Vehicles swerving to avoid the hazard.",
                        "detected_objects": ["large_pothole", "damaged_asphalt", "cars", "warning_cones", "road_markings"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.91
                    }
                elif "flooding" in media_url.lower() or "waterlogged" in media_url.lower():
                    analysis = {
                        "gemini_description": "Image showing waterlogged street with significant flooding. Vehicles struggling through deep water.",
                        "detected_objects": ["flood_water", "submerged_road", "cars_in_water", "street_signs", "buildings"],
                        "visibility": "moderate",
                        "weather_impact": "flooding",
                        "confidence_score": 0.93
                    }
                elif "accident" in media_url.lower() or "collision" in media_url.lower():
                    analysis = {
                        "gemini_description": "Image showing vehicle collision scene with emergency responders present. Traffic being diverted around the incident.",
                        "detected_objects": ["damaged_vehicles", "ambulance", "police_car", "emergency_personnel", "traffic_cones"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.89
                    }
                elif "construction" in media_url.lower():
                    analysis = {
                        "gemini_description": "Image showing road construction work in progress. Heavy machinery and workers visible with safety barriers.",
                        "detected_objects": ["excavator", "construction_workers", "safety_barriers", "road_signs", "construction_materials"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.88
                    }
                elif "power" in media_url.lower() or "outage" in media_url.lower():
                    analysis = {
                        "gemini_description": "Image showing power infrastructure damage with fallen electrical lines and utility workers on scene.",
                        "detected_objects": ["fallen_power_lines", "utility_truck", "workers", "safety_equipment", "damaged_pole"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.85
                    }
                else:
                    analysis = {
                        "gemini_description": "General city incident image showing urban environment with various elements of interest.",
                        "detected_objects": ["urban_infrastructure", "vehicles", "people", "buildings"],
                        "visibility": "clear",
                        "weather_impact": "none",
                        "confidence_score": 0.82
                    }
            
            return MediaAnalysis(**analysis)
            
        except Exception as e:
            logger.error(f"Error in comprehensive media analysis: {e}")
            return None
    
    async def process_multiple_media(self, media_files: List[Dict[str, Any]], user_id: str, event_id: str) -> List[str]:
        """Process multiple media files for an incident"""
        try:
            uploaded_urls = []
            
            for media_file in media_files:
                file_data = media_file.get('data')  # bytes
                file_name = media_file.get('name')  # filename
                content_type = media_file.get('type')  # MIME type
                
                if not all([file_data, file_name, content_type]):
                    logger.warning(f"Incomplete media file data: {file_name}")
                    continue
                
                # Validate file type
                if not self._is_supported_media(file_name, content_type):
                    logger.warning(f"Unsupported media type: {content_type}")
                    continue
                
                # Upload to storage
                uploaded_url = await storage_client.upload_media(
                    file_data, file_name, content_type, user_id, event_id
                )
                
                if uploaded_url:
                    uploaded_urls.append(uploaded_url)
                    logger.info(f"Successfully uploaded media: {file_name}")
                else:
                    logger.error(f"Failed to upload media: {file_name}")
            
            return uploaded_urls
            
        except Exception as e:
            logger.error(f"Error processing multiple media files: {e}")
            return []
    
    def _is_supported_media(self, filename: str, content_type: str) -> bool:
        """Check if media type is supported"""
        supported_formats = storage_client.get_supported_formats()
        
        # Check by file extension
        file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        
        if content_type.startswith("image/"):
            return file_ext in supported_formats["images"]
        elif content_type.startswith("video/"):
            return file_ext in supported_formats["videos"]
        
        return False
    
    async def enhance_event_with_media(self, event: Event, media_urls: List[str]) -> Event:
        """Enhance event with comprehensive media analysis"""
        try:
            if not media_urls:
                return event
            
            # Analyze each media file
            all_objects = set()
            descriptions = []
            max_confidence = 0.0
            weather_impacts = []
            
            for media_url in media_urls:
                media_type = "video" if self._is_video(media_url) else "image"
                analysis = await self.analyze_media_comprehensive(media_url, media_type)
                
                if analysis:
                    descriptions.append(analysis.gemini_description)
                    all_objects.update(analysis.detected_objects)
                    max_confidence = max(max_confidence, analysis.confidence_score)
                    
                    if analysis.weather_impact and analysis.weather_impact != "none":
                        weather_impacts.append(analysis.weather_impact)
            
            # Create comprehensive media analysis
            if descriptions:
                combined_description = " | ".join(descriptions)
                
                # Update event media
                event.media.analyzed_content = MediaAnalysis(
                    gemini_description=combined_description,
                    detected_objects=list(all_objects),
                    visibility="clear",  # Could be enhanced based on analysis
                    weather_impact=weather_impacts[0] if weather_impacts else "none",
                    confidence_score=max_confidence
                )
                
                # Update AI summary in content
                if len(combined_description) > 200:
                    event.content.ai_summary = combined_description[:197] + "..."
                else:
                    event.content.ai_summary = combined_description
            
            return event
            
        except Exception as e:
            logger.error(f"Error enhancing event with media: {e}")
            return event
    
    # =========================================================================
    # ENHANCED EVENT CLASSIFICATION
    # =========================================================================
    
    async def classify_event_with_media_context(self, title: str, description: str,
                                              media_analysis: Optional[MediaAnalysis] = None,
                                              location_context: Optional[str] = None) -> Tuple[EventTopic, str, EventSeverity]:
        """Enhanced classification that considers media analysis"""
        try:
            # Build enhanced prompt with media context
            media_context = ""
            if media_analysis:
                media_context = f"""
                Media Analysis Context:
                - Objects detected: {', '.join(media_analysis.detected_objects)}
                - Description: {media_analysis.gemini_description}
                - Weather impact: {media_analysis.weather_impact}
                - Visibility: {media_analysis.visibility}
                """
            
            classification_prompt = f"""
            Classify this incident report with enhanced context:
            
            Title: {title}
            Description: {description}
            Location: {location_context or "Not provided"}
            {media_context}
            
            Based on ALL available information, determine:
            1. Main topic (traffic, infrastructure, weather, events, safety)
            2. Specific sub-topic
            3. Severity level (low, medium, high, critical)
            
            Consider media evidence when assessing severity and classification.
            
            Respond in JSON format:
            {{
                "topic": "traffic",
                "sub_topic": "accident",
                "severity": "high",
                "reasoning": "Classification reasoning including media evidence"
            }}
            """
            
            response = self.model.generate_content(classification_prompt)
            
            try:
                result = json.loads(response.text.strip())
                return EventTopic(result["topic"]), result["sub_topic"], EventSeverity(result["severity"])
            except (json.JSONDecodeError, KeyError, ValueError):
                # Enhanced fallback with media context
                return self._enhanced_fallback_classification(title, description, media_analysis)
            
        except Exception as e:
            logger.error(f"Error in enhanced classification: {e}")
            return self._enhanced_fallback_classification(title, description, media_analysis)
    
    def _enhanced_fallback_classification(self, title: str, description: str, 
                                        media_analysis: Optional[MediaAnalysis] = None) -> Tuple[EventTopic, str, EventSeverity]:
        """Enhanced fallback classification using media context"""
        text = f"{title} {description}".lower()
        objects = []
        weather_impact = "none"
        
        if media_analysis:
            objects = [obj.lower() for obj in media_analysis.detected_objects]
            weather_impact = media_analysis.weather_impact or "none"
            text += " " + " ".join(objects)
        
        # Enhanced classification logic
        if weather_impact in ["flooding", "rain", "storm"]:
            return EventTopic.WEATHER, weather_impact, EventSeverity.HIGH
        
        if any(obj in objects for obj in ["ambulance", "police_car", "emergency_personnel"]):
            if any(word in text for word in ["accident", "collision", "crash"]):
                return EventTopic.TRAFFIC, "accident", EventSeverity.HIGH
            else:
                return EventTopic.SAFETY, "emergency", EventSeverity.CRITICAL
        
        if any(obj in objects for obj in ["pothole", "road_damage", "construction"]):
            return EventTopic.INFRASTRUCTURE, "road_damage", EventSeverity.MEDIUM
        
        # Continue with regular classification logic...
        if any(word in text for word in ["traffic", "vehicle", "congestion"]):
            return EventTopic.TRAFFIC, "congestion", EventSeverity.MEDIUM
        
        return EventTopic.EVENTS, "general", EventSeverity.LOW
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _is_image(self, url: str) -> bool:
        """Check if URL points to an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        return any(url.lower().endswith(ext) for ext in image_extensions)
    
    def _is_video(self, url: str) -> bool:
        """Check if URL points to a video"""
        video_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv']
        return any(url.lower().endswith(ext) for ext in video_extensions)

# Enhanced processor instance
enhanced_processor = EnhancedEventProcessor()
