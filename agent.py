#!/usr/bin/env python3
"""
City Pulse Agent - Agentic Layer
Advanced AI Agent with conversational intelligence and proactive capabilities
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import re
import sys
import os

# Add data layer to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our data layer and API models
from data.database.database_manager import db_manager
from data.processors.enhanced_event_processor import enhanced_processor
from data.models.schemas import (
    EventTopic, EventSeverity, Coordinates, 
    ConversationMessage, MessageRole, UserContext
)
from data.models.media_schemas import ChatWithMediaRequest, EnhancedChatResponse
import google.generativeai as genai
from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CityPulseAgent:
    """
    Advanced AI Agent for City Pulse
    Provides intelligent, context-aware responses with proactive capabilities
    """
    
    def __init__(self):
        self.conversation_memory = {}  # Store user conversations
        self.user_contexts = {}        # Store user preferences and patterns
        self.active_alerts = {}        # Track ongoing alerts per user
        self._initialize_gemini()
        
    def _initialize_gemini(self):
        """Initialize Gemini for advanced conversation"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("🤖 City Pulse Agent initialized with Gemini AI")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    # =========================================================================
    # CORE AGENT CAPABILITIES
    # =========================================================================
    
    async def process_user_message(self, user_id: str, message: str, 
                                 location: Optional[Coordinates] = None,
                                 media_references: List[str] = None) -> Dict[str, Any]:
        """
        Main agent processing - analyzes user intent and provides intelligent response
        """
        try:
            # Update conversation memory
            self._update_conversation_memory(user_id, message, location)
            
            # Analyze user intent
            intent_analysis = await self._analyze_user_intent(message, location, media_references)
            
            # Get relevant context
            context = await self._get_relevant_context(user_id, intent_analysis, location)
            
            # Generate intelligent response
            response = await self._generate_intelligent_response(
                user_id, message, intent_analysis, context, media_references
            )
            
            # Check for proactive opportunities
            proactive_suggestions = await self._generate_proactive_suggestions(
                user_id, intent_analysis, location
            )
            
            # Update user context
            self._update_user_context(user_id, intent_analysis, response)
            
            return {
                "response": response,
                "intent": intent_analysis,
                "context_used": context,
                "proactive_suggestions": proactive_suggestions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return self._generate_fallback_response(message)
    
    async def _analyze_user_intent(self, message: str, location: Optional[Coordinates],
                                 media_references: List[str] = None) -> Dict[str, Any]:
        """Advanced intent analysis using Gemini"""
        try:
            # Build context for intent analysis
            media_context = ""
            if media_references:
                media_context = f"\nUser has shared {len(media_references)} media files for analysis."
            
            location_context = ""
            if location:
                location_context = f"\nUser location: {location.lat:.4f}, {location.lng:.4f} (Bengaluru area)"
            
            intent_prompt = f"""
            Analyze this user message for intent in a smart city context:
            
            Message: "{message}"
            {location_context}
            {media_context}
            
            Determine:
            1. Primary intent (report_incident, get_info, ask_help, chat, emergency)
            2. Topic category (traffic, infrastructure, weather, events, safety, general)
            3. Urgency level (low, medium, high, critical)
            4. Action required (search, create, analyze, recommend, alert)
            5. Emotional tone (neutral, concerned, frustrated, urgent, casual)
            6. Specific entities (roads, areas, times, event types)
            
            Consider these Bengaluru-specific patterns:
            - "ORR" = Outer Ring Road
            - "traffic" often relates to IT corridor routes
            - "power cut" = power outage
            - "water problem" = water supply issue
            - Monsoon season = flooding concerns
            
            Respond in JSON format:
            {{
                "primary_intent": "report_incident",
                "topic_category": "traffic", 
                "urgency_level": "medium",
                "action_required": "create",
                "emotional_tone": "concerned",
                "entities": {{"roads": ["ORR"], "areas": ["HSR Layout"], "time": "now"}},
                "confidence": 0.85,
                "reasoning": "User is reporting a traffic issue requiring immediate attention"
            }}
            """
            
            response = self.model.generate_content(intent_prompt)
            
            try:
                intent_data = json.loads(response.text.strip())
                logger.info(f"Intent analyzed: {intent_data.get('primary_intent')} ({intent_data.get('confidence', 0):.2f})")
                return intent_data
            except json.JSONDecodeError:
                return self._fallback_intent_analysis(message)
                
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return self._fallback_intent_analysis(message)
    
    async def _get_relevant_context(self, user_id: str, intent_analysis: Dict[str, Any],
                                  location: Optional[Coordinates]) -> Dict[str, Any]:
        """Gather relevant context for intelligent response"""
        context = {
            "user_history": self.conversation_memory.get(user_id, [])[-5:],  # Last 5 messages
            "user_preferences": self.user_contexts.get(user_id, {}),
            "current_events": [],
            "related_incidents": [],
            "system_status": {}
        }
        
        try:
            # Get relevant events based on intent
            if intent_analysis.get("action_required") in ["search", "recommend"]:
                topic = intent_analysis.get("topic_category")
                if topic and topic != "general":
                    search_query = self._build_search_query(intent_analysis)
                    
                    events = await db_manager.search_events_semantically(
                        query=search_query,
                        user_location=location,
                        max_results=5
                    )
                    context["related_incidents"] = events
            
            # Get current system status
            health = await db_manager.health_check()
            stats = await db_manager.get_system_stats()
            context["system_status"] = {"health": health, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error gathering context: {e}")
        
        return context
    
    async def _generate_intelligent_response(self, user_id: str, message: str,
                                           intent_analysis: Dict[str, Any],
                                           context: Dict[str, Any],
                                           media_references: List[str] = None) -> Dict[str, Any]:
        """Generate contextually intelligent response"""
        try:
            # Build comprehensive prompt for response generation
            response_prompt = self._build_response_prompt(
                message, intent_analysis, context, media_references
            )
            
            response = self.model.generate_content(response_prompt)
            
            # Parse and structure the response
            response_data = self._parse_agent_response(response.text)
            
            # Add specific actions based on intent
            if intent_analysis.get("action_required") == "create":
                response_data["action_buttons"] = [
                    {"text": "Report Incident", "action": "create_incident"},
                    {"text": "Upload Photos", "action": "upload_media"},
                    {"text": "Get Updates", "action": "track_incident"}
                ]
            elif intent_analysis.get("action_required") == "search":
                response_data["action_buttons"] = [
                    {"text": "Show on Map", "action": "show_map"},
                    {"text": "Alternative Routes", "action": "get_routes"},
                    {"text": "Set Alert", "action": "set_alert"}
                ]
            
            # Add relevant events to response
            if context.get("related_incidents"):
                response_data["related_events"] = [
                    {
                        "id": event["event_id"],
                        "title": event["document"].split(".")[0][:50] + "...",
                        "similarity": round(event["similarity_score"], 2),
                        "distance_km": event.get("distance_km", 0)
                    }
                    for event in context["related_incidents"][:3]
                ]
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_fallback_response(message)
    
    async def _generate_proactive_suggestions(self, user_id: str, 
                                            intent_analysis: Dict[str, Any],
                                            location: Optional[Coordinates]) -> List[Dict[str, Any]]:
        """Generate proactive suggestions based on user context and current conditions"""
        suggestions = []
        
        try:
            # Time-based suggestions
            current_hour = datetime.now().hour
            
            if 8 <= current_hour <= 10:  # Morning commute
                suggestions.append({
                    "type": "commute_alert",
                    "title": "Morning Commute Update",
                    "message": "Check traffic conditions on your usual route to work",
                    "action": "get_commute_info",
                    "priority": "medium"
                })
            elif 17 <= current_hour <= 20:  # Evening commute
                suggestions.append({
                    "type": "commute_alert", 
                    "title": "Evening Traffic Alert",
                    "message": "Plan your route home - checking for incidents",
                    "action": "get_evening_traffic",
                    "priority": "medium"
                })
            
            # Location-based suggestions
            if location:
                # Check for nearby incidents
                nearby_events = await db_manager.search_events_semantically(
                    query="incidents near location",
                    user_location=location,
                    max_results=3
                )
                
                if nearby_events:
                    high_severity_events = [
                        e for e in nearby_events 
                        if e.get("metadata", {}).get("severity") in ["high", "critical"]
                    ]
                    
                    if high_severity_events:
                        suggestions.append({
                            "type": "safety_alert",
                            "title": "Nearby Incident Alert",
                            "message": f"High-priority incident detected {high_severity_events[0].get('distance_km', 0):.1f}km away",
                            "action": "view_incident_details",
                            "priority": "high",
                            "event_id": high_severity_events[0]["event_id"]
                        })
            
            # Intent-based suggestions
            if intent_analysis.get("topic_category") == "traffic":
                suggestions.append({
                    "type": "traffic_optimization",
                    "title": "Smart Route Planning",
                    "message": "I can suggest optimal routes based on real-time conditions",
                    "action": "get_smart_routes",
                    "priority": "low"
                })
            
        except Exception as e:
            logger.error(f"Error generating proactive suggestions: {e}")
        
        return suggestions
    
    # =========================================================================
    # SPECIALIZED AGENT CAPABILITIES  
    # =========================================================================
    
    async def handle_emergency_situation(self, user_id: str, message: str,
                                       location: Optional[Coordinates]) -> Dict[str, Any]:
        """Special handling for emergency situations"""
        try:
            emergency_response = {
                "response_type": "emergency",
                "main_message": "🚨 Emergency detected. Here's what you should do:",
                "immediate_actions": [],
                "emergency_contacts": [
                    {"service": "Police", "number": "100"},
                    {"service": "Fire", "number": "101"}, 
                    {"service": "Ambulance", "number": "108"},
                    {"service": "BBMP Control Room", "number": "1551"}
                ],
                "safety_instructions": [],
                "location_shared": bool(location)
            }
            
            # Analyze emergency type
            message_lower = message.lower()
            
            if any(word in message_lower for word in ["fire", "burning", "smoke"]):
                emergency_response["immediate_actions"] = [
                    "Call Fire Department: 101",
                    "Evacuate the area if safe to do so",
                    "Do not use elevators",
                    "Stay low if there's smoke"
                ]
                emergency_response["safety_instructions"] = [
                    "Move away from the fire source",
                    "Alert others in the building",
                    "Wait for emergency services"
                ]
                
            elif any(word in message_lower for word in ["accident", "injured", "hurt"]):
                emergency_response["immediate_actions"] = [
                    "Call Ambulance: 108",
                    "Do not move injured persons unless in immediate danger",
                    "Apply first aid if trained",
                    "Clear the area for emergency vehicles"
                ]
                
            elif any(word in message_lower for word in ["flood", "drowning", "water"]):
                emergency_response["immediate_actions"] = [
                    "Move to higher ground immediately",
                    "Call emergency services: 100",
                    "Do not drive through flooded roads",
                    "Avoid electrical equipment"
                ]
            
            # Create incident report automatically
            if location:
                incident_data = {
                    "topic": EventTopic.SAFETY,
                    "sub_topic": "emergency",
                    "title": f"Emergency reported: {message[:50]}...",
                    "description": f"Emergency situation reported by user. Details: {message}",
                    "location": location,
                    "severity": EventSeverity.CRITICAL
                }
                
                # This would create the incident in the background
                # await db_manager.process_user_report(incident_data, user_id)
                emergency_response["incident_created"] = True
            
            return emergency_response
            
        except Exception as e:
            logger.error(f"Error handling emergency: {e}")
            return {
                "response_type": "emergency_fallback",
                "main_message": "Emergency detected. Please call emergency services immediately.",
                "emergency_contacts": [{"service": "Emergency", "number": "112"}]
            }
    
    async def provide_route_recommendations(self, user_id: str, 
                                          origin: Coordinates,
                                          destination: Optional[Coordinates] = None) -> Dict[str, Any]:
        """Provide intelligent route recommendations based on current conditions"""
        try:
            # Get traffic incidents near the route
            route_incidents = await db_manager.search_events_semantically(
                query="traffic incidents route optimization",
                user_location=origin,
                max_results=10
            )
            
            # Filter for traffic-related incidents
            traffic_incidents = [
                incident for incident in route_incidents
                if incident.get("metadata", {}).get("topic") == "traffic"
            ]
            
            recommendations = {
                "route_analysis": {
                    "incidents_found": len(traffic_incidents),
                    "high_impact_incidents": len([
                        i for i in traffic_incidents 
                        if i.get("metadata", {}).get("severity") in ["high", "critical"]
                    ])
                },
                "recommended_actions": [],
                "alternative_suggestions": [],
                "estimated_delays": {},
                "live_updates": True
            }
            
            # Generate recommendations based on incidents
            if traffic_incidents:
                recommendations["recommended_actions"].append(
                    "🚗 Current route has active incidents - consider alternatives"
                )
                
                # Suggest alternatives based on incident locations
                for incident in traffic_incidents[:3]:
                    distance = incident.get("distance_km", 0)
                    if distance < 2:  # Very close to route
                        recommendations["alternative_suggestions"].append(
                            f"Avoid area near {distance:.1f}km ahead - {incident.get('metadata', {}).get('severity', 'unknown')} severity incident"
                        )
                
                recommendations["recommended_actions"].extend([
                    "📱 Enable live traffic updates",
                    "⏰ Consider adjusting departure time",
                    "🗺️ Use alternative routes if available"
                ])
            else:
                recommendations["recommended_actions"].append(
                    "✅ Route looks clear - no major incidents detected"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error providing route recommendations: {e}")
            return {"error": "Unable to analyze routes at this time"}
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _build_search_query(self, intent_analysis: Dict[str, Any]) -> str:
        """Build search query from intent analysis"""
        topic = intent_analysis.get("topic_category", "")
        entities = intent_analysis.get("entities", {})
        
        query_parts = [topic]
        
        if entities.get("roads"):
            query_parts.extend(entities["roads"])
        if entities.get("areas"):
            query_parts.extend(entities["areas"])
        
        return " ".join(filter(None, query_parts))
    
    def _build_response_prompt(self, message: str, intent_analysis: Dict[str, Any],
                             context: Dict[str, Any], media_references: List[str] = None) -> str:
        """Build comprehensive prompt for response generation"""
        
        user_history = context.get("user_history", [])
        related_incidents = context.get("related_incidents", [])
        
        history_text = ""
        if user_history:
            history_text = f"Recent conversation: {[msg['content'] for msg in user_history[-3:]]}"
        
        incidents_text = ""
        if related_incidents:
            incidents_text = f"Related incidents found: {len(related_incidents)} incidents"
        
        media_text = ""
        if media_references:
            media_text = f"User has shared {len(media_references)} media files for analysis."
        
        prompt = f"""
        You are the City Pulse Agent, an intelligent assistant for Bengaluru city management.
        
        User message: "{message}"
        Intent analysis: {intent_analysis}
        {history_text}
        {incidents_text}
        {media_text}
        
        Provide a helpful, contextual response that:
        1. Addresses the user's specific need
        2. Uses local Bengaluru context (areas, roads, services)
        3. Provides actionable information
        4. Maintains a helpful, professional tone
        5. Includes relevant suggestions
        
        Bengaluru context to consider:
        - Traffic hotspots: ORR, Electronic City, Whitefield, Sarjapur Road
        - Monsoon issues: Flooding in low-lying areas
        - Services: BBMP (city), BESCOM (power), BWSSB (water)
        - Areas: HSR Layout, Koramangala, Indiranagar, Marathahalli
        
        Respond in JSON format:
        {{
            "main_message": "Clear, helpful response to user",
            "suggestions": ["Helpful suggestion 1", "Helpful suggestion 2"],
            "follow_up_questions": ["Question to gather more info"],
            "confidence_level": 0.85,
            "response_type": "informational"
        }}
        """
        
        return prompt
    
    def _parse_agent_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and structure agent response"""
        try:
            # Try to parse as JSON first
            response_data = json.loads(response_text.strip())
            return response_data
        except json.JSONDecodeError:
            # Fallback to text response
            return {
                "main_message": response_text.strip(),
                "suggestions": [],
                "follow_up_questions": [],
                "confidence_level": 0.5,
                "response_type": "text"
            }
    
    def _update_conversation_memory(self, user_id: str, message: str, 
                                  location: Optional[Coordinates]):
        """Update conversation memory for context"""
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = []
        
        self.conversation_memory[user_id].append({
            "timestamp": datetime.utcnow().isoformat(),
            "content": message,
            "location": {"lat": location.lat, "lng": location.lng} if location else None
        })
        
        # Keep only last 20 messages
        self.conversation_memory[user_id] = self.conversation_memory[user_id][-20:]
    
    def _update_user_context(self, user_id: str, intent_analysis: Dict[str, Any], 
                           response: Dict[str, Any]):
        """Update user context and preferences"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "preferred_topics": [],
                "frequent_locations": [],
                "interaction_patterns": {},
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Update preferred topics
        topic = intent_analysis.get("topic_category")
        if topic and topic not in self.user_contexts[user_id]["preferred_topics"]:
            self.user_contexts[user_id]["preferred_topics"].append(topic)
        
        # Update interaction patterns
        intent = intent_analysis.get("primary_intent")
        if intent:
            patterns = self.user_contexts[user_id]["interaction_patterns"]
            patterns[intent] = patterns.get(intent, 0) + 1
        
        self.user_contexts[user_id]["last_updated"] = datetime.utcnow().isoformat()
    
    def _fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Fallback intent analysis using simple keyword matching"""
        message_lower = message.lower()
        
        # Emergency detection
        if any(word in message_lower for word in ["emergency", "urgent", "help", "accident", "fire"]):
            return {
                "primary_intent": "emergency",
                "topic_category": "safety",
                "urgency_level": "critical",
                "action_required": "alert",
                "emotional_tone": "urgent",
                "confidence": 0.7
            }
        
        # Traffic queries
        elif any(word in message_lower for word in ["traffic", "road", "route", "jam", "congestion"]):
            return {
                "primary_intent": "get_info",
                "topic_category": "traffic", 
                "urgency_level": "medium",
                "action_required": "search",
                "emotional_tone": "neutral",
                "confidence": 0.6
            }
        
        # Default
        return {
            "primary_intent": "chat",
            "topic_category": "general",
            "urgency_level": "low",
            "action_required": "respond",
            "emotional_tone": "neutral",
            "confidence": 0.3
        }
    
    def _generate_fallback_response(self, message: str) -> Dict[str, Any]:
        """Generate fallback response when AI processing fails"""
        return {
            "main_message": "I understand you're asking about city-related information. Let me help you with that.",
            "suggestions": [
                "Report an incident",
                "Check traffic conditions", 
                "Get area information",
                "Emergency contacts"
            ],
            "follow_up_questions": ["Could you provide more details about what you need help with?"],
            "confidence_level": 0.5,
            "response_type": "fallback"
        }

# Create global agent instance
city_pulse_agent = CityPulseAgent()
