import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import sys
import os

# Add parent directory to path to import config  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.database.chroma_client import chroma_client
from data.processors.event_processor import event_processor
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
from data.mock_data.data_generator import mock_generator
from data.models.schemas import (
    Event, User, UserConversation, EventTopic, 
    Coordinates, EventCreateRequest
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Unified interface for all database operations"""
    
    def __init__(self):
        self.chroma = chroma_client
        self.processor = event_processor
        self.enhanced_processor = enhanced_subcategory_processor
        self.mock_gen = mock_generator
    
    # =========================================================================
    # INITIALIZATION & SETUP
    # =========================================================================
    
    async def initialize_databases(self) -> bool:
        """Initialize all database connections"""
        try:
            # Check health of ChromaDB
            chroma_healthy = await self.chroma.health_check()
            
            logger.info(f"Database health - ChromaDB: {chroma_healthy}")
            
            return chroma_healthy
            
        except Exception as e:
            logger.error(f"Error initializing databases: {e}")
            return False
    
    async def populate_mock_data(self, events_count: int = 50, users_count: int = 10) -> bool:
        """Populate databases with mock data for demo"""
        try:
            logger.info(f"Generating {events_count} events and {users_count} users")
            
            # Generate mock events
            events = self.mock_gen.generate_events(events_count)
            
            # Save events to ChromaDB
            for i, event in enumerate(events):
                success = await self.chroma.add_event(event)
                if success:
                    logger.info(f"Added event {i+1}/{len(events)}: {event.content.title}")
                else:
                    logger.warning(f"Failed to add event {i+1}")
            
            # Generate mock users
            users = self.mock_gen.generate_users(users_count)
            
            # Generate conversations for each user
            for user in users:
                conversation = self.mock_gen.generate_conversation(user.id)
                logger.info(f"Generated conversation for user: {user.profile.name}")
            
            logger.info(f"Successfully populated mock data: {len(events)} events, {len(users)} users")
            return True
            
        except Exception as e:
            logger.error(f"Error populating mock data: {e}")
            return False
    
    # =========================================================================
    # EVENT OPERATIONS
    # =========================================================================
    
    async def create_event(self, event: Event) -> str:
        """Create event in ChromaDB"""
        try:
            # Add to vector database for semantic search
            success = await self.chroma.add_event(event)
            
            if success:
                logger.info(f"Created event: {event.id}")
                return event.id
            else:
                raise Exception("Failed to add event to ChromaDB")
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
    
    async def process_user_report(self, report: EventCreateRequest, user_id: str) -> Event:
        """Process user-submitted report into a complete event"""
        try:
            # Process the report using AI
            event = await self.processor.process_user_report(
                title=report.title,
                description=report.description,
                location=report.location,
                address=report.address,
                media_urls=report.media_urls
            )
            
            # Override severity if specified
            if report.severity:
                event.impact_analysis.severity = report.severity
            
            # Save the event
            event_id = await self.create_event(event)
            
            logger.info(f"Processed user report from {user_id} into event {event_id}")
            return event
            
        except Exception as e:
            logger.error(f"Error processing user report: {e}")
            raise
    
    async def search_events_semantically(self, query: str, 
                                       user_location: Optional[Coordinates] = None,
                                       max_results: int = 10) -> List[Dict[str, Any]]:
        """Search events using semantic similarity"""
        try:
            # Get similar events from ChromaDB
            similar_events = await self.chroma.search_similar_events(
                query_text=query,
                location=user_location,
                max_results=max_results
            )
            
            return similar_events
            
        except Exception as e:
            logger.error(f"Error in semantic event search: {e}")
            return []
    
    # =========================================================================
    # ANALYTICS & INSIGHTS
    # =========================================================================
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        try:
            # Get collection stats from ChromaDB
            chroma_stats = await self.chroma.get_collection_stats()
            
            return {
                "chroma_db": chroma_stats,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all database services"""
        return {
            "chroma_db": await self.chroma.health_check()
        }

# Singleton instance
db_manager = DatabaseManager()
