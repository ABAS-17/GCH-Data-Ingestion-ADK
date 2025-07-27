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
            if not firebase_admin._apps:
                # Try file-based credentials first
                creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if creds_path and os.path.exists(creds_path):
                    logger.info("Initializing Firebase with credentials file")
                    firebase_admin.initialize_app(options={
                        'storageBucket': config.FIREBASE_STORAGE_BUCKET or f"{config.FIREBASE_PROJECT_ID}.appspot.com"
                    })
                else:
                    # Fall back to environment variables
                    firebase_project_id = os.getenv('FIREBASE_PROJECT_ID')
                    firebase_private_key = os.getenv('FIREBASE_PRIVATE_KEY')
                    firebase_client_email = os.getenv('FIREBASE_CLIENT_EMAIL')
                    
                    if firebase_project_id and firebase_private_key and firebase_client_email:
                        logger.info("Initializing Firebase with environment variables")
                        
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
                        
                        cred = credentials.Certificate(creds_dict)
                        firebase_admin.initialize_app(cred, options={
                            'storageBucket': config.FIREBASE_STORAGE_BUCKET or f"{firebase_project_id}.appspot.com"
                        })
                    else:
                        logger.warning("Firebase credentials not found in file or environment variables")
                        self.bucket = None
                        return
            
            # Get storage bucket
            self.bucket = storage.bucket()
            logger.info("✅ Firebase Storage initialized successfully")
            
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
                logger.warning("Firebase Storage not available, returning mock URL")
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
            logger.info(f"✅ Media uploaded successfully: {unique_filename}")
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
            
            logger.info(f"✅ Media deleted successfully: {blob_name}")
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
    
    def health_check(self) -> bool:
        """Check if Firebase Storage is available"""
        return self.bucket is not None

# Singleton instance
storage_client = FirebaseStorageClient()