import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
import google.generativeai as genai
from datetime import datetime
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from data.models.schemas import Event, EventTopic, Coordinates

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """ChromaDB client for vector similarity search and embeddings"""
    
    def __init__(self):
        self.client = None
        self.events_collection = None
        self.users_collection = None
        self._initialize_chroma()
        self._initialize_gemini()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collections"""
        try:
            # Initialize ChromaDB with persistent storage
            self.client = chromadb.PersistentClient(
                path=config.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get events collection
            self.events_collection = self.client.get_or_create_collection(
                name=config.CHROMA_COLLECTION_EVENTS,
                metadata={"description": "City events for semantic search"}
            )
            
            # Create or get users collection for preference matching
            self.users_collection = self.client.get_or_create_collection(
                name=config.CHROMA_COLLECTION_USERS,
                metadata={"description": "User preferences for personalization"}
            )
            
            logger.info("ChromaDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _initialize_gemini(self):
        """Initialize Gemini for embedding generation"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            logger.info("Gemini client initialized for embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini"""
        try:
            # Use Gemini's embedding model
            model = 'models/embedding-001'
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="semantic_similarity"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fallback to a zero vector if embedding fails
            return [0.0] * 768  # Gemini embedding dimension
    
    def _prepare_event_text(self, event: Event) -> str:
        """Prepare event text for embedding"""
        # Combine relevant text fields for better semantic search
        text_parts = [
            event.content.title,
            event.content.description,
            event.topic.value,
            event.sub_topic,
            event.geographic_data.location.address or "",
        ]
        
        # Add AI summary if available
        if event.content.ai_summary:
            text_parts.append(event.content.ai_summary)
        
        # Add analyzed media content if available
        if event.media.analyzed_content:
            text_parts.append(event.media.analyzed_content.gemini_description)
        
        return " ".join(filter(None, text_parts))
    
    # =========================================================================
    # EVENT VECTOR OPERATIONS
    # =========================================================================
    
    async def add_event(self, event: Event) -> bool:
        """Add event to vector database"""
        try:
            # Prepare text for embedding
            event_text = self._prepare_event_text(event)
            
            # Generate embedding
            embedding = self._generate_embedding(event_text)
            
            # Prepare metadata for filtering and retrieval
            metadata = {
                "event_id": event.id,
                "topic": event.topic.value,
                "sub_topic": event.sub_topic,
                "severity": event.impact_analysis.severity.value,
                "latitude": event.geographic_data.location.lat,
                "longitude": event.geographic_data.location.lng,
                "created_at": event.temporal_data.created_at.isoformat(),
                "source": event.source.value,
                "confidence_score": event.impact_analysis.confidence_score,
                "affected_users": event.impact_analysis.affected_users_estimated
            }
            
            # Add location area info if available
            if hasattr(event.geographic_data, 'administrative_area'):
                area = event.geographic_data.administrative_area
                if area:
                    metadata.update({
                        "ward": area.get("ward", ""),
                        "zone": area.get("zone", ""),
                        "city": area.get("city", "")
                    })
            
            # Add to collection
            self.events_collection.add(
                embeddings=[embedding],
                documents=[event_text],
                metadatas=[metadata],
                ids=[event.id]
            )
            
            logger.info(f"Added event {event.id} to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding event to vector database: {e}")
            return False
    
    async def search_similar_events(self, query_text: str, 
                                  location: Optional[Coordinates] = None,
                                  topic_filter: Optional[EventTopic] = None,
                                  max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for events similar to query text"""
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Prepare where filter
            where_filter = {}
            if topic_filter:
                where_filter["topic"] = topic_filter.value
            
            # Search in events collection
            results = self.events_collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            similar_events = []
            if results['ids'] and results['ids'][0]:
                for i, event_id in enumerate(results['ids'][0]):
                    event_data = {
                        "event_id": event_id,
                        "similarity_score": 1 - results['distances'][0][i],  # Convert distance to similarity
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i]
                    }
                    
                    # Filter by location if specified
                    if location:
                        event_lat = event_data["metadata"]["latitude"]
                        event_lng = event_data["metadata"]["longitude"]
                        distance = self._calculate_distance(
                            location.lat, location.lng, event_lat, event_lng
                        )
                        if distance <= config.DEFAULT_LOCATION_RADIUS_KM:
                            event_data["distance_km"] = distance
                            similar_events.append(event_data)
                    else:
                        similar_events.append(event_data)
            
            return similar_events
            
        except Exception as e:
            logger.error(f"Error searching similar events: {e}")
            return []
    
    async def get_events_by_semantic_query(self, query: str,
                                         user_location: Optional[Coordinates] = None,
                                         radius_km: float = 5,
                                         max_results: int = 5) -> List[str]:
        """Get event IDs matching semantic query within location radius"""
        try:
            # First get similar events
            similar_events = await self.search_similar_events(
                query_text=query,
                location=user_location,
                max_results=max_results * 2  # Get more to filter by location
            )
            
            # Filter by location if specified
            if user_location:
                filtered_events = []
                for event in similar_events:
                    if event.get("distance_km", float('inf')) <= radius_km:
                        filtered_events.append(event)
                similar_events = filtered_events
            
            # Return top event IDs
            return [event["event_id"] for event in similar_events[:max_results]]
            
        except Exception as e:
            logger.error(f"Error getting events by semantic query: {e}")
            return []
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _calculate_distance(self, lat1: float, lng1: float, 
                          lat2: float, lng2: float) -> float:
        """Calculate distance between two points using haversine formula"""
        import math
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        return c * r
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collections"""
        try:
            events_count = self.events_collection.count()
            users_count = self.users_collection.count()
            
            return {
                "events_count": events_count,
                "users_count": users_count,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"status": "error", "error": str(e)}
    
    async def health_check(self) -> bool:
        """Check if ChromaDB is healthy"""
        try:
            # Try to get collection stats
            stats = await self.get_collection_stats()
            return stats.get("status") == "healthy"
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False

# Singleton instance
chroma_client = ChromaDBClient()
