# data/agents/city_pulse_agentic_layer.py
"""
City Pulse Agentic Layer - Global Yet Personalized Assistant
Uses Google Gemini with function calling for intelligent city assistance
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import uuid

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our existing components
from data.models.schemas import EventTopic, Coordinates, User
from data.database.user_manager import user_data_manager
from data.database.database_manager import db_manager

# Google Gemini imports
import google.generativeai as genai
from config import config

logger = logging.getLogger(__name__)


class CityPulseAgenticLayer:
    """
    Advanced Agentic Layer for City Pulse
    Provides both conversational AI and proactive dashboard content generation
    """
    
    def __init__(self):
        self.model = None
        self.conversation_sessions = {}  # Track ongoing conversations
        self.user_contexts = {}  # Cache user contexts
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini with function calling capabilities"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            
            # Initialize model with function calling
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            logger.info("🤖 City Pulse Agentic Layer initialized with Gemini")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    # =========================================================================
    # CORE AGENTIC FUNCTIONS
    # =========================================================================
    
    async def generate_dashboard_content(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate proactive dashboard cards for user"""
        try:
            # Get user context
            user_context = await self._get_user_context(user_id)
            current_time = datetime.now().strftime("%H:%M")
            
            # Get relevant data for dashboard
            location_coords = None
            if user_context.get('current_location'):
                loc = user_context['current_location']
                location_coords = Coordinates(lat=loc['lat'], lng=loc['lng'])
            
            # Search for relevant events
            relevant_events = []
            for topic in user_context.get('preferred_topics', ['traffic']):
                events = await db_manager.search_events_semantically(
                    query=f"{topic} incidents",
                    user_location=location_coords,
                    max_results=3
                )
                relevant_events.extend(events)
            
            # Build comprehensive prompt for dashboard generation
            dashboard_prompt = f"""
            You are the City Pulse AI Assistant generating personalized dashboard content for Bengaluru.
            
            User Context:
            - Name: {user_context.get('name', 'User')}
            - Location: {user_context.get('current_location', 'Bengaluru')}
            - Preferred Topics: {user_context.get('preferred_topics', [])}
            - Commute Routes: {user_context.get('commute_routes', [])}
            - Current Time: {current_time}
            
            Recent Events in User's Area:
            {json.dumps(relevant_events[:3], indent=2) if relevant_events else "No recent events"}
            
            Task: Generate 3-4 personalized dashboard cards with actionable insights.
            
            Create cards for:
            1. Traffic alerts (if user interested in traffic)
            2. Weather impact on commute
            3. Local events matching user interests
            4. Infrastructure updates in user area
            
            Format each card as JSON with:
            - type: (traffic_alert, weather_warning, event_recommendation, infrastructure_update)
            - priority: (low, medium, high, critical)
            - title: Brief descriptive title
            - summary: Actionable insight (1-2 sentences)
            - action: Specific recommended action
            - confidence: 0.0-1.0 confidence score
            - expires_at: When this info becomes stale
            
            Focus on actionable information relevant RIGHT NOW for this user.
            """
            
            # Generate dashboard content
            response = self.model.generate_content(dashboard_prompt)
            
            # Parse cards from response
            cards = self._parse_dashboard_cards(response.text, user_context)
            
            logger.info(f"Generated {len(cards)} dashboard cards for user {user_id}")
            return cards
            
        except Exception as e:
            logger.error(f"Error generating dashboard content: {e}")
            return self._fallback_dashboard_cards(user_id)
    
    async def handle_conversation(self, user_id: str, message: str, 
                                location: Optional[Coordinates] = None) -> Dict[str, Any]:
        """Handle conversational interaction with user"""
        try:
            # Get user context and conversation history
            user_context = await self._get_user_context(user_id)
            conversation_history = self.conversation_sessions.get(user_id, [])
            
            # Build location context
            location_context = ""
            search_location = location
            if location:
                location_context = f"User's current location: {location.lat}, {location.lng}"
            elif user_context.get('current_location'):
                loc = user_context['current_location']
                location_context = f"User's location: {loc.get('lat')}, {loc.get('lng')}"
                search_location = Coordinates(lat=loc['lat'], lng=loc['lng'])
            
            # Search knowledge base for relevant context
            knowledge_results = []
            if search_location:
                # Extract key terms from user message for search
                search_query = self._extract_search_terms(message)
                knowledge_results = await db_manager.search_events_semantically(
                    query=search_query,
                    user_location=search_location,
                    max_results=3
                )
            
            # Build comprehensive conversation prompt
            conversation_prompt = f"""
            You are the City Pulse AI Assistant - a helpful, knowledgeable city guide for Bengaluru.
            
            User Profile:
            - Name: {user_context.get('name', 'User')}
            - Interests: {user_context.get('preferred_topics', [])}
            - Commute Routes: {user_context.get('commute_routes', [])}
            {location_context}
            
            Recent Conversation:
            {self._format_conversation_history(conversation_history[-3:])}
            
            Relevant Local Information:
            {json.dumps(knowledge_results, indent=2) if knowledge_results else "No specific local incidents found"}
            
            User's Current Message: "{message}"
            
            Instructions:
            - Provide helpful, conversational responses with actionable information
            - Use the local information from our knowledge base when relevant
            - Be specific to Bengaluru context (mention areas like MG Road, HSR Layout, Electronic City, ORR, etc.)
            - Give practical recommendations (alternative routes, timings, preparations)
            - Keep responses natural and friendly
            - If asking about traffic, weather, or local events, use the provided local information
            
            Response Guidelines:
            - Start with direct answer to user's question
            - Include specific local details from the knowledge base if relevant
            - End with helpful suggestion or follow-up question
            - Keep response conversational (2-4 sentences)
            """
            
            # Generate response
            response = self.model.generate_content(conversation_prompt)
            
            # Update conversation history
            self._update_conversation_history(user_id, message, response.text)
            
            # Extract any suggested actions from the response
            suggested_actions = self._extract_suggested_actions(response.text, message)
            
            return {
                "response": response.text,
                "suggested_actions": suggested_actions,
                "conversation_id": self._get_conversation_id(user_id),
                "knowledge_used": len(knowledge_results),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            return self._fallback_conversation_response(message)
    
    async def get_personalized_insights(self, user_id: str, 
                                      insight_type: str = "general") -> Dict[str, Any]:
        """Generate specific insights based on user context and city data"""
        try:
            user_context = await self._get_user_context(user_id)
            
            # Get location-based events
            location_coords = None
            if user_context.get('current_location'):
                loc = user_context['current_location']
                location_coords = Coordinates(lat=loc['lat'], lng=loc['lng'])
            
            relevant_data = []
            if location_coords:
                for topic in user_context.get('preferred_topics', ['traffic', 'infrastructure']):
                    events = await db_manager.search_events_semantically(
                        query=f"{topic} {insight_type}",
                        user_location=location_coords,
                        max_results=3
                    )
                    relevant_data.extend(events)
            
            insights_prompt = f"""
            Generate personalized insights for a Bengaluru resident based on their profile and current city conditions.
            
            User Context: {json.dumps(user_context, indent=2)}
            Insight Type: {insight_type}
            
            Local Data Available:
            {json.dumps(relevant_data[:5], indent=2) if relevant_data else "No specific local data"}
            
            Create insights on:
            - Traffic patterns affecting user's routes
            - Weather impacts on user's plans  
            - Local events matching user's interests
            - Infrastructure updates in user's area
            
            Format as actionable insights with confidence scores.
            """
            
            response = self.model.generate_content(insights_prompt)
            
            return {
                "insights": response.text,
                "insight_type": insight_type,
                "user_id": user_id,
                "data_points_used": len(relevant_data),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context"""
        try:
            # Check cache first (5 minute cache)
            if user_id in self.user_contexts:
                cached_time = self.user_contexts[user_id].get('_cached_at')
                if cached_time and (datetime.utcnow() - cached_time).seconds < 300:
                    return self.user_contexts[user_id]
            
            # Get user profile
            user = await user_data_manager.get_user(user_id)
            preferences = await user_data_manager.get_user_preferences(user_id)
            
            context = {
                "user_id": user_id,
                "name": user.profile.name if user else "User",
                "email": user.profile.email if user else None,
                "current_location": {
                    "lat": user.locations.current.lat,
                    "lng": user.locations.current.lng
                } if user and user.locations.current else None,
                "home_location": {
                    "address": user.locations.home.formatted_address,
                    "lat": user.locations.home.location.lat,
                    "lng": user.locations.home.location.lng
                } if user and user.locations.home else None,
                "work_location": {
                    "address": user.locations.work.formatted_address,
                    "lat": user.locations.work.location.lat,
                    "lng": user.locations.work.location.lng
                } if user and user.locations.work else None,
                "preferred_topics": [topic.value for topic in preferences.preferred_topics] if preferences else [],
                "commute_routes": preferences.commute_routes if preferences else [],
                "notification_times": preferences.notification_times if preferences else [],
                "_cached_at": datetime.utcnow()
            }
            
            # Cache the context
            self.user_contexts[user_id] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"user_id": user_id, "name": "User"}
    
    def _parse_dashboard_cards(self, ai_response: str, user_context: Dict) -> List[Dict[str, Any]]:
        """Parse dashboard cards from AI response"""
        cards = []
        try:
            # Try to extract JSON from response
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, ai_response)
            
            for match in json_matches:
                try:
                    card_data = json.loads(match)
                    if 'type' in card_data and 'title' in card_data:
                        card = {
                            "id": str(uuid.uuid4()),
                            "type": card_data.get("type", "info"),
                            "priority": card_data.get("priority", "medium"),
                            "title": card_data.get("title", ""),
                            "summary": card_data.get("summary", ""),
                            "action": card_data.get("action"),
                            "confidence": card_data.get("confidence", 0.8),
                            "expires_at": card_data.get("expires_at"),
                            "created_at": datetime.utcnow().isoformat(),
                            "user_id": user_context.get("user_id")
                        }
                        cards.append(card)
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, create cards from text analysis
            if not cards:
                cards = self._create_cards_from_text(ai_response, user_context)
                
        except Exception as e:
            logger.error(f"Error parsing cards: {e}")
            cards = self._fallback_dashboard_cards(user_context.get("user_id", "unknown"))
        
        return cards[:4]  # Max 4 cards
    
    def _create_cards_from_text(self, text: str, user_context: Dict) -> List[Dict[str, Any]]:
        """Create cards from AI text response when JSON parsing fails"""
        cards = []
        
        # Look for key patterns in the text
        text_lower = text.lower()
        
        if 'traffic' in text_lower:
            cards.append({
                "id": str(uuid.uuid4()),
                "type": "traffic_alert",
                "priority": "medium",
                "title": "Traffic Update",
                "summary": "Check current traffic conditions on your routes",
                "action": "View traffic details",
                "confidence": 0.7,
                "created_at": datetime.utcnow().isoformat()
            })
        
        if 'weather' in text_lower or 'rain' in text_lower:
            cards.append({
                "id": str(uuid.uuid4()),
                "type": "weather_warning", 
                "priority": "medium",
                "title": "Weather Alert",
                "summary": "Weather conditions may affect your commute",
                "action": "Check weather forecast",
                "confidence": 0.7,
                "created_at": datetime.utcnow().isoformat()
            })
        
        return cards
    
    def _extract_search_terms(self, message: str) -> str:
        """Extract key search terms from user message"""
        # Simple keyword extraction
        keywords = []
        message_lower = message.lower()
        
        # Traffic-related terms
        if any(word in message_lower for word in ['traffic', 'road', 'route', 'jam', 'congestion']):
            keywords.append('traffic')
        
        # Weather terms
        if any(word in message_lower for word in ['weather', 'rain', 'flood', 'storm']):
            keywords.append('weather')
        
        # Infrastructure terms
        if any(word in message_lower for word in ['power', 'electricity', 'water', 'infrastructure']):
            keywords.append('infrastructure')
        
        # Events terms
        if any(word in message_lower for word in ['event', 'festival', 'celebration']):
            keywords.append('events')
        
        # Location terms
        bengaluru_areas = ['mg road', 'koramangala', 'hsr layout', 'whitefield', 'electronic city', 'orr', 'silk board']
        for area in bengaluru_areas:
            if area in message_lower:
                keywords.append(area)
        
        return ' '.join(keywords) if keywords else message
    
    def _update_conversation_history(self, user_id: str, user_message: str, ai_response: str):
        """Update conversation history for context"""
        if user_id not in self.conversation_sessions:
            self.conversation_sessions[user_id] = []
        
        self.conversation_sessions[user_id].extend([
            {"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": ai_response, "timestamp": datetime.utcnow().isoformat()}
        ])
        
        # Keep only last 10 messages
        self.conversation_sessions[user_id] = self.conversation_sessions[user_id][-10:]
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "No previous conversation."
        
        formatted = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)
    
    def _extract_suggested_actions(self, response_text: str, user_message: str) -> List[Dict[str, Any]]:
        """Extract suggested actions from conversation response"""
        actions = []
        text = response_text.lower()
        message = user_message.lower()
        
        # Traffic-related actions
        if any(word in text for word in ['route', 'navigation', 'directions']):
            actions.append({"type": "navigation", "text": "Get Directions", "priority": "high"})
        
        if any(word in text for word in ['traffic', 'congestion']):
            actions.append({"type": "traffic", "text": "Live Traffic", "priority": "medium"})
        
        # Weather actions
        if any(word in text for word in ['weather', 'rain', 'forecast']):
            actions.append({"type": "weather", "text": "Weather Forecast", "priority": "medium"})
        
        # Emergency actions
        if any(word in message for word in ['emergency', 'accident', 'urgent']):
            actions.append({"type": "emergency", "text": "Emergency Help", "priority": "critical"})
        
        # Local events
        if any(word in text for word in ['event', 'happening', 'festival']):
            actions.append({"type": "events", "text": "Local Events", "priority": "low"})
        
        return actions
    
    def _get_conversation_id(self, user_id: str) -> str:
        """Get or create conversation ID"""
        return f"conv_{user_id}_{datetime.now().strftime('%Y%m%d')}"
    
    def _fallback_dashboard_cards(self, user_id: str) -> List[Dict[str, Any]]:
        """Fallback dashboard cards when AI generation fails"""
        return [
            {
                "id": str(uuid.uuid4()),
                "type": "welcome",
                "priority": "medium",
                "title": "Welcome to City Pulse",
                "summary": "Your personalized city assistant is ready to help with traffic, weather, and local insights",
                "action": "Ask me anything about Bengaluru",
                "confidence": 0.9,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "type": "info",
                "priority": "low",
                "title": "Getting Started",
                "summary": "Ask about traffic conditions, weather updates, or local events in your area",
                "action": "Start chatting",
                "confidence": 0.9,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
    
    def _fallback_conversation_response(self, message: str) -> Dict[str, Any]:
        """Fallback response when conversation fails"""
        return {
            "response": "I'm here to help with Bengaluru city information! You can ask me about traffic conditions, weather updates, local events, or anything else related to the city. What would you like to know?",
            "suggested_actions": [
                {"type": "traffic", "text": "Traffic Updates", "priority": "medium"},
                {"type": "weather", "text": "Weather Info", "priority": "medium"},
                {"type": "help", "text": "Help", "priority": "low"}
            ],
            "conversation_id": "fallback",
            "timestamp": datetime.utcnow().isoformat()
        }


# Create singleton instance
city_pulse_agent = CityPulseAgenticLayer()
