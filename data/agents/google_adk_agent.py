# data/agents/google_adk_agent.py
"""
Google ADK-based Agentic Layer for City Pulse
Replaces the custom Gemini implementation with proper Google ADK framework
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import uuid
import os
import sys

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our existing components
from data.models.schemas import EventTopic, Coordinates, User
from data.database.user_manager import user_data_manager
from data.database.database_manager import db_manager
from config import config

# Google ADK imports
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import litellm

logger = logging.getLogger(__name__)


class CityPulseADKAgent:
    """
    Advanced Google ADK-based Agentic Layer for City Pulse
    Provides both conversational AI and proactive dashboard content generation
    """
    
    def __init__(self):
        self.agents = {}  # Store multiple specialized agents
        self.runner = None
        self.session_service = None
        self.conversation_sessions = {}
        self.user_contexts = {}
        self._initialize_adk_agents()
    
    def _initialize_adk_agents(self):
        """Initialize Google ADK agents with different specializations"""
        # Set up the environment for ADK
        os.environ["GOOGLE_API_KEY"] = config.GEMINI_API_KEY
        
        # Initialize session service
        self.session_service = InMemorySessionService()
        
        # Create specialized agents
        self._create_conversation_agent()
        self._create_dashboard_agent()
        self._create_insights_agent()
        
        # Initialize runner with required app_name
        self.runner = Runner(
            agent=self.agents["conversation"],
            session_service=self.session_service,
            app_name="city_pulse_adk_agent"
        )
        
        logger.info("🤖 Google ADK-based City Pulse Agentic Layer initialized")
    
    def _create_conversation_agent(self):
        """Create the main conversational agent"""
        # Define tools for the conversation agent
        conversation_tools = [
            self._create_search_events_tool(),
            self._create_get_weather_tool(),
            self._create_get_traffic_tool(),
            self._create_get_user_location_tool()
        ]
        
        self.agents["conversation"] = Agent(
            name="city_pulse_conversation_agent",
            model="gemini-2.0-flash",
            description="Intelligent city assistant for Bengaluru. Helps with traffic, weather, events, and infrastructure issues.",
            instruction="""You are the City Pulse AI Assistant - a knowledgeable and helpful city guide for Bengaluru.

Your capabilities:
- Provide real-time traffic information and route suggestions
- Share weather updates and alerts
- Find local events and activities
- Report on infrastructure issues (power, water, construction)
- Give location-specific advice and recommendations

Context awareness:
- Always consider the user's location when providing advice
- Reference specific Bengaluru areas like MG Road, Koramangala, HSR Layout, Electronic City, Whitefield, ORR
- Provide actionable recommendations with specific next steps
- Use local knowledge about common routes, areas, and landmarks

Response style:
- Be conversational and friendly
- Give specific, actionable advice
- Include confidence levels when uncertain
- Suggest follow-up actions when appropriate
- Keep responses concise but informative (2-4 sentences)

When users ask about:
- Traffic: Use the search_events and get_traffic tools to find current conditions
- Weather: Use get_weather tool for forecasts and alerts
- Events: Search for local happenings and recommendations
- Infrastructure: Look for ongoing issues and provide alternatives
""",
            tools=conversation_tools
        )
    
    def _create_dashboard_agent(self):
        """Create agent specialized for dashboard content generation"""
        dashboard_tools = [
            self._create_analyze_user_patterns_tool(),
            self._create_search_events_tool(),
            self._create_get_weather_tool()
        ]
        
        self.agents["dashboard"] = Agent(
            name="city_pulse_dashboard_agent", 
            model="gemini-2.0-flash",
            description="Specialized agent for generating personalized dashboard content cards.",
            instruction="""You are a dashboard content specialist for City Pulse. Your job is to create personalized, actionable dashboard cards for Bengaluru residents.

Your role:
- Analyze user preferences and location to create relevant content
- Generate 3-4 high-value dashboard cards per request
- Focus on timely, actionable information
- Prioritize content by urgency and relevance

