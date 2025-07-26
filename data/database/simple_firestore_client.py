# data/database/simple_firestore_client.py
"""
Simplified Firestore client for subcategory management
Focuses on basic operations without complex transactions for initial setup
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

try:
    from google.cloud import firestore
    from google.cloud.firestore import AsyncClient
    from google.api_core import exceptions as gcp_exceptions
    from google.oauth2 import service_account
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


class SimpleFirestoreSubcategoryClient:
    """Simplified async Firestore client for subcategory management"""
    
    def __init__(self):
        self.db: Optional[AsyncClient] = None
        self._initialized = False
        
        # Collection names
        self.SUBCATEGORIES_COLLECTION = "subcategories"
        
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
            
            # Try file-based credentials first
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                logger.info("Initializing Firestore with credentials file")
                if not config.FIREBASE_PROJECT_ID:
                    raise ValueError("FIREBASE_PROJECT_ID not configured")
                self.db = firestore.AsyncClient(project=config.FIREBASE_PROJECT_ID)
            else:
                # Fall back to environment variables
                firebase_project_id = os.getenv('FIREBASE_PROJECT_ID')
                firebase_private_key = os.getenv('FIREBASE_PRIVATE_KEY')
                firebase_client_email = os.getenv('FIREBASE_CLIENT_EMAIL')
                
                if firebase_project_id and firebase_private_key and firebase_client_email:
                    logger.info("Initializing Firestore with environment variables")
                    
                    creds_dict = {
                        "type": os.getenv('FIREBASE_TYPE', 'service_account'),
                        "project_id": firebase_project_id,
                        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                        "private_key": firebase_private_key,
                        "client_email": firebase_client_email,
                        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                        "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                        "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                        "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
                        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
                        "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com')
                    }
                    
                    # Remove None values
                    creds_dict = {k: v for k, v in creds_dict.items() if v is not None}
                    
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    self.db = firestore.AsyncClient(project=firebase_project_id, credentials=credentials)
                else:
                    logger.warning("Firestore credentials not found in file or environment variables")
                    logger.warning("Using mock Firestore implementation")
                    self._mock_data = {}
                    self._initialized = True
                    return True
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            logger.info("✅ Simple Firestore subcategory client initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore client: {e}")
            # Fall back to mock implementation
            logger.warning("Falling back to mock Firestore implementation")
            self._mock_data = {}
            self._initialized = True
            return True
    
    async def _test_connection(self):
        """Test Firestore connection"""
        if not FIRESTORE_AVAILABLE or not self.db:
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
    # SIMPLE SUBCATEGORY CRUD OPERATIONS
    # =========================================================================
    
    async def create_subcategory(self, subcategory: Subcategory) -> bool:
        """Create a new subcategory (simplified without transactions)"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE or not self.db:
                return await self._mock_create_subcategory(subcategory)
                
            # Check if subcategory already exists
            existing = await self._get_subcategory_by_name(subcategory.topic, subcategory.name)
            if existing:
                logger.info(f"Subcategory {subcategory.name} already exists")
                return True  # Consider it success if it already exists
            
            # Create Firestore document
            doc_data = SubcategoryFirestoreDocument.from_subcategory(subcategory)
            
            # Set document directly (no transaction for simplicity)
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).document(subcategory.id)
            await doc_ref.set(doc_data.dict())
            
            logger.info(f"✅ Created subcategory: {subcategory.name} ({subcategory.id})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating subcategory {subcategory.name}: {e}")
            return False
    
    async def get_subcategory(self, subcategory_id: str) -> Optional[Subcategory]:
        """Get subcategory by ID"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE or not self.db:
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
            if not FIRESTORE_AVAILABLE or not self.db:
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
        """Update subcategory usage statistics (simplified)"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if not FIRESTORE_AVAILABLE or not self.db:
                subcategory = self._mock_data.get(subcategory_id)
                if subcategory:
                    subcategory.update_metadata(confidence_score, user_confirmed, user_rejected)
                return subcategory is not None
                
            # Get current subcategory
            subcategory = await self.get_subcategory(subcategory_id)
            if not subcategory:
                return False
            
            # Update metadata
            subcategory.update_metadata(confidence_score, user_confirmed, user_rejected)
            
            # Save back to Firestore
            doc_data = SubcategoryFirestoreDocument.from_subcategory(subcategory)
            doc_ref = self.db.collection(self.SUBCATEGORIES_COLLECTION).document(subcategory_id)
            await doc_ref.update(doc_data.dict())
            
            logger.debug(f"Updated usage for subcategory: {subcategory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subcategory usage {subcategory_id}: {e}")
            return False
    
    async def get_or_create_subcategory(self, topic: EventTopic, name: str,
                                      display_name: Optional[str] = None,
                                      description: Optional[str] = None,
                                      source: SubcategorySource = SubcategorySource.AI_GENERATED,
                                      created_by: Optional[str] = None) -> Tuple[Subcategory, bool]:
        """Get existing subcategory or create new one"""
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
    
    async def _get_subcategory_by_name(self, topic: EventTopic, name: str) -> Optional[Subcategory]:
        """Get subcategory by name"""
        if not FIRESTORE_AVAILABLE or not self.db:
            return await self._find_subcategory_by_name_or_alias(topic, name)
            
        try:
            query = self.db.collection(self.SUBCATEGORIES_COLLECTION).where(
                "topic", "==", topic.value
            ).where("name", "==", name.lower().strip())
            
            docs = [doc async for doc in query.stream()]
            
            if docs:
                doc = docs[0]
                doc_data = SubcategoryFirestoreDocument(**doc.to_dict())
                return doc_data.to_subcategory(doc.id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subcategory by name: {e}")
            return None
    
    async def search_similar_subcategories(self, topic: EventTopic, query_text: str,
                                         max_results: int = 10) -> List[Tuple[Subcategory, float]]:
        """Search for similar subcategories using text similarity"""
        try:
            # Get all subcategories for topic
            subcategories = await self.get_subcategories_by_topic(topic, SubcategoryStatus.ACTIVE)
            
            # Simple text-based similarity
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
    
    async def health_check(self) -> bool:
        """Check Firestore connection health"""
        if not self._initialized:
            return False
            
        try:
            if not FIRESTORE_AVAILABLE or not self.db:
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
        if not hasattr(self, '_mock_data'):
            self._mock_data = {}
            
        if subcategory.id in self._mock_data:
            return True  # Already exists, consider success
        self._mock_data[subcategory.id] = subcategory
        logger.info(f"🔧 Mock: Created subcategory {subcategory.name}")
        return True


# Singleton instance
simple_firestore_client = SimpleFirestoreSubcategoryClient()