# Fixed MediaUploadResponse schema
class MediaUploadResponse(BaseModel):
    """Response model for media upload"""
    success: bool
    uploaded_files: List[Dict[str, Union[str, int]]] = Field(default_factory=list)  # Allow both str and int
    failed_files: List[Dict[str, str]] = Field(default_factory=list)
    total_uploaded: int = 0
    storage_urls: List[str] = Field(default_factory=list)
