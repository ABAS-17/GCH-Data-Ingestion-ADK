"""
Simplified storage client that works without Firebase
For hackathon/demo purposes
"""

from typing import List, Optional, Dict, Any
import logging
import uuid
import os
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class MockStorageClient:
    """Mock storage client for development/demo without Firebase"""
    
    def __init__(self):
        self.mock_storage = {}  # In-memory storage for demo
        logger.info("Mock Storage client initialized (no Firebase required)")
    
    async def upload_media(self, file_data: bytes, file_name: str, 
                          content_type: str, user_id: str, event_id: str) -> Optional[str]:
        """Mock upload media file"""
        try:
            # Generate mock URL
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            mock_url = f"gs://demo-bucket/media/{user_id}/{event_id}/{timestamp}_{file_name}"
            
            # Store in mock storage
            self.mock_storage[mock_url] = {
                "data": file_data,
                "content_type": content_type,
                "size": len(file_data),
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Mock uploaded: {file_name} -> {mock_url}")
            return mock_url
            
        except Exception as e:
            logger.error(f"Error in mock upload: {e}")
            return None
    
    async def delete_media(self, file_url: str) -> bool:
        """Mock delete media file"""
        try:
            if file_url in self.mock_storage:
                del self.mock_storage[file_url]
                logger.info(f"Mock deleted: {file_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error in mock deletion: {e}")
            return False
    
    def get_supported_formats(self) -> dict:
        """Get supported media formats"""
        return {
            "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
            "videos": [".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv"],
            "max_size_mb": 50,
            "max_files": 5
        }
    
    def get_storage_stats(self) -> dict:
        """Get mock storage statistics"""
        total_files = len(self.mock_storage)
        total_size = sum(item["size"] for item in self.mock_storage.values())
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_type": "mock"
        }

# Use mock storage client
storage_client = MockStorageClient()