Card types to generate:
1. Traffic alerts - for commute routes and current conditions
2. Weather warnings - impacting user's day or commute  
3. Local events - matching user interests and location
4. Infrastructure updates - affecting user's area

Card format requirements:
- Clear, specific titles
- Actionable summaries (1-2 sentences)
- Specific recommended actions
- Appropriate priority levels (low, medium, high, critical)
- Confidence scores based on data quality

Content guidelines:
- Be proactive - anticipate user needs
- Location-specific to Bengaluru areas
- Time-sensitive information gets higher priority
- Include specific areas like HSR Layout, Koramangala, etc.
- Make recommendations actionable and specific
""",
            tools=dashboard_tools
        )
    
    def _create_insights_agent(self):
        """Create agent for generating analytical insights"""
        insights_tools = [
            self._create_analyze_trends_tool(),
            self._create_search_events_tool()
        ]
        
        self.agents["insights"] = Agent(
            name="city_pulse_insights_agent",
            model="gemini-2.0-flash", 
            description="Analytics specialist providing data-driven insights about city patterns.",
            instruction="""You are an analytical insights specialist for City Pulse. You analyze city data patterns to provide valuable insights for Bengaluru residents.

Your expertise:
- Identify trends in traffic, weather, and infrastructure
- Correlate patterns across different data sources
- Provide predictive insights when possible
- Explain the significance of observed patterns

Insight types:
- Traffic pattern analysis and predictions
- Weather impact assessments
- Event correlation analysis
- Infrastructure issue trends
- Safety and security patterns

Analysis approach:
- Use data from multiple sources
- Explain your reasoning clearly
- Provide confidence levels for predictions
- Suggest actionable responses to insights
- Focus on user-relevant implications

