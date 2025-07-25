# data/database/firestore_client.py
"""
Firestore client for subcategory management and persistence
Handles atomic operations and maintains data consistency
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

try:
    from google.cloud import firestore
    from google.cloud.firestore import AsyncClient, AsyncTransaction
    from google.api_core import exceptions as gcp_exceptions
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    logging.warning("Firestore SDK not available - using mock implementation")

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from data.models.subcategory_schemas import (
    Subcategory, SubcategoryFirestoreDocument, SubcategorySource, 
    SubcategoryStatus, ClassificationResult, SubcategoryAnalytics,
    TopicSubcategoryDistribution, SubcategoryUsageStats
)
from data.models.schemas import EventTopic

logger = logging.getLogger(__name__)


class FirestoreSubcategoryClient:
    """Async Firestore client for subcategory management"""
    
    def __init__(self):
        self.db: Optional[AsyncClient] = None
        self._initialized = False
        
        # Collection names
        self.SUBCATEGORIES_COLLECTION = "subcategories"
        self.SUBCATEGORY_ANALYTICS_COLLECTION = "subcategory_analytics"
        self.SUBCATEGORY_RELATIONSHIPS_COLLECTION = "subcategory_relationships"
        
    async def initialize(self) -> bool:
        """Initialize Firestore connection"""
        if self._initialized:
            return True
            
        try:
            if not FIRESTORE_AVAILABLE:
                logger.warning("Using mock Firestore implementation")
                self._mock_data = {}
                self._initialized = True
                return True
                
            if not config.FIREBASE_PROJECT_ID:
                raise ValueError("FIREBASE_PROJECT_ID not configured")
                
            self.db = firestore.AsyncClient(project=config.FIREBASE_PROJECT_ID)
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            logger.info("✅ Firestore subcategory client initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore client: {e}")
            return False
    
    async def _test_connection(self):
        """Test Firestore connection"""
        if not FIRESTORE_AVAILABLE:
            return True
            
        try:
            # Try to read from subcategories collection
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).limit(1)
            async for _ in doc_ref.stream():
                break
            return True
        except Exception as e:
            logger.error(f"Firestore connection test failed: {e}")
            raise
    
    # =========================================================================
    # SUBCATEGORY CRUD OPERATIONS
    # =========================================================================
    
    async def create_subcategory(self, subcategory: Subcategory) -> bool:
        """Create a new subcategory with atomic transaction"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE:
                return await self._mock_create_subcategory(subcategory)
                
            # Use transaction for atomicity
            async def transaction_func(transaction):
                return await self._create_subcategory_transaction(transaction, subcategory)
            
            return await self.db.transaction(transaction_func)
            
        except Exception as e:
            logger.error(f"Error creating subcategory {subcategory.name}: {e}")
            return False
    
    async def _create_subcategory_transaction(self, transaction: AsyncTransaction, 
                                           subcategory: Subcategory) -> bool:
        """Atomic transaction for subcategory creation"""
        try:
            # Check if subcategory already exists
            existing = await self._get_subcategory_by_name(
                subcategory.topic, subcategory.name, transaction
            )
            if existing:
                logger.warning(f"Subcategory {subcategory.name} already exists")
                return False
            
            # Create Firestore document
            doc_data = SubcategoryFirestoreDocument.from_subcategory(subcategory)
            
            # Set document in transaction
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).document(subcategory.id)
            transaction.set(doc_ref, doc_data.dict())
            
            # Update analytics collection
            await self._update_analytics_on_create(transaction, subcategory)
            
            logger.info(f"✅ Created subcategory: {subcategory.name} ({subcategory.id})")
            return True
            
        except Exception as e:
            logger.error(f"Transaction failed for subcategory creation: {e}")
            raise
    
    async def get_subcategory(self, subcategory_id: str) -> Optional[Subcategory]:
        """Get subcategory by ID"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE:
                return self._mock_data.get(subcategory_id)
                
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).document(subcategory_id)
            doc = await doc_ref.get()
            
            if not doc.exists:
                return None
                
            doc_data = SubcategoryFirestoreDocument(**doc.to_dict())
            return doc_data.to_subcategory(subcategory_id)
            
        except Exception as e:
            logger.error(f"Error getting subcategory {subcategory_id}: {e}")
            return None
    
    async def get_subcategories_by_topic(self, topic: EventTopic, 
                                       status: Optional[SubcategoryStatus] = None) -> List[Subcategory]:
        """Get all subcategories for a topic"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE:
                return [sc for sc in self._mock_data.values() 
                       if sc.topic == topic and (not status or sc.status == status)]
                
            query = self.db.collection(self.SUBCATEGORIES_COLLECTION).where(
                "topic", "==", topic.value
            )
            
            if status:
                query = query.where("status", "==", status.value)
            
            subcategories = []
            async for doc in query.stream():
                doc_data = SubcategoryFirestoreDocument(**doc.to_dict())
                subcategories.append(doc_data.to_subcategory(doc.id))
            
            return subcategories
            
        except Exception as e:
            logger.error(f"Error getting subcategories for topic {topic}: {e}")
            return []
    
    async def update_subcategory_usage(self, subcategory_id: str, 
                                     confidence_score: Optional[float] = None,
                                     user_confirmed: bool = False,
                                     user_rejected: bool = False) -> bool:
        """Update subcategory usage statistics atomically"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE:
                subcategory = self._mock_data.get(subcategory_id)
                if subcategory:
                    subcategory.update_metadata(confidence_score, user_confirmed, user_rejected)
                return subcategory is not None
                
            # Use transaction for atomic updates
            async def transaction_func(transaction):
                return await self._update_usage_transaction(
                    transaction, subcategory_id, confidence_score, user_confirmed, user_rejected
                )
            
            return await self.db.transaction(transaction_func)
            
        except Exception as e:
            logger.error(f"Error updating subcategory usage {subcategory_id}: {e}")
            return False
    
    async def _update_usage_transaction(self, transaction: AsyncTransaction,
                                      subcategory_id: str, confidence_score: Optional[float],
                                      user_confirmed: bool, user_rejected: bool) -> bool:
        """Atomic transaction for usage updates"""
        try:
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).document(subcategory_id)
            doc = await transaction.get(doc_ref)
            
            if not doc.exists:
                return False
            
            # Get current data
            doc_data = SubcategoryFirestoreDocument(**doc.to_dict())
            subcategory = doc_data.to_subcategory(subcategory_id)
            
            # Update metadata
            subcategory.update_metadata(confidence_score, user_confirmed, user_rejected)
            
            # Convert back to Firestore format
            updated_doc = SubcategoryFirestoreDocument.from_subcategory(subcategory)
            
            # Update document
            transaction.update(doc_ref, updated_doc.dict())
            
            logger.debug(f"Updated usage for subcategory: {subcategory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Usage update transaction failed: {e}")
            raise
    
    # =========================================================================
    # SEARCH AND CLASSIFICATION SUPPORT
    # =========================================================================
    
    async def search_similar_subcategories(self, topic: EventTopic, query_text: str,
                                         max_results: int = 10) -> List[Tuple[Subcategory, float]]:
        """Search for similar subcategories using text similarity"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Get all subcategories for topic
            subcategories = await self.get_subcategories_by_topic(topic, SubcategoryStatus.ACTIVE)
            
            # Simple text-based similarity (in production, use vector embeddings)
            results = []
            query_lower = query_text.lower()
            
            for subcategory in subcategories:
                # Calculate similarity score
                score = 0.0
                
                # Exact name match
                if subcategory.name.lower() == query_lower:
                    score = 1.0
                # Name contains query
                elif query_lower in subcategory.name.lower():
                    score = 0.8
                # Display name match
                elif query_lower in subcategory.display_name.lower():
                    score = 0.6
                # Alias match
                elif any(query_lower in alias.lower() for alias in subcategory.relationships.aliases):
                    score = 0.7
                # Description match
                elif subcategory.description and query_lower in subcategory.description.lower():
                    score = 0.4
                
                if score > 0:
                    results.append((subcategory, score))
            
            # Sort by score and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching subcategories: {e}")
            return []
    
    async def get_or_create_subcategory(self, topic: EventTopic, name: str,
                                      display_name: Optional[str] = None,
                                      description: Optional[str] = None,
                                      source: SubcategorySource = SubcategorySource.AI_GENERATED,
                                      created_by: Optional[str] = None) -> Tuple[Subcategory, bool]:
        """Get existing subcategory or create new one atomically"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # First try to find existing
            existing = await self._find_subcategory_by_name_or_alias(topic, name)
            if existing:
                return existing, False
            
            # Create new subcategory
            new_subcategory = Subcategory(
                name=name.lower().strip(),
                topic=topic,
                display_name=display_name or name.title(),
                description=description,
                source=source,
                created_by=created_by
            )
            
            success = await self.create_subcategory(new_subcategory)
            if success:
                return new_subcategory, True
            else:
                # Might have been created by another process, try to get it
                existing = await self._find_subcategory_by_name_or_alias(topic, name)
                if existing:
                    return existing, False
                raise Exception("Failed to create subcategory")
                
        except Exception as e:
            logger.error(f"Error in get_or_create_subcategory: {e}")
            raise
    
    async def _find_subcategory_by_name_or_alias(self, topic: EventTopic, name: str) -> Optional[Subcategory]:
        """Find subcategory by name or alias"""
        subcategories = await self.get_subcategories_by_topic(topic, SubcategoryStatus.ACTIVE)
        name_lower = name.lower().strip()
        
        for subcategory in subcategories:
            if subcategory.name == name_lower:
                return subcategory
            if name_lower in [alias.lower() for alias in subcategory.relationships.aliases]:
                return subcategory
        
        return None
    
    async def _get_subcategory_by_name(self, topic: EventTopic, name: str,
                                     transaction: Optional[AsyncTransaction] = None) -> Optional[Subcategory]:
        """Get subcategory by name within transaction"""
        if not FIRESTORE_AVAILABLE:
            return await self._find_subcategory_by_name_or_alias(topic, name)
            
        try:
            query = self.db.collection(self.SUBCATEGORIES_COLLECTION).where(
                "topic", "==", topic.value
            ).where("name", "==", name.lower().strip())
            
            if transaction:
                docs = [doc async for doc in transaction.get(query)]
            else:
                docs = [doc async for doc in query.stream()]
            
            if docs:
                doc = docs[0]
                doc_data = SubcategoryFirestoreDocument(**doc.to_dict())
                return doc_data.to_subcategory(doc.id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subcategory by name: {e}")
            return None
    
    # =========================================================================
    # ANALYTICS AND REPORTING
    # =========================================================================
    
    async def get_subcategory_analytics(self) -> Optional[SubcategoryAnalytics]:
        """Generate comprehensive subcategory analytics"""
        if not self._initialized:
            await self.initialize()
            
        try:
            analytics_data = {
                "total_subcategories": 0,
                "by_topic": [],
                "by_source": {},
                "by_status": {},
                "avg_confidence_scores": {},
                "top_performing": [],
                "needs_review": [],
            }
            
            # Get analytics for each topic
            for topic in EventTopic:
                topic_analytics = await self._get_topic_analytics(topic)
                analytics_data["by_topic"].append(topic_analytics)
                analytics_data["total_subcategories"] += topic_analytics.total_subcategories
            
            return SubcategoryAnalytics(**analytics_data)
            
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return None
    
    async def _get_topic_analytics(self, topic: EventTopic) -> TopicSubcategoryDistribution:
        """Get analytics for a specific topic"""
        subcategories = await self.get_subcategories_by_topic(topic)
        
        active_count = len([sc for sc in subcategories if sc.status == SubcategoryStatus.ACTIVE])
        
        # Sort by usage for most/least used
        usage_stats = []
        for sc in subcategories:
            if sc.metadata.usage_count > 0:
                satisfaction_rate = 0.0
                total_feedback = sc.metadata.user_confirmations + sc.metadata.user_rejections
                if total_feedback > 0:
                    satisfaction_rate = sc.metadata.user_confirmations / total_feedback
                
                stats = SubcategoryUsageStats(
                    subcategory_id=sc.id,
                    subcategory_name=sc.name,
                    topic=topic,
                    total_usage=sc.metadata.usage_count,
                    usage_last_7_days=0,  # Would need temporal tracking
                    usage_last_30_days=0,  # Would need temporal tracking
                    avg_confidence=sc.metadata.avg_confidence or 0.0,
                    user_satisfaction_rate=satisfaction_rate,
                    trend="stable"  # Would need historical data
                )
                usage_stats.append(stats)
        
        usage_stats.sort(key=lambda x: x.total_usage, reverse=True)
        
        return TopicSubcategoryDistribution(
            topic=topic,
            total_subcategories=len(subcategories),
            active_subcategories=active_count,
            most_used_subcategories=usage_stats[:5],
            least_used_subcategories=[sc.id for sc in subcategories if sc.metadata.usage_count == 0][:5],
            newly_created_count=len([sc for sc in subcategories 
                                   if sc.created_at > datetime.utcnow() - timedelta(days=30)])
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _update_analytics_on_create(self, transaction: AsyncTransaction, subcategory: Subcategory):
        """Update analytics when a new subcategory is created"""
        # In a full implementation, this would update aggregate analytics documents
        pass
    
    async def health_check(self) -> bool:
        """Check Firestore connection health"""
        if not self._initialized:
            return False
            
        try:
            if not FIRESTORE_AVAILABLE:
                return True
            
            await self._test_connection()
            return True
        except Exception:
            return False
    
    # =========================================================================
    # MOCK IMPLEMENTATION FOR DEVELOPMENT
    # =========================================================================
    
    async def _mock_create_subcategory(self, subcategory: Subcategory) -> bool:
        """Mock implementation for development"""
        if subcategory.id in self._mock_data:
            return False
        self._mock_data[subcategory.id] = subcategory
        logger.info(f"🔧 Mock: Created subcategory {subcategory.name}")
        return True


# Singleton instance
firestore_subcategory_client = FirestoreSubcategoryClient()
