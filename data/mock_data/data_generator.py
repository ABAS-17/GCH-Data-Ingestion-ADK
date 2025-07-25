import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.models.schemas import (
    Event, User, UserConversation, ConversationMessage, MessageRole,
    EventTopic, EventSeverity, EventSource, EventContent,
    GeographicData, LocationData, Coordinates, ImpactAnalysis,
    EventMedia, TemporalData, UserProfile, UserPermissions,
    UserLocations, GooglePlace, MessageContext,
    UserContext, UserPreferences
)

logger = logging.getLogger(__name__)

class MockDataGenerator:
    """Generate realistic mock data for Bengaluru city"""
    
    def __init__(self):
        # Bengaluru locations and landmarks
        self.bengaluru_areas = [
            {"name": "HSR Layout", "lat": 12.9116, "lng": 77.6370},
            {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245},
            {"name": "Indiranagar", "lat": 12.9784, "lng": 77.6408},
            {"name": "Whitefield", "lat": 12.9698, "lng": 77.7499},
            {"name": "Electronic City", "lat": 12.8456, "lng": 77.6603},
            {"name": "Marathahalli", "lat": 12.9591, "lng": 77.6974},
            {"name": "BTM Layout", "lat": 12.9165, "lng": 77.6101},
            {"name": "Jayanagar", "lat": 12.9249, "lng": 77.5832},
            {"name": "Rajajinagar", "lat": 12.9894, "lng": 77.5555},
            {"name": "Banashankari", "lat": 12.9081, "lng": 77.5675},
            {"name": "Malleswaram", "lat": 13.0039, "lng": 77.5749},
            {"name": "MG Road", "lat": 12.9716, "lng": 77.5946},
            {"name": "Hebbal", "lat": 13.0358, "lng": 77.5970},
            {"name": "Yeshwanthpur", "lat": 13.0280, "lng": 77.5540},
            {"name": "JP Nagar", "lat": 12.9089, "lng": 77.5849}
        ]
        
        self.roads = [
            "Old Airport Road", "Outer Ring Road", "Hosur Road", "Bannerghatta Road",
            "Sarjapur Road", "Whitefield Main Road", "ORR", "Mysore Road",
            "Tumkur Road", "Bellary Road", "Kanakpura Road", "Electronic City Flyover"
        ]
        
        # Event templates for different topics
        self.event_templates = {
            EventTopic.TRAFFIC: [
                ("Heavy traffic on {road}", "Multiple vehicle breakdown causing {delay} min delays. Alternative routes recommended via {alt_route}."),
                ("Road closure at {area}", "Temporary closure due to {reason}. Expected to reopen by {time}."),
                ("Accident reported on {road}", "Minor collision reported, traffic moving slowly. Emergency services on scene."),
                ("Construction work on {road}", "Ongoing road maintenance causing lane closures. Peak hours affected.")
            ],
            EventTopic.INFRASTRUCTURE: [
                ("Power outage in {area}", "Electricity supply disrupted due to {reason}. Restoration expected by {time}."),
                ("Water supply issue in {area}", "Low water pressure reported. BWSSB working on restoration."),
                ("Road damage on {road}", "Large pothole causing vehicle damage. Authorities notified."),
                ("Street light maintenance", "Street lighting repair work ongoing in {area} sector.")
            ],
            EventTopic.WEATHER: [
                ("Heavy rainfall in {area}", "Intense showers causing waterlogging in low-lying areas. Drive carefully."),
                ("Flooding reported on {road}", "Water accumulation making road impassable. Avoid the area."),
                ("Storm warning for {area}", "Strong winds and rain expected. Secure loose objects."),
                ("Heat wave conditions", "Temperature reaching 38°C in {area}. Stay hydrated.")
            ],
            EventTopic.EVENTS: [
                ("Cultural festival at {area}", "Traditional celebrations ongoing. Expect crowd and parking challenges."),
                ("Marathon event on {road}", "Running event causing temporary road closures from {time}."),
                ("Concert at {area}", "Live music event. Heavy foot traffic and parking shortage expected."),
                ("Tech meetup in {area}", "Networking event for IT professionals. Limited parking available.")
            ],
            EventTopic.SAFETY: [
                ("Fire reported near {area}", "Emergency services responding. Avoid the immediate area."),
                ("Security alert in {area}", "Increased police presence due to safety concerns."),
                ("Medical emergency on {road}", "Ambulance services active. Traffic may be affected."),
                ("Protest march on {road}", "Peaceful demonstration affecting traffic flow.")
            ]
        }
    
    # =========================================================================
    # EVENT GENERATION
    # =========================================================================
    
    def generate_event(self, topic: EventTopic = None) -> Event:
        """Generate a single realistic event"""
        if not topic:
            topic = random.choice(list(EventTopic))
        
        # Choose template and area
        template = random.choice(self.event_templates[topic])
        area = random.choice(self.bengaluru_areas)
        road = random.choice(self.roads)
        
        # Generate title and description
        title = template[0].format(
            area=area["name"],
            road=road,
            delay=random.randint(10, 60),
            time=f"{random.randint(1, 12)}:{random.randint(0, 59):02d}",
            reason=random.choice(["technical fault", "maintenance work", "equipment failure"])
        )
        
        description = template[1].format(
            area=area["name"],
            road=road,
            delay=random.randint(10, 60),
            alt_route=random.choice(self.roads),
            time=f"{random.randint(1, 12)}:{random.randint(0, 59):02d}",
            reason=random.choice(["technical fault", "maintenance work", "equipment failure"])
        )
        
        # Add some randomness to coordinates
        lat = area["lat"] + random.uniform(-0.01, 0.01)
        lng = area["lng"] + random.uniform(-0.01, 0.01)
        
        # Create location data
        location_data = LocationData(
            lat=lat,
            lng=lng,
            timestamp=datetime.utcnow(),
            address=f"{area['name']}, Bengaluru, Karnataka"
        )
        
        geographic_data = GeographicData(
            location=location_data,
            administrative_area={
                "ward": area["name"],
                "zone": random.choice(["Bommanahalli", "Mahadevapura", "East", "West", "South"]),
                "city": "Bengaluru",
                "state": "Karnataka"
            },
            affected_area={
                "radius_km": random.uniform(1.0, 5.0),
                "affected_roads": [road] + random.sample(self.roads, k=random.randint(1, 3)),
                "nearby_landmarks": [
                    {"name": f"Landmark {i}", "distance_km": random.uniform(0.5, 2.0)}
                    for i in range(random.randint(1, 3))
                ]
            }
        )
        
        # Determine severity based on topic
        severity_weights = {
            EventTopic.TRAFFIC: [EventSeverity.MEDIUM, EventSeverity.HIGH],
            EventTopic.INFRASTRUCTURE: [EventSeverity.LOW, EventSeverity.MEDIUM],
            EventTopic.WEATHER: [EventSeverity.MEDIUM, EventSeverity.HIGH, EventSeverity.CRITICAL],
            EventTopic.EVENTS: [EventSeverity.LOW, EventSeverity.MEDIUM],
            EventTopic.SAFETY: [EventSeverity.HIGH, EventSeverity.CRITICAL]
        }
        severity = random.choice(severity_weights[topic])
        
        # Create event
        event = Event(
            topic=topic,
            sub_topic=self._get_subtopic(topic),
            content=EventContent(title=title, description=description),
            geographic_data=geographic_data,
            impact_analysis=ImpactAnalysis(
                severity=severity,
                confidence_score=random.uniform(0.7, 0.95),
                affected_users_estimated=random.randint(50, 1000),
                alternate_routes=[],
                calendar_impact={}
            ),
            source=random.choice(list(EventSource)),
            temporal_data=TemporalData(
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 180)),
                estimated_resolution=datetime.utcnow() + timedelta(hours=random.randint(1, 8))
            )
        )
        
        return event
    
    def generate_events(self, count: int = 50) -> List[Event]:
        """Generate multiple events with distribution across topics"""
        events = []
        
        # Topic distribution (more traffic and infrastructure events)
        topic_weights = [
            (EventTopic.TRAFFIC, 0.4),
            (EventTopic.INFRASTRUCTURE, 0.25),
            (EventTopic.WEATHER, 0.15),
            (EventTopic.EVENTS, 0.15),
            (EventTopic.SAFETY, 0.05)
        ]
        
        for i in range(count):
            # Choose topic based on weights
            rand = random.random()
            cumulative = 0
            chosen_topic = EventTopic.TRAFFIC
            
            for topic, weight in topic_weights:
                cumulative += weight
                if rand <= cumulative:
                    chosen_topic = topic
                    break
            
            events.append(self.generate_event(chosen_topic))
        
        return events
    
    # =========================================================================
    # USER GENERATION
    # =========================================================================
    
    def generate_user(self) -> User:
        """Generate a realistic user profile"""
        first_names = ["Arjun", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Ravi", "Kavya", "Suresh", "Meera"]
        last_names = ["Sharma", "Patel", "Kumar", "Singh", "Reddy", "Nair", "Gupta", "Iyer", "Rao", "Joshi"]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}"
        
        # Choose home and work locations
        home_area = random.choice(self.bengaluru_areas)
        work_area = random.choice([area for area in self.bengaluru_areas if area != home_area])
        
        user = User(
            profile=UserProfile(
                google_id=f"google_{uuid.uuid4().hex[:10]}",
                email=email,
                name=f"{first_name} {last_name}",
                avatar_url=f"https://ui-avatars.com/api/?name={first_name}+{last_name}"
            ),
            permissions=UserPermissions(
                location_access=True,
                calendar_access=random.choice([True, False]),
                notification_enabled=True
            ),
            locations=UserLocations(
                home=GooglePlace(
                    place_id=f"place_{uuid.uuid4().hex[:10]}",
                    formatted_address=f"{home_area['name']}, Bengaluru, Karnataka",
                    location=Coordinates(lat=home_area["lat"], lng=home_area["lng"]),
                    types=["sublocality", "political"],
                    name=home_area["name"]
                ),
                work=GooglePlace(
                    place_id=f"place_{uuid.uuid4().hex[:10]}",
                    formatted_address=f"{work_area['name']}, Bengaluru, Karnataka",
                    location=Coordinates(lat=work_area["lat"], lng=work_area["lng"]),
                    types=["establishment", "point_of_interest"],
                    name=f"Office in {work_area['name']}"
                )
            )
        )
        
        return user
    
    def generate_users(self, count: int = 10) -> List[User]:
        """Generate multiple users"""
        return [self.generate_user() for _ in range(count)]
    
    # =========================================================================
    # CONVERSATION GENERATION
    # =========================================================================
    
    def generate_conversation(self, user_id: str) -> UserConversation:
        """Generate realistic conversation history for a user"""
        
        conversation_templates = [
            ("What's the traffic like to Whitefield?", "There's moderate traffic on the usual route via ORR. Consider taking Sarjapur Road for a 10-minute faster journey."),
            ("Any events happening this weekend?", "There's a cultural festival at Cubbon Park and a tech meetup in Koramangala. Both are family-friendly!"),
            ("Is there flooding on Hosur Road?", "Yes, heavy waterlogging reported near Electronic City. Alternative routes via Bannerghatta Road are clear."),
            ("Power outage in my area?", "BESCOM reports scheduled maintenance in HSR Layout from 10 AM to 2 PM today."),
            ("Best route to airport right now?", "Take the ORR via Hebbal - approximately 45 minutes with current traffic conditions.")
        ]
        
        messages = []
        for i, (user_msg, assistant_msg) in enumerate(random.sample(conversation_templates, k=min(3, len(conversation_templates)))):
            # User message
            messages.append(ConversationMessage(
                role=MessageRole.USER,
                content=user_msg,
                context=MessageContext(
                    user_location=Coordinates(
                        lat=random.uniform(12.8, 13.1),
                        lng=random.uniform(77.4, 77.8)
                    ),
                    intent="query"
                )
            ))
            
            # Assistant response
            messages.append(ConversationMessage(
                role=MessageRole.ASSISTANT,
                content=assistant_msg,
                context=MessageContext(
                    events_referenced=[f"event_{uuid.uuid4().hex[:8]}"],
                    recommendations_given=["alternative_route"]
                )
            ))
        
        # User preferences based on conversation
        preferences = UserPreferences(
            preferred_topics=[random.choice(list(EventTopic)) for _ in range(2)],
            commute_routes=["HSR to Whitefield", "Koramangala to Electronic City"],
            notification_times=["08:30", "18:00"]
        )
        
        return UserConversation(
            user_id=user_id,
            conversation_history=messages,
            user_context=UserContext(preferences=preferences)
        )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _get_subtopic(self, topic: EventTopic) -> str:
        """Get appropriate subtopic for given topic"""
        subtopics = {
            EventTopic.TRAFFIC: ["accident", "congestion", "closure", "construction"],
            EventTopic.INFRASTRUCTURE: ["power_outage", "water_supply", "road_damage", "maintenance"],
            EventTopic.WEATHER: ["rain", "flood", "storm", "heat"],
            EventTopic.EVENTS: ["cultural", "sports", "tech", "music"],
            EventTopic.SAFETY: ["fire", "emergency", "security", "medical"]
        }
        return random.choice(subtopics[topic])

# Singleton instance
mock_generator = MockDataGenerator()