Output format:
- Clear insight statements
- Supporting evidence from data
- Confidence scores (0.0-1.0)
- Recommended actions based on insights
- Time relevance of the insights
""",
            tools=insights_tools
        )
    
    # =========================================================================
    # TOOL DEFINITIONS
    # =========================================================================
    
    def _create_search_events_tool(self):
        """Tool for searching city events and incidents"""
        def search_events(query: str, location_lat: float = None, location_lng: float = None, max_results: int = 5) -> Dict[str, Any]:
            """Search for city events and incidents based on query and location.
            
            Args:
                query: Search query for events (e.g., "traffic", "flooding", "power outage")
                location_lat: Latitude for location-based search
                location_lng: Longitude for location-based search  
                max_results: Maximum number of results to return
                
            Returns:
                Dictionary with search results including events and metadata
            """
            try:
                user_location = None
                if location_lat and location_lng:
                    user_location = Coordinates(lat=location_lat, lng=location_lng)
                
                # Use asyncio to run the async search
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    db_manager.search_events_semantically(
                        query=query,
                        user_location=user_location,
                        max_results=max_results
                    )
                )
                loop.close()
                
                return {
                    "status": "success",
                    "query": query,
                    "results_count": len(results),
                    "events": results[:max_results]
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "query": query
                }
        
        return search_events
    
    def _create_get_weather_tool(self):
        """Tool for getting weather information"""
        def get_weather(location: str = "Bengaluru") -> Dict[str, Any]:
            """Get current weather information for Bengaluru.
            
            Args:
                location: Location name (defaults to Bengaluru)
                
            Returns:
                Weather information including current conditions and forecast
            """
            # Mock weather data - in production, integrate with weather API
            weather_conditions = [
                {"condition": "sunny", "temp": "28°C", "humidity": "65%", "wind": "light"},
                {"condition": "partly cloudy", "temp": "26°C", "humidity": "70%", "wind": "moderate"},
                {"condition": "rainy", "temp": "24°C", "humidity": "85%", "wind": "strong"},
                {"condition": "thunderstorm", "temp": "22°C", "humidity": "90%", "wind": "very strong"}
            ]
            
            import random
            current = random.choice(weather_conditions)
            
            return {
                "status": "success",
                "location": location,
                "current_weather": current,
                "forecast": "Partly cloudy with chances of evening showers",
                "alerts": ["Monsoon advisory in effect"] if current["condition"] in ["rainy", "thunderstorm"] else [],
                "last_updated": datetime.utcnow().isoformat()
            }
        
        return get_weather
    
    def _create_get_traffic_tool(self):
        """Tool for getting traffic information"""
        def get_traffic(route: str = "", location_lat: float = None, location_lng: float = None) -> Dict[str, Any]:
            """Get traffic information for specific routes or areas.
            
            Args:
                route: Specific route or area name
                location_lat: Latitude for location-based traffic info
                location_lng: Longitude for location-based traffic info
                
            Returns:
                Traffic conditions and route recommendations
            """
            # Mock traffic data - in production, integrate with traffic APIs
            traffic_areas = {
                "ORR": {"status": "heavy", "delay": "25-35 minutes", "alternative": "Sarjapur Road"},
                "Electronic City": {"status": "moderate", "delay": "15-20 minutes", "alternative": "Hosur Road"},
                "MG Road": {"status": "light", "delay": "5-10 minutes", "alternative": "Brigade Road"},
                "Koramangala": {"status": "moderate", "delay": "10-15 minutes", "alternative": "Intermediate Ring Road"},
                "HSR Layout": {"status": "light", "delay": "5-10 minutes", "alternative": "27th Main Road"}
            }
            
            if route and route in traffic_areas:
                area_traffic = traffic_areas[route]
            else:
                area_traffic = {"status": "moderate", "delay": "10-20 minutes", "alternative": "Check alternate routes"}
            
            return {
                "status": "success",
                "area": route or "Bengaluru",
                "traffic_conditions": area_traffic,
                "recommendations": [
                    f"Current delay: {area_traffic['delay']}",
                    f"Alternative: {area_traffic['alternative']}"
                ],
                "last_updated": datetime.utcnow().isoformat()
            }
        
        return get_traffic
    
    def _create_get_user_location_tool(self):
        """Tool for getting user location context"""
        def get_user_location(user_id: str) -> Dict[str, Any]:
            """Get user's location and area context.
            
            Args:
                user_id: User identifier
                
            Returns:
                User location information and local context
            """
            try:
                # Get from cache first
                user_context = self.user_contexts.get(user_id, {})
                
                if user_context.get('current_location'):
                    location = user_context['current_location']
                    return {
                        "status": "success",
                        "user_id": user_id,
                        "location": location,
                        "area_context": self._get_area_context(location.get('lat'), location.get('lng'))
                    }
                else:
                    return {
                        "status": "no_location",
                        "user_id": user_id,
                        "message": "No location available for user"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "user_id": user_id
                }
        
        return get_user_location
    
    def _create_analyze_user_patterns_tool(self):
        """Tool for analyzing user behavior patterns"""
        def analyze_user_patterns(user_id: str) -> Dict[str, Any]:
            """Analyze user patterns for dashboard personalization.
            
            Args:
                user_id: User identifier
                
            Returns:
                User behavior analysis for personalization
            """
            try:
                user_context = self.user_contexts.get(user_id, {})
                
                patterns = {
                    "preferred_topics": user_context.get("preferred_topics", ["traffic"]),
                    "common_locations": [
                        user_context.get("home_location", {}),
                        user_context.get("work_location", {})
                    ],
                    "commute_routes": user_context.get("commute_routes", []),
                    "active_times": user_context.get("notification_times", ["08:00", "18:00"]),
                    "interaction_history": len(self.conversation_sessions.get(user_id, []))
                }
                
                return {
                    "status": "success",
                    "user_id": user_id,
                    "patterns": patterns,
                    "recommendations": self._generate_personalization_recommendations(patterns)
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "user_id": user_id
                }
        
        return analyze_user_patterns
    
    def _create_analyze_trends_tool(self):
        """Tool for analyzing city-wide trends"""
        def analyze_trends(timeframe: str = "24h", topic: str = "all") -> Dict[str, Any]:
            """Analyze trends in city data.
            
            Args:
                timeframe: Time period for analysis (1h, 24h, 7d, 30d)
                topic: Specific topic to analyze or "all"
                
            Returns:
                Trend analysis results
            """
            # Mock trend analysis - in production, analyze real data
            trends = {
                "traffic": {
                    "trend": "increasing",
                    "change_percent": 15,
                    "peak_areas": ["ORR", "Electronic City"],
                    "prediction": "Heavy congestion expected during evening rush"
                },
                "infrastructure": {
                    "trend": "stable", 
                    "change_percent": -5,
                    "hotspots": ["HSR Layout", "Whitefield"],
                    "prediction": "Minor power issues may continue"
                },
                "weather": {
                    "trend": "deteriorating",
                    "change_percent": 25,
                    "impact_areas": ["South Bengaluru"],
                    "prediction": "Increased rainfall expected"
                }
            }
            
            if topic != "all" and topic in trends:
                topic_trends = {topic: trends[topic]}
            else:
                topic_trends = trends
            
            return {
                "status": "success",
                "timeframe": timeframe,
                "topic": topic,
                "trends": topic_trends,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        return analyze_trends
    
    # =========================================================================
    # CORE AGENTIC FUNCTIONS
    # =========================================================================
    
    async def handle_conversation(self, user_id: str, message: str, 
                                location: Optional[Coordinates] = None) -> Dict[str, Any]:
        """Handle conversational interaction using Google ADK"""
        # Get user context
        user_context = await self._get_user_context(user_id)
        
        # Build conversation context
        session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d')}"
        
        # Enhance message with context
        enhanced_message = self._build_contextual_message(message, user_context, location)
        
        # Prepare message for ADK
        content = types.Content(
            role='user',
            parts=[types.Part(text=enhanced_message)]
        )
        
        # Run conversation through ADK
        response_text = ""
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                break
        
        # Update conversation history
        self._update_conversation_history(user_id, message, response_text)
        
        # Extract suggested actions
        suggested_actions = self._extract_suggested_actions(response_text, message)
        
        return {
            "response": response_text,
            "suggested_actions": suggested_actions,
            "conversation_id": session_id,
            "knowledge_used": 1,  # ADK handles tool usage internally
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_dashboard_content(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate dashboard content using ADK dashboard agent"""
        try:
            if not ADK_AVAILABLE:
                return await self._fallback_dashboard_content(user_id)
            
            # Get user context for personalization
            user_context = await self._get_user_context(user_id)
            
            # Build dashboard generation prompt
            dashboard_prompt = self._build_dashboard_prompt(user_context)
            
            # Use dashboard agent
            dashboard_runner = Runner(
                agent=self.agents["dashboard"],
                session_service=self.session_service
            )
            
            # Generate dashboard content
            content = types.Content(
                role='user',
                parts=[types.Part(text=dashboard_prompt)]
            )
            
            response_text = ""
            session_id = f"dashboard_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            async for event in dashboard_runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                    break
            
            # Parse and structure the dashboard cards
            cards = self._parse_dashboard_response(response_text, user_context)
            
            logger.info(f"Generated {len(cards)} dashboard cards using ADK for user {user_id}")
            return cards
            
        except Exception as e:
            logger.error(f"Error generating dashboard with ADK: {e}")
            return await self._fallback_dashboard_content(user_id)
    
    async def get_personalized_insights(self, user_id: str, 
                                      insight_type: str = "general") -> Dict[str, Any]:
        """Generate insights using ADK insights agent"""
        try:
            if not ADK_AVAILABLE:
                return await self._fallback_insights(user_id, insight_type)
            
            # Get user context
            user_context = await self._get_user_context(user_id)
            
            # Build insights prompt
            insights_prompt = self._build_insights_prompt(user_context, insight_type)
            
            # Use insights agent
            insights_runner = Runner(
                agent=self.agents["insights"],
                session_service=self.session_service
            )
            
            # Generate insights
            content = types.Content(
                role='user',
                parts=[types.Part(text=insights_prompt)]
            )
            
            response_text = ""
            session_id = f"insights_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            async for event in insights_runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                    break
            
            return {
                "insights": response_text,
                "insight_type": insight_type,
                "user_id": user_id,
                "data_points_used": 3,  # ADK handles data integration
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating insights with ADK: {e}")
            return await self._fallback_insights(user_id, insight_type)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context (same as before)"""
        try:
            # Check cache first
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
            
            self.user_contexts[user_id] = context
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"user_id": user_id, "name": "User"}
    
    def _build_contextual_message(self, message: str, user_context: Dict, location: Optional[Coordinates]) -> str:
        """Build enhanced message with context for ADK"""
        context_parts = [f"User message: {message}"]
        
        # Add user info
        if user_context.get("name"):
            context_parts.append(f"User name: {user_context['name']}")
        
        # Add location context
        if location:
            context_parts.append(f"Current location: {location.lat}, {location.lng}")
            area_context = self._get_area_context(location.lat, location.lng)
            if area_context:
                context_parts.append(f"Area context: {area_context}")
        elif user_context.get("current_location"):
            loc = user_context["current_location"]
            context_parts.append(f"User location: {loc['lat']}, {loc['lng']}")
        
        # Add preferences
        if user_context.get("preferred_topics"):
            context_parts.append(f"User interests: {', '.join(user_context['preferred_topics'])}")
        
        return "\n".join(context_parts)
    
    def _build_dashboard_prompt(self, user_context: Dict) -> str:
        """Build prompt for dashboard generation"""
        current_time = datetime.now().strftime("%H:%M")
        
        prompt_parts = [
            f"Generate 3-4 personalized dashboard cards for user at {current_time}.",
            f"User context: {json.dumps(user_context, indent=2)}",
            "",
            "Create cards for:",
            "1. Traffic alerts relevant to user's routes and interests",
            "2. Weather warnings affecting user's day/commute", 
            "3. Local events matching user's interests and location",
            "4. Infrastructure updates in user's area",
            "",
            "For each card, provide:",
            "- type: (traffic_alert, weather_warning, event_recommendation, infrastructure_update)",
            "- priority: (low, medium, high, critical)",
            "- title: Clear, specific title",
            "- summary: Actionable insight (1-2 sentences)",
            "- action: Specific recommended action",
            "- confidence: 0.0-1.0 confidence score",
            "",
            "Focus on actionable information that's relevant RIGHT NOW for this user in Bengaluru."
        ]
        
        return "\n".join(prompt_parts)
    
    def _build_insights_prompt(self, user_context: Dict, insight_type: str) -> str:
        """Build prompt for insights generation"""
        prompt_parts = [
            f"Generate personalized {insight_type} insights for Bengaluru resident.",
            f"User context: {json.dumps(user_context, indent=2)}",
            "",
            "Analyze and provide insights on:",
            "- Traffic patterns affecting user's routes",
            "- Weather impacts on user's plans",
            "- Local events matching user's interests", 
            "- Infrastructure updates in user's area",
            "",
            "Format insights with:",
            "- Clear insight statements",
            "- Supporting evidence from city data",
            "- Confidence scores (0.0-1.0)",
            "- Recommended actions",
            "- Time relevance",
            "",
            "Make insights actionable and specific to user's needs."
        ]
        
        return "\n".join(prompt_parts)
    
    def _get_area_context(self, lat: float, lng: float) -> str:
        """Get area context for coordinates"""
        # Simple area mapping for Bengaluru
        areas = [
            {"name": "MG Road", "lat": 12.9716, "lng": 77.5946, "radius": 0.01},
            {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245, "radius": 0.015},
            {"name": "HSR Layout", "lat": 12.9116, "lng": 77.6370, "radius": 0.02},
            {"name": "Electronic City", "lat": 12.8456, "lng": 77.6603, "radius": 0.025},
            {"name": "Whitefield", "lat": 12.9698, "lng": 77.7499, "radius": 0.03}
        ]
        
        for area in areas:
            distance = ((lat - area["lat"])**2 + (lng - area["lng"])**2)**0.5
            if distance <= area["radius"]:
                return area["name"]
        
        return "Bengaluru"
    
    def _parse_dashboard_response(self, response_text: str, user_context: Dict) -> List[Dict[str, Any]]:
        """Parse dashboard response from ADK agent"""
        cards = []
        
        try:
            # Try to parse structured response
            lines = response_text.split('\n')
            current_card = {}
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key in ['type', 'priority', 'title', 'summary', 'action']:
                        current_card[key] = value
                    elif key == 'confidence':
                        try:
                            current_card['confidence'] = float(value)
                        except:
                            current_card['confidence'] = 0.8
                
                # End of card
                if line == '' and current_card and 'title' in current_card:
                    card = {
                        "id": str(uuid.uuid4()),
                        "type": current_card.get("type", "info"),
                        "priority": current_card.get("priority", "medium"),
                        "title": current_card.get("title", ""),
                        "summary": current_card.get("summary", ""),
                        "action": current_card.get("action"),
                        "confidence": current_card.get("confidence", 0.8),
                        "created_at": datetime.utcnow().isoformat(),
                        "user_id": user_context.get("user_id")
                    }
                    cards.append(card)
                    current_card = {}
            
            # Add final card if exists
            if current_card and 'title' in current_card:
                card = {
                    "id": str(uuid.uuid4()),
                    "type": current_card.get("type", "info"),
                    "priority": current_card.get("priority", "medium"), 
                    "title": current_card.get("title", ""),
                    "summary": current_card.get("summary", ""),
                    "action": current_card.get("action"),
                    "confidence": current_card.get("confidence", 0.8),
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": user_context.get("user_id")
                }
                cards.append(card)
        
        except Exception as e:
            logger.error(f"Error parsing dashboard response: {e}")
            # Fallback to basic cards
            cards = self._create_fallback_cards(user_context)
        
        return cards[:4]  # Max 4 cards
    
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
    
    def _update_conversation_history(self, user_id: str, user_message: str, ai_response: str):
        """Update conversation history"""
        if user_id not in self.conversation_sessions:
            self.conversation_sessions[user_id] = []
        
        self.conversation_sessions[user_id].extend([
            {"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": ai_response, "timestamp": datetime.utcnow().isoformat()}
        ])
        
        # Keep only last 10 messages
        self.conversation_sessions[user_id] = self.conversation_sessions[user_id][-10:]
    
    def _generate_personalization_recommendations(self, patterns: Dict) -> List[str]:
        """Generate personalization recommendations based on user patterns"""
        recommendations = []
        
        if "traffic" in patterns.get("preferred_topics", []):
            recommendations.append("Show traffic alerts for main commute routes")
        
        if "weather" in patterns.get("preferred_topics", []):
            recommendations.append("Include weather impact on outdoor activities")
        
        if patterns.get("commute_routes"):
            recommendations.append("Prioritize updates for user's commute routes")
        
        return recommendations
    
    def _create_fallback_cards(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Create fallback cards when parsing fails"""
        return [
            {
                "id": str(uuid.uuid4()),
                "type": "welcome",
                "priority": "medium",
                "title": "Welcome to City Pulse",
                "summary": "Your personalized city assistant is ready to help with traffic, weather, and local insights",
                "action": "Ask me anything about Bengaluru",
                "confidence": 0.9,
                "created_at": datetime.utcnow().isoformat(),
                "user_id": user_context.get("user_id")
            }
        ]
    


# Create singleton instance
city_pulse_adk_agent = CityPulseADKAgent()
