import firebase_admin
from firebase_admin import credentials, storage
from typing import List, Optional, Tuple
import logging
import uuid
import os
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class FirebaseStorageClient:
    """Firebase Storage client for handling media uploads"""
    
    def __init__(self):
        self.bucket = None
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize Firebase Storage"""
        try:
            # Initialize Firebase if not already done
            if not firebase_admin._apps:
                # For development, use default credentials
                firebase_admin.initialize_app(options={
                    'storageBucket': config.FIREBASE_STORAGE_BUCKET or f"{config.FIREBASE_PROJECT_ID}.appspot.com"
                })
            
            # Get storage bucket
            self.bucket = storage.bucket()
            logger.info("Firebase Storage initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Storage: {e}")
            # For POC, we'll work without Firebase Storage
            self.bucket = None
    
    async def upload_media(self, file_data: bytes, file_name: str, 
                          content_type: str, user_id: str, event_id: str) -> Optional[str]:
        """Upload media file to Firebase Storage"""
        try:
            if not self.bucket:
                # Return mock URL for POC
                return f"gs://mock-bucket/media/{event_id}/{file_name}"
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"media/{user_id}/{event_id}/{timestamp}_{file_name}"
            
            # Upload file
            blob = self.bucket.blob(unique_filename)
            blob.upload_from_string(file_data, content_type=content_type)
            
            # Make publicly readable (for demo purposes)
            blob.make_public()
            
            # Return public URL
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    async def delete_media(self, file_url: str) -> bool:
        """Delete media file from Firebase Storage"""
        try:
            if not self.bucket or file_url.startswith("gs://mock-bucket"):
                return True  # Mock deletion
            
            # Extract blob name from URL
            blob_name = file_url.split(f"{self.bucket.name}/")[-1]
            blob = self.bucket.blob(blob_name)
            blob.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting media: {e}")
            return False
    
    def get_supported_formats(self) -> dict:
        """Get supported media formats"""
        return {
            "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
            "videos": [".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv"],
            "max_size_mb": 50,
            "max_files": 5
        }

# Singleton instance
storage_client = FirebaseStorageClient()
