import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Application configuration settings"""
    
    # Google Cloud Configuration
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    
    # Google APIs
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_CALENDAR_API_KEY: str = os.getenv("GOOGLE_CALENDAR_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # ChromaDB Configuration
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    CHROMA_COLLECTION_EVENTS: str = os.getenv("CHROMA_COLLECTION_EVENTS", "city_events")
    CHROMA_COLLECTION_USERS: str = os.getenv("CHROMA_COLLECTION_USERS", "user_preferences")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Application Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    
    # Firestore Collections
    USERS_COLLECTION = "users"
    EVENTS_COLLECTION = "global_events"
    CONVERSATIONS_COLLECTION = "user_conversations"
    DASHBOARDS_COLLECTION = "user_dashboards"
    REPORTS_COLLECTION = "user_reports"
    
    # Vector Search Configuration
    EMBEDDING_DIMENSION = 1536  # OpenAI ada-002 embedding size
    SIMILARITY_THRESHOLD = 0.7
    MAX_SEARCH_RESULTS = 10
    
    # Location Configuration
    DEFAULT_LOCATION_RADIUS_KM = 5
    MAX_LOCATION_RADIUS_KM = 50
    BENGALURU_CENTER = {"lat": 12.9716, "lng": 77.5946}
    
    # Event Configuration
    EVENT_EXPIRY_HOURS = 24
    MAX_EVENTS_PER_LOCATION = 50
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            "GOOGLE_CLOUD_PROJECT",
            "FIREBASE_PROJECT_ID", 
            "GEMINI_API_KEY"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        return True

# Create singleton config instance
config = Config()

# Validate configuration on import
if config.ENVIRONMENT == "production":
    config.validate_config()
