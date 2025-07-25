# data/processors/subcategory_classifier.py
"""
AI-powered subcategory classification system
Integrates with existing event processor and Firestore for dynamic subcategory management
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime

import google.generativeai as genai

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from data.models.schemas import EventTopic, EventSeverity
from data.models.subcategory_schemas import (
    Subcategory, SubcategorySource, SubcategoryStatus, ClassificationContext,
    ClassificationResult, SubcategoryClassificationRequest
)
from data.database.simple_firestore_client import simple_firestore_client

logger = logging.getLogger(__name__)


class SubcategoryClassifier:
    """AI-powered subcategory classification with dynamic creation"""
    
    def __init__(self):
        self._initialize_gemini()
        self.firestore_client = simple_firestore_client
        
        # Classification confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.8
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.6
        self.LOW_CONFIDENCE_THRESHOLD = 0.4
        
        # Predefined subcategories for fallback
        self.FALLBACK_SUBCATEGORIES = {
            EventTopic.TRAFFIC: {
                "accident": "Vehicle accidents and collisions",
                "congestion": "Traffic jams and slow movement",
                "closure": "Road closures and blockages", 
                "construction": "Road work and maintenance",
                "breakdown": "Vehicle breakdowns",
                "signal_issue": "Traffic signal problems"
            },
            EventTopic.INFRASTRUCTURE: {
                "power_outage": "Electricity supply disruption",
                "water_supply": "Water availability issues",
                "road_damage": "Damaged roads and potholes",
                "maintenance": "Scheduled infrastructure work",
                "network_issue": "Internet and telecom problems",
                "waste_management": "Garbage collection issues"
            },
            EventTopic.WEATHER: {
                "rain": "Rainfall and precipitation",
                "flood": "Waterlogging and flooding",
                "storm": "Severe weather conditions",
                "heat": "High temperature conditions",
                "wind": "Strong wind conditions",
                "fog": "Low visibility due to fog"
            },
            EventTopic.EVENTS: {
                "cultural": "Cultural festivals and celebrations",
                "sports": "Sports events and competitions",
                "tech": "Technology events and meetups",
                "music": "Concerts and musical events",
                "political": "Political rallies and meetings",
                "religious": "Religious gatherings and festivals"
            },
            EventTopic.SAFETY: {
                "fire": "Fire emergencies and incidents",
                "emergency": "General emergency situations",
                "security": "Security and safety concerns",
                "medical": "Medical emergencies",
                "crime": "Criminal activities",
                "accident": "Safety-related accidents"
            }
        }
    
    def _initialize_gemini(self):
        """Initialize Gemini AI for classification"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("✅ Gemini initialized for subcategory classification")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise
    
    # =========================================================================
    # MAIN CLASSIFICATION METHODS
    # =========================================================================
    
    async def classify_subcategory(self, request: SubcategoryClassificationRequest) -> ClassificationResult:
        """Main method to classify or create subcategory"""
        try:
            # Step 1: Get existing subcategories for the topic
            existing_subcategories = await self.firestore_client.get_subcategories_by_topic(
                request.topic, SubcategoryStatus.ACTIVE
            )
            
            # Update context with existing subcategories
            request.context.existing_subcategories = [sc.name for sc in existing_subcategories]
            
            # Step 2: Try AI classification first
            ai_result = await self._classify_with_ai(request)
            
            if ai_result and ai_result.confidence_score >= request.min_confidence_threshold:
                # Step 3: Check if classified subcategory exists
                subcategory = await self._find_or_create_subcategory(
                    request.topic, ai_result.subcategory_name, ai_result, "ai_classification"
                )
                
                if subcategory:
                    # Update usage statistics
                    await self.firestore_client.update_subcategory_usage(
                        subcategory.id, ai_result.confidence_score
                    )
                    
                    return ClassificationResult(
                        subcategory_name=subcategory.name,
                        confidence_score=ai_result.confidence_score,
                        is_new_subcategory=ai_result.is_new_subcategory,
                        reasoning=ai_result.reasoning,
                        alternative_suggestions=ai_result.alternative_suggestions,
                        new_subcategory_id=subcategory.id if ai_result.is_new_subcategory else None,
                        display_name=subcategory.display_name,
                        description=subcategory.description
                    )
            
            # Step 4: Fallback to rule-based classification
            logger.info(f"AI classification failed or low confidence, using fallback for: {request.context.event_title}")
            fallback_result = await self._classify_with_fallback(request)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"Error in subcategory classification: {e}")
            # Return generic subcategory as last resort
            return ClassificationResult(
                subcategory_name="general",
                confidence_score=0.1,
                is_new_subcategory=False,
                reasoning=f"Classification failed: {str(e)}",
                alternative_suggestions=[]
            )
    
    async def _classify_with_ai(self, request: SubcategoryClassificationRequest) -> Optional[ClassificationResult]:
        """Use Gemini AI to classify subcategory"""
        try:
            # Build prompt for AI classification
            prompt = self._build_classification_prompt(request)
            
            # Get AI response
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini AI")
                return None
            
            # Parse AI response
            result = self._parse_ai_response(response.text, request.topic)
            
            logger.info(f"✅ AI classified: {result.subcategory_name} (confidence: {result.confidence_score})")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI classification: {e}")
            return None
    
    def _build_classification_prompt(self, request: SubcategoryClassificationRequest) -> str:
        """Build prompt for AI classification"""
        existing_subcats = ", ".join(request.context.existing_subcategories)
        
        prompt = f"""
You are a smart city incident classification expert. Your task is to classify the following incident into the most appropriate subcategory.

INCIDENT DETAILS:
Topic: {request.topic.value}
Title: {request.context.event_title}
Description: {request.context.event_description}

EXISTING SUBCATEGORIES for {request.topic.value}: {existing_subcats}

INSTRUCTIONS:
1. If the incident clearly fits an existing subcategory, use that exact name
2. If no existing subcategory is appropriate, suggest a NEW subcategory name
3. Use lowercase, underscores for spaces (e.g., "traffic_signal" not "Traffic Signal")
4. Keep subcategory names concise but descriptive
5. Provide confidence score between 0.0 and 1.0

RESPONSE FORMAT (JSON only):
{{
    "subcategory_name": "exact_subcategory_name",
    "confidence_score": 0.85,
    "is_new_subcategory": false,
    "reasoning": "Brief explanation of why this subcategory was chosen",
    "alternative_suggestions": ["alt1", "alt2"]
}}

Respond with ONLY the JSON, no other text.
"""
        
        if request.context.location_context:
            prompt += f"\nLocation Context: {request.context.location_context}"
        
        if request.context.media_analysis:
            prompt += f"\nMedia Analysis: {request.context.media_analysis}"
        
        return prompt
    
    def _parse_ai_response(self, response_text: str, topic: EventTopic) -> ClassificationResult:
        """Parse AI response into ClassificationResult"""
        try:
            # Clean the response (remove markdown formatting if present)
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            # Parse JSON
            data = json.loads(cleaned_response.strip())
            
            # Validate and clean subcategory name
            subcategory_name = self._clean_subcategory_name(data.get("subcategory_name", "general"))
            
            return ClassificationResult(
                subcategory_name=subcategory_name,
                confidence_score=float(data.get("confidence_score", 0.5)),
                is_new_subcategory=bool(data.get("is_new_subcategory", False)),
                reasoning=data.get("reasoning", "AI classification"),
                alternative_suggestions=[
                    self._clean_subcategory_name(alt) 
                    for alt in data.get("alternative_suggestions", [])
                ]
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing AI response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Try to extract subcategory name from text as fallback
            subcategory_name = self._extract_subcategory_from_text(response_text, topic)
            
            return ClassificationResult(
                subcategory_name=subcategory_name,
                confidence_score=0.3,
                is_new_subcategory=False,
                reasoning="Parsed from text (JSON parsing failed)",
                alternative_suggestions=[]
            )
    
    def _clean_subcategory_name(self, name: str) -> str:
        """Clean and standardize subcategory name"""
        if not name:
            return "general"
        
        # Convert to lowercase, replace spaces with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', name.lower().strip())
        
        # Remove multiple underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        return cleaned or "general"
    
    def _extract_subcategory_from_text(self, text: str, topic: EventTopic) -> str:
        """Extract subcategory name from free text as fallback"""
        text_lower = text.lower()
        
        # Look for existing subcategories in text
        for subcategory in self.FALLBACK_SUBCATEGORIES.get(topic, {}):
            if subcategory in text_lower:
                return subcategory
        
        # Look for common keywords by topic
        keyword_mapping = {
            EventTopic.TRAFFIC: {
                'accident': ['accident', 'collision', 'crash'],
                'congestion': ['traffic', 'jam', 'congestion', 'slow'],
                'closure': ['closed', 'closure', 'blocked'],
                'construction': ['construction', 'work', 'repair']
            },
            EventTopic.INFRASTRUCTURE: {
                'power_outage': ['power', 'electricity', 'outage'],
                'water_supply': ['water', 'supply', 'pressure'],
                'road_damage': ['pothole', 'damage', 'road'],
                'maintenance': ['maintenance', 'repair', 'work']
            },
            EventTopic.WEATHER: {
                'rain': ['rain', 'rainfall', 'drizzle'],
                'flood': ['flood', 'waterlog', 'water'],
                'storm': ['storm', 'thunder', 'lightning'],
                'heat': ['heat', 'hot', 'temperature']
            }
        }
        
        topic_keywords = keyword_mapping.get(topic, {})
        for subcategory, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return subcategory
        
        return "general"
    
    async def _classify_with_fallback(self, request: SubcategoryClassificationRequest) -> ClassificationResult:
        """Fallback rule-based classification"""
        try:
            # Use simple keyword matching
            title_desc = f"{request.context.event_title} {request.context.event_description}".lower()
            
            best_match = "general"
            best_score = 0.2
            
            # Check against fallback subcategories
            topic_subcategories = self.FALLBACK_SUBCATEGORIES.get(request.topic, {})
            
            for subcategory, description in topic_subcategories.items():
                score = self._calculate_text_similarity(title_desc, subcategory + " " + description)
                if score > best_score:
                    best_match = subcategory
                    best_score = score
            
            # Find or create the subcategory
            subcategory = await self._find_or_create_subcategory(
                request.topic, best_match, None, "fallback_classification"
            )
            
            if subcategory:
                await self.firestore_client.update_subcategory_usage(
                    subcategory.id, best_score
                )
            
            return ClassificationResult(
                subcategory_name=best_match,
                confidence_score=best_score,
                is_new_subcategory=False,
                reasoning=f"Fallback rule-based classification for {request.topic.value}",
                alternative_suggestions=list(topic_subcategories.keys())[:3]
            )
            
        except Exception as e:
            logger.error(f"Error in fallback classification: {e}")
            return ClassificationResult(
                subcategory_name="general",
                confidence_score=0.1,
                is_new_subcategory=False,
                reasoning="Fallback classification failed",
                alternative_suggestions=[]
            )
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    # =========================================================================
    # SUBCATEGORY MANAGEMENT
    # =========================================================================
    
    async def _find_or_create_subcategory(self, topic: EventTopic, name: str,
                                         ai_result: Optional[ClassificationResult] = None,
                                         created_by: str = "system") -> Optional[Subcategory]:
        """Find existing subcategory or create new one"""
        try:
            # First try to find existing subcategory
            subcategory = await self.firestore_client._find_subcategory_by_name_or_alias(topic, name)
            
            if subcategory:
                return subcategory
            
            # Create new subcategory
            display_name = name.replace('_', ' ').title()
            description = None
            
            # Get description from AI result or fallback
            if ai_result and ai_result.reasoning:
                description = ai_result.reasoning
            elif name in self.FALLBACK_SUBCATEGORIES.get(topic, {}):
                description = self.FALLBACK_SUBCATEGORIES[topic][name]
            
            # Determine source
            source = SubcategorySource.AI_GENERATED if ai_result else SubcategorySource.PREDEFINED
            
            new_subcategory, created = await self.firestore_client.get_or_create_subcategory(
                topic=topic,
                name=name,
                display_name=display_name,
                description=description,
                source=source,
                created_by=created_by
            )
            
            if created:
                logger.info(f"✅ Created new subcategory: {name} for topic {topic.value}")
            
            return new_subcategory
            
        except Exception as e:
            logger.error(f"Error finding/creating subcategory {name}: {e}")
            return None
    
    # =========================================================================
    # INITIALIZATION AND SETUP
    # =========================================================================
    
    async def initialize_predefined_subcategories(self) -> bool:
        """Initialize system with predefined subcategories"""
        try:
            await self.firestore_client.initialize()
            
            created_count = 0
            
            for topic, subcategories in self.FALLBACK_SUBCATEGORIES.items():
                for name, description in subcategories.items():
                    subcategory = Subcategory(
                        name=name,
                        topic=topic,
                        display_name=name.replace('_', ' ').title(),
                        description=description,
                        source=SubcategorySource.PREDEFINED,
                        created_by="system"
                    )
                    
                    success = await self.firestore_client.create_subcategory(subcategory)
                    if success:
                        created_count += 1
            
            logger.info(f"✅ Initialized {created_count} predefined subcategories")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing predefined subcategories: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check classifier health"""
        try:
            # Test Gemini connection
            test_response = self.model.generate_content("Test")
            if not test_response:
                return False
            
            # Test Firestore connection
            return await self.firestore_client.health_check()
            
        except Exception as e:
            logger.error(f"Classifier health check failed: {e}")
            return False


# Singleton instance
subcategory_classifier = SubcategoryClassifier()
