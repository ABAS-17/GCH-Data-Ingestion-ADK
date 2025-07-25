# Enhanced API models for media support
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Union
from datetime import datetime
import uuid

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from schemas import EventTopic, EventSeverity, Coordinates

# ============================================================================
# ENHANCED MEDIA MODELS
# ============================================================================

class MediaFile(BaseModel):
    """Model for uploaded media files"""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="MIME type (image/jpeg, video/mp4, etc.)")
    size_bytes: int = Field(..., gt=0, le=50*1024*1024, description="File size in bytes")
    data: Optional[bytes] = Field(None, description="File data for upload")
    url: Optional[str] = Field(None, description="URL after upload")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp',
            'video/mp4', 'video/avi', 'video/mov', 'video/webm', 'video/mkv'
        ]
        if v not in allowed_types:
            raise ValueError(f'Content type {v} not supported. Allowed: {allowed_types}')
        return v
    
    @validator('filename')
    def validate_filename(cls, v):
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', 
                            '.mp4', '.avi', '.mov', '.webm', '.mkv']
        ext = '.' + v.split('.')[-1].lower() if '.' in v else ''
        if ext not in allowed_extensions:
            raise ValueError(f'File extension {ext} not supported')
        return v

class EnhancedEventCreateRequest(BaseModel):
    """Enhanced event creation with comprehensive media support"""
    topic: EventTopic
    sub_topic: str
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    location: Union[Coordinates, Dict[str, float]]
    address: Optional[str] = None
    severity: EventSeverity = EventSeverity.MEDIUM
    
    # Enhanced media support
    media_files: List[MediaFile] = Field(default_factory=list, max_items=5)
    media_urls: List[str] = Field(default_factory=list, max_items=5, description="URLs of already uploaded media")
    
    # Additional context
    reporter_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('location')
    def validate_location(cls, v):
        if isinstance(v, dict):
            if 'lat' in v and 'lng' in v:
                return Coordinates(lat=v['lat'], lng=v['lng'])
            else:
                raise ValueError('Location dict must contain lat and lng keys')
        elif isinstance(v, Coordinates):
            return v
        else:
            raise ValueError('Location must be Coordinates object or dict with lat/lng')
    
    @validator('media_files')
    def validate_media_count(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 media files allowed per incident')
        return v
    
    class Config:
        json_encoders = {
            bytes: lambda v: v.decode('utf-8') if v else None
        }

class MediaUploadResponse(BaseModel):
    """Response model for media upload"""
    success: bool
    uploaded_files: List[Dict[str, str]] = Field(default_factory=list)
    failed_files: List[Dict[str, str]] = Field(default_factory=list)
    total_uploaded: int = 0
    storage_urls: List[str] = Field(default_factory=list)
    
class MediaAnalysisResponse(BaseModel):
    """Response model for media analysis"""
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    media_url: str
    media_type: str
    analysis_results: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# ENHANCED CHAT MODELS
# ============================================================================

class ChatWithMediaRequest(BaseModel):
    """Chat request that can include media context"""
    user_id: str
    message: str = Field(..., min_length=1, max_length=1000)
    location: Optional[Coordinates] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Media context for the conversation
    media_references: List[str] = Field(default_factory=list, description="URLs of media being discussed")
    include_media_analysis: bool = Field(default=False, description="Whether to analyze referenced media")

class EnhancedChatResponse(BaseModel):
    """Enhanced chat response with media insights"""
    message_id: str
    response: str
    suggestions: List[str] = Field(default_factory=list)
    referenced_events: List[str] = Field(default_factory=list)
    media_insights: Optional[Dict[str, Any]] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# INCIDENT REPORTING WORKFLOW MODELS
# ============================================================================

class IncidentReport(BaseModel):
    """Complete incident report with all information"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    basic_info: EnhancedEventCreateRequest
    media_analysis: List[MediaAnalysisResponse] = Field(default_factory=list)
    ai_classification: Optional[Dict[str, Any]] = Field(default=None)
    processing_status: str = Field(default="pending", description="pending, processing, completed, failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class IncidentReportStatus(BaseModel):
    """Status of incident report processing"""
    report_id: str
    status: str  # pending, uploading_media, analyzing_media, classifying, storing, completed, failed
    progress_percentage: int = Field(..., ge=0, le=100)
    current_step: str
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

# ============================================================================
# MEDIA MANAGEMENT MODELS
# ============================================================================

class MediaLibraryItem(BaseModel):
    """Item in user's media library"""
    media_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    media_type: str  # image, video
    content_type: str
    size_bytes: int
    storage_url: str
    thumbnail_url: Optional[str] = None
    
    # Analysis results
    ai_analysis: Optional[Dict[str, Any]] = Field(default=None)
    analysis_timestamp: Optional[datetime] = None
    
    # Usage tracking
    used_in_reports: List[str] = Field(default_factory=list, description="List of report IDs")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None

class MediaLibraryResponse(BaseModel):
    """Response for media library queries"""
    total_items: int
    items: List[MediaLibraryItem]
    page: int
    per_page: int
    total_pages: int
    storage_used_mb: float

# ============================================================================
# BATCH PROCESSING MODELS
# ============================================================================

class BatchMediaProcessingRequest(BaseModel):
    """Request for batch processing multiple media files"""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    media_files: List[MediaFile] = Field(..., min_items=1, max_items=20)
    processing_options: Dict[str, Any] = Field(default_factory=dict)

class BatchProcessingStatus(BaseModel):
    """Status of batch media processing"""
    batch_id: str
    total_files: int
    processed_files: int
    failed_files: int
    status: str  # queued, processing, completed, failed
    results: List[MediaAnalysisResponse] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
