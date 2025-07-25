from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class EventTopic(str, Enum):
    TRAFFIC = "traffic"
    INFRASTRUCTURE = "infrastructure"
    WEATHER = "weather"
    EVENTS = "events"
    SAFETY = "safety"

class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ONGOING = "ongoing"

class EventSource(str, Enum):
    API_FEED = "api_feed"
    CITIZEN_REPORT = "citizen_report"
    PREDICTION = "prediction"

# ============================================================================
# LOCATION AND GEOGRAPHIC MODELS
# ============================================================================

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")

class LocationData(BaseModel):
    lat: float
    lng: float
    accuracy: Optional[int] = Field(None, description="Accuracy in meters")
    timestamp: datetime
    address: Optional[str] = None
    place_id: Optional[str] = Field(None, description="Google Place ID")

class GooglePlace(BaseModel):
    place_id: str = Field(..., description="Google Place ID")
    formatted_address: str
    location: Coordinates
    types: List[str] = Field(default_factory=list)
    name: Optional[str] = None
class GeographicData(BaseModel):
    location: LocationData
    administrative_area: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Ward, zone, city, state info"
    )
    affected_area: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Radius, affected roads, landmarks"
    )

# ============================================================================
# GOOGLE CALENDAR MODELS
# ============================================================================

class CalendarDateTime(BaseModel):
    dateTime: str = Field(..., description="ISO 8601 datetime string")
    timeZone: str = Field(default="Asia/Kolkata")

class CalendarLocation(BaseModel):
    description: str
    place_id: Optional[str] = None
    coordinates: Optional[Coordinates] = None

class CalendarEvent(BaseModel):
    google_event_id: str
    summary: str
    description: Optional[str] = None
    start: CalendarDateTime
    end: CalendarDateTime
    location: Optional[CalendarLocation] = None
    attendees: List[Dict[str, str]] = Field(default_factory=list)
    travel_context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CalendarIntegration(BaseModel):
    access_token: str = Field(..., description="Encrypted token")
    refresh_token: str = Field(..., description="Encrypted refresh token")
    calendar_id: str = Field(default="primary")
    sync_enabled: bool = True
    last_sync: Optional[datetime] = None
    permissions: List[str] = Field(default_factory=lambda: ["read"])
    timezone: str = Field(default="Asia/Kolkata")
# ============================================================================
# USER MODELS
# ============================================================================

class UserProfile(BaseModel):
    google_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserPermissions(BaseModel):
    location_access: bool = False
    calendar_access: bool = False
    notification_enabled: bool = True
    last_permission_update: datetime = Field(default_factory=datetime.utcnow)

class TravelPreferences(BaseModel):
    mode: str = Field(default="driving", description="driving, walking, transit, bicycling")
    avoid: List[str] = Field(default_factory=list, description="tolls, highways, etc")
    units: str = Field(default="metric")

class LocationPreferences(BaseModel):
    radius_km: int = Field(default=5, ge=1, le=50)
    auto_update: bool = True

class UserLocations(BaseModel):
    current: Optional[LocationData] = None
    home: Optional[GooglePlace] = None
    work: Optional[GooglePlace] = None
    preferences: LocationPreferences = Field(default_factory=LocationPreferences)

class GoogleIntegrations(BaseModel):
    calendar: Optional[CalendarIntegration] = None
    maps: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MovementPattern(BaseModel):
    frequently_visited: List[Dict[str, Any]] = Field(default_factory=list)
    commute_routes: List[Dict[str, Any]] = Field(default_factory=list)

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile: UserProfile
    permissions: UserPermissions = Field(default_factory=UserPermissions)
    google_integrations: GoogleIntegrations = Field(default_factory=GoogleIntegrations)
    locations: UserLocations = Field(default_factory=UserLocations)
    movement_pattern: MovementPattern = Field(default_factory=MovementPattern)
# ============================================================================
# EVENT MODELS
# ============================================================================

