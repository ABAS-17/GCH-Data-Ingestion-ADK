# data/models/subcategory_schemas.py
"""
Enhanced Subcategory Management Models with Dynamic Classification
Supports both predefined and AI-generated subcategories with Firestore persistence
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid

from .schemas import EventTopic


# ============================================================================
# SUBCATEGORY MANAGEMENT ENUMS
# ============================================================================

class SubcategorySource(str, Enum):
    """Source of subcategory creation"""
    PREDEFINED = "predefined"          # System-defined subcategories
    AI_GENERATED = "ai_generated"      # Created by AI classification
    USER_SUBMITTED = "user_submitted"  # Created from user reports
    ADMIN_ADDED = "admin_added"        # Manually added by admin

class SubcategoryStatus(str, Enum):
    """Status of subcategory in the system"""
    ACTIVE = "active"                  # Actively used for classification
    DEPRECATED = "deprecated"          # No longer recommended but valid
    MERGED = "merged"                  # Merged into another subcategory
    PENDING_REVIEW = "pending_review"  # New subcategory awaiting approval


# ============================================================================
# CORE SUBCATEGORY MODELS
# ============================================================================

class SubcategoryMetadata(BaseModel):
    """Metadata for subcategory usage and analytics"""
    usage_count: int = Field(default=0, description="Number of times used")
    last_used: Optional[datetime] = None
    confidence_scores: List[float] = Field(default_factory=list, description="AI confidence scores")
    user_confirmations: int = Field(default=0, description="User confirmations of accuracy")
    user_rejections: int = Field(default=0, description="User rejections")
    avg_confidence: Optional[float] = None
    creation_confidence: Optional[float] = None

class SubcategoryRelationships(BaseModel):
    """Relationships between subcategories"""
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    similar_subcategories: List[str] = Field(default_factory=list, description="Related subcategory IDs")
    parent_subcategory: Optional[str] = None  # For hierarchical relationships
    child_subcategories: List[str] = Field(default_factory=list)
    merged_from: List[str] = Field(default_factory=list, description="Subcategories merged into this one")
    merged_into: Optional[str] = None  # If this subcategory was merged

class Subcategory(BaseModel):
    """Complete subcategory definition with dynamic management"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=50, description="Canonical subcategory name")
    topic: EventTopic = Field(..., description="Parent topic")
    display_name: str = Field(..., description="Human-friendly display name")
    description: Optional[str] = Field(None, max_length=200, description="Description of subcategory")
    
    # Source and status tracking
    source: SubcategorySource = Field(..., description="How this subcategory was created")
    status: SubcategoryStatus = Field(default=SubcategoryStatus.ACTIVE)
    
    # Relationships and metadata
    relationships: SubcategoryRelationships = Field(default_factory=SubcategoryRelationships)
    metadata: SubcategoryMetadata = Field(default_factory=SubcategoryMetadata)
    
    # System fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User ID or system")
    
    # Vector embedding for semantic similarity (excluded from serialization)
    embedding: Optional[List[float]] = Field(None, exclude=True)

    @validator('name')
    def validate_name(cls, v):
        """Ensure subcategory name follows naming conventions"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Subcategory name must be alphanumeric with underscores/hyphens only')
        return v.lower().strip()

    def update_metadata(self, confidence_score: Optional[float] = None, 
                       user_confirmed: bool = False, user_rejected: bool = False):
        """Update subcategory metadata based on usage"""
        self.metadata.usage_count += 1
        self.metadata.last_used = datetime.utcnow()
        
        if confidence_score is not None:
            self.metadata.confidence_scores.append(confidence_score)
            # Calculate rolling average
            recent_scores = self.metadata.confidence_scores[-10:]  # Last 10 scores
            self.metadata.avg_confidence = sum(recent_scores) / len(recent_scores)
        
        if user_confirmed:
            self.metadata.user_confirmations += 1
        if user_rejected:
            self.metadata.user_rejections += 1
        
        self.updated_at = datetime.utcnow()


# ============================================================================
# CLASSIFICATION MODELS
# ============================================================================

class ClassificationContext(BaseModel):
    """Context for AI subcategory classification"""
    event_title: str
    event_description: str
    location_context: Optional[Dict[str, Any]] = None
    media_analysis: Optional[Dict[str, Any]] = None
    user_context: Optional[Dict[str, Any]] = None
    existing_subcategories: List[str] = Field(default_factory=list)

class ClassificationResult(BaseModel):
    """Result of AI subcategory classification"""
    subcategory_name: str = Field(..., description="Classified or created subcategory name")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_new_subcategory: bool = Field(default=False)
    reasoning: Optional[str] = Field(None, description="AI reasoning for classification")
    alternative_suggestions: List[str] = Field(default_factory=list)
    
    # If new subcategory was created
    new_subcategory_id: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None

class SubcategoryClassificationRequest(BaseModel):
    """Request for subcategory classification"""
    topic: EventTopic
    context: ClassificationContext
    force_create_new: bool = Field(default=False, description="Force creation of new subcategory")
    min_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


# ============================================================================
# FIRESTORE DOCUMENT MODELS
# ============================================================================

class SubcategoryFirestoreDocument(BaseModel):
    """Firestore document structure for subcategories"""
    name: str
    topic: str  # EventTopic value
    display_name: str
    description: Optional[str] = None
    source: str  # SubcategorySource value
    status: str  # SubcategoryStatus value
    relationships: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    @classmethod
    def from_subcategory(cls, subcategory: Subcategory) -> "SubcategoryFirestoreDocument":
        """Convert Subcategory to Firestore document"""
        return cls(
            name=subcategory.name,
            topic=subcategory.topic.value,
            display_name=subcategory.display_name,
            description=subcategory.description,
            source=subcategory.source.value,
            status=subcategory.status.value,
            relationships=subcategory.relationships.dict(),
            metadata=subcategory.metadata.dict(),
            created_at=subcategory.created_at,
            updated_at=subcategory.updated_at,
            created_by=subcategory.created_by
        )

    def to_subcategory(self, subcategory_id: str) -> Subcategory:
        """Convert Firestore document to Subcategory"""
        return Subcategory(
            id=subcategory_id,
            name=self.name,
            topic=EventTopic(self.topic),
            display_name=self.display_name,
            description=self.description,
            source=SubcategorySource(self.source),
            status=SubcategoryStatus(self.status),
            relationships=SubcategoryRelationships(**self.relationships),
            metadata=SubcategoryMetadata(**self.metadata),
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by
        )


# ============================================================================
# ANALYTICS AND REPORTING MODELS
# ============================================================================

class SubcategoryUsageStats(BaseModel):
    """Analytics for subcategory usage"""
    subcategory_id: str
    subcategory_name: str
    topic: EventTopic
    total_usage: int
    usage_last_7_days: int
    usage_last_30_days: int
    avg_confidence: float
    user_satisfaction_rate: float  # confirmations / (confirmations + rejections)
    trend: str  # "increasing", "decreasing", "stable"

class TopicSubcategoryDistribution(BaseModel):
    """Distribution of subcategories within a topic"""
    topic: EventTopic
    total_subcategories: int
    active_subcategories: int
    most_used_subcategories: List[SubcategoryUsageStats]
    least_used_subcategories: List[str]
    newly_created_count: int  # In last 30 days

class SubcategoryAnalytics(BaseModel):
    """Comprehensive subcategory analytics"""
    total_subcategories: int
    by_topic: List[TopicSubcategoryDistribution]
    by_source: Dict[str, int]  # Count by SubcategorySource
    by_status: Dict[str, int]  # Count by SubcategoryStatus
    avg_confidence_scores: Dict[str, float]  # By topic
    top_performing: List[SubcategoryUsageStats]
    needs_review: List[str]  # Subcategory IDs with low confidence/high rejection
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class CreateSubcategoryRequest(BaseModel):
    """Request to create a new subcategory"""
    name: str = Field(..., min_length=1, max_length=50)
    topic: EventTopic
    display_name: str
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    force_create: bool = Field(default=False, description="Create even if similar exists")

class UpdateSubcategoryRequest(BaseModel):
    """Request to update an existing subcategory"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SubcategoryStatus] = None
    add_aliases: List[str] = Field(default_factory=list)
    remove_aliases: List[str] = Field(default_factory=list)

class SubcategorySearchRequest(BaseModel):
    """Request to search subcategories"""
    query: str
    topic: Optional[EventTopic] = None
    status: Optional[SubcategoryStatus] = None
    include_aliases: bool = Field(default=True)
    max_results: int = Field(default=10, ge=1, le=100)

class SubcategoryResponse(BaseModel):
    """Response with subcategory information"""
    success: bool
    subcategory: Optional[Subcategory] = None
    message: Optional[str] = None

class SubcategoryListResponse(BaseModel):
    """Response with list of subcategories"""
    success: bool
    subcategories: List[Subcategory]
    total_count: int
    filtered_count: int
    message: Optional[str] = None

class ClassificationResponse(BaseModel):
    """Response from subcategory classification"""
    success: bool
    result: Optional[ClassificationResult] = None
    subcategory: Optional[Subcategory] = None
    message: Optional[str] = None
