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

logger = logging.getLogger(__name__)

class EventProcessor:
    """Process and analyze events using Gemini AI"""
    
    def __init__(self):
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini for content analysis"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini initialized for event processing")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    # =========================================================================
    # IMAGE/VIDEO ANALYSIS
    # =========================================================================
    
    async def analyze_media(self, media_url: str, media_type: str = "image") -> Optional[MediaAnalysis]:
        """Analyze uploaded image or video using Gemini Vision"""
        try:
            # For this POC, we'll simulate media analysis
            # In production, you'd download the media from Firebase Storage
            
            # For POC, simulate analysis based on media type
            mock_analysis = {
                "gemini_description": f"Traffic scene with multiple vehicles, appears to be during daytime with clear visibility",
                "detected_objects": ["cars", "road", "traffic_signs"],
                "visibility": "clear",
                "weather_impact": "none",
                "confidence_score": 0.85
            }
            
            return MediaAnalysis(**mock_analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing media: {e}")
            return None
    
    # =========================================================================
    # EVENT CLASSIFICATION
    # =========================================================================
    
    async def classify_event(self, title: str, description: str, 
                           location_context: Optional[str] = None) -> Tuple[EventTopic, str, EventSeverity]:
        """Classify event topic, sub_topic, and severity using Gemini"""
        try:
            classification_prompt = f"""
            Classify this event report into appropriate categories:
            
            Title: {title}
            Description: {description}
            Location Context: {location_context or "Not provided"}
            
            Based on this information, determine:
            1. Main topic (traffic, infrastructure, weather, events, safety)
            2. Sub-topic (specific category within the main topic)
            3. Severity level (low, medium, high, critical)
            
            Topic definitions:
            - traffic: Vehicle-related issues, accidents, congestion, road closures
            - infrastructure: Power outages, water supply, road damage, construction
            - weather: Rain, flooding, storms, heat waves
            - events: Cultural events, festivals, sports, gatherings
            - safety: Crime, emergencies, fires, accidents
            
            Severity guidelines:
            - low: Minor issues, informational
            - medium: Moderate impact, some inconvenience
            - high: Significant impact, major disruption
            - critical: Emergency situation, immediate action needed
            
            Respond in JSON format:
            {{
                "topic": "traffic",
                "sub_topic": "accident",
                "severity": "high",
                "reasoning": "Brief explanation of classification"
            }}
            """
            
            response = self.model.generate_content(classification_prompt)
            
            try:
                # Parse JSON response
                result = json.loads(response.text.strip())
                
                topic = EventTopic(result["topic"])
                sub_topic = result["sub_topic"]
                severity = EventSeverity(result["severity"])
                
                return topic, sub_topic, severity
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse classification response: {e}")
                # Fallback classification
                return self._fallback_classification(title, description)
            
        except Exception as e:
            logger.error(f"Error classifying event: {e}")
            return self._fallback_classification(title, description)
    
    def _fallback_classification(self, title: str, description: str) -> Tuple[EventTopic, str, EventSeverity]:
        """Fallback classification using keyword matching"""
        text = f"{title} {description}".lower()
        
        # Traffic keywords
        if any(word in text for word in ["traffic", "accident", "vehicle", "car", "road", "highway"]):
            if any(word in text for word in ["accident", "crash", "collision"]):
                return EventTopic.TRAFFIC, "accident", EventSeverity.HIGH
            return EventTopic.TRAFFIC, "congestion", EventSeverity.MEDIUM
        
        # Infrastructure keywords
        elif any(word in text for word in ["power", "electricity", "water", "construction", "repair"]):
            return EventTopic.INFRASTRUCTURE, "maintenance", EventSeverity.MEDIUM
        
        # Weather keywords
        elif any(word in text for word in ["rain", "flood", "storm", "weather"]):
            return EventTopic.WEATHER, "rain", EventSeverity.MEDIUM
        
        # Event keywords
        elif any(word in text for word in ["festival", "concert", "celebration", "event"]):
            return EventTopic.EVENTS, "cultural", EventSeverity.LOW
        
        # Safety keywords
        elif any(word in text for word in ["emergency", "fire", "crime", "danger"]):
            return EventTopic.SAFETY, "emergency", EventSeverity.HIGH
        
        # Default
        return EventTopic.EVENTS, "general", EventSeverity.LOW
    
    # =========================================================================
    # EVENT CREATION PIPELINE
    # =========================================================================
    
    async def process_user_report(self, title: str, description: str,
                                location: Coordinates, address: Optional[str] = None,
                                media_urls: List[str] = None) -> Event:
        """Process a user-submitted report into a complete Event object"""
        try:
            # 1. Classify the event
            topic, sub_topic, severity = await self.classify_event(title, description, address)
            
            # 2. Enrich location data
            geographic_data = await self.enrich_location_data(location, address)
            
            # 3. Process media if available
            media = EventMedia()
            if media_urls:
                media.images = [url for url in media_urls if self._is_image(url)]
                media.videos = [url for url in media_urls if self._is_video(url)]
                
                # Analyze first image if available
                if media.images:
                    media.analyzed_content = await self.analyze_media(media.images[0], "image")
            
            # 4. Create event content
            content = EventContent(
                title=title,
                description=description
            )
            
            # 5. Analyze impact
            impact_analysis = ImpactAnalysis(
                severity=severity,
                confidence_score=0.8,
                affected_users_estimated=100,
                alternate_routes=[],
                calendar_impact={}
            )
            
            # 6. Create complete event
            event = Event(
                topic=topic,
                sub_topic=sub_topic,
                content=content,
                geographic_data=geographic_data,
                impact_analysis=impact_analysis,
                media=media,
                source=EventSource.CITIZEN_REPORT,
                temporal_data=TemporalData()
            )
            
            logger.info(f"Processed user report into event: {event.id}")
            return event
            
        except Exception as e:
            logger.error(f"Error processing user report: {e}")
            raise
    
    async def enrich_location_data(self, coordinates: Coordinates, 
                                 address: Optional[str] = None) -> GeographicData:
        """Enrich location data with administrative area information"""
        try:
            # For POC, create mock administrative area data
            # In production, use Google Maps Geocoding API
            
            location_data = LocationData(
                lat=coordinates.lat,
                lng=coordinates.lng,
                timestamp=datetime.utcnow(),
                address=address or f"Location near {coordinates.lat:.4f}, {coordinates.lng:.4f}"
            )
            
            # Mock administrative area for Bengaluru
            administrative_area = {
                "ward": "HSR Layout",
                "zone": "Bommanahalli",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India"
            }
            
            # Mock affected area calculation
            affected_area = {
                "radius_km": 2,
                "affected_roads": ["Old Airport Road", "HSR Layout Main Road"],
                "nearby_landmarks": [
                    {"name": "Forum Mall", "distance_km": 1.2},
                    {"name": "HSR BDA Complex", "distance_km": 0.8}
                ]
            }
            
            return GeographicData(
                location=location_data,
                administrative_area=administrative_area,
                affected_area=affected_area
            )
            
        except Exception as e:
            logger.error(f"Error enriching location data: {e}")
            # Return minimal location data
            return GeographicData(
                location=LocationData(
                    lat=coordinates.lat,
                    lng=coordinates.lng,
                    timestamp=datetime.utcnow(),
                    address=address
                )
            )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _is_image(self, url: str) -> bool:
        """Check if URL points to an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return any(url.lower().endswith(ext) for ext in image_extensions)
    
    def _is_video(self, url: str) -> bool:
        """Check if URL points to a video"""
        video_extensions = ['.mp4', '.avi', '.mov', '.webm']
        return any(url.lower().endswith(ext) for ext in video_extensions)

# Singleton instance
event_processor = EventProcessor()