class MediaAnalysis(BaseModel):
    gemini_description: str
    detected_objects: List[str] = Field(default_factory=list)
    visibility: Optional[str] = None
    weather_impact: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

class EventMedia(BaseModel):
    images: List[str] = Field(default_factory=list, description="Storage URLs")
    videos: List[str] = Field(default_factory=list, description="Storage URLs")
    analyzed_content: Optional[MediaAnalysis] = None

class EventEngagement(BaseModel):
    reports_count: int = Field(default=1)
    confirmations: int = Field(default=0)
    last_confirmation: Optional[datetime] = None

class ImpactAnalysis(BaseModel):
    severity: EventSeverity
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    affected_users_estimated: int = Field(default=0)
    alternate_routes: List[Dict[str, Any]] = Field(default_factory=list)
    calendar_impact: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TemporalData(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_resolution: Optional[datetime] = None
    peak_impact_time: Optional[datetime] = None

class EventContent(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    ai_summary: Optional[str] = Field(None, max_length=500)

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: EventTopic
    sub_topic: str
    content: EventContent
    geographic_data: GeographicData
    temporal_data: TemporalData = Field(default_factory=TemporalData)
    impact_analysis: ImpactAnalysis
    media: EventMedia = Field(default_factory=EventMedia)
    engagement: EventEngagement = Field(default_factory=EventEngagement)
    source: EventSource
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Vector embedding (will be handled separately)
    embedding: Optional[List[float]] = Field(None, exclude=True)
# ============================================================================
# CONVERSATION MODELS
# ============================================================================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageContext(BaseModel):
    user_location: Optional[Coordinates] = None
    intent: Optional[str] = None
    events_referenced: List[str] = Field(default_factory=list)
    recommendations_given: List[str] = Field(default_factory=list)

class ConversationMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: MessageRole
    content: str
    context: MessageContext = Field(default_factory=MessageContext)

class UserBehaviorPatterns(BaseModel):
    frequent_locations: List[Dict[str, Any]] = Field(default_factory=list)
    travel_times: Dict[str, str] = Field(default_factory=dict)

class UserPreferences(BaseModel):
    preferred_topics: List[EventTopic] = Field(default_factory=list)
    commute_routes: List[str] = Field(default_factory=list)
    notification_times: List[str] = Field(default_factory=list)

class InteractionSummary(BaseModel):
    total_queries: int = Field(default=0)
    most_asked_topic: Optional[EventTopic] = None
    last_interaction: Optional[datetime] = None

class UserContext(BaseModel):
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    behavior_patterns: UserBehaviorPatterns = Field(default_factory=UserBehaviorPatterns)
    interaction_summary: InteractionSummary = Field(default_factory=InteractionSummary)

class UserConversation(BaseModel):
    user_id: str
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    user_context: UserContext = Field(default_factory=UserContext)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
# ============================================================================
# DASHBOARD MODELS
# ============================================================================

class DashboardCardType(str, Enum):
    TRAFFIC_ALERT = "traffic_alert"
    EVENT_RECOMMENDATION = "event_recommendation"
    WEATHER_WARNING = "weather_warning"
    CALENDAR_REMINDER = "calendar_reminder"

class DashboardCard(BaseModel):
    card_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: DashboardCardType
    topic: EventTopic
    priority: EventSeverity
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=300)
    action_button: Optional[str] = Field(None, max_length=50)
    location: Optional[Coordinates] = None
    relevant_events: List[str] = Field(default_factory=list)
    media: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserDashboard(BaseModel):
    user_id: str
    personalized_cards: List[DashboardCard] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class EventCreateRequest(BaseModel):
    topic: EventTopic
    sub_topic: str
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    location: Union[Coordinates, Dict[str, float]]
    address: Optional[str] = None
    severity: EventSeverity = EventSeverity.MEDIUM
    media_urls: List[str] = Field(default_factory=list)

class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(..., min_length=1, max_length=1000)
    location: Optional[Coordinates] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    message_id: str
    response: str
    suggestions: List[str] = Field(default_factory=list)
    referenced_events: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
