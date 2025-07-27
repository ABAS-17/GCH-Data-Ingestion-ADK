@app.post("/events/enhanced", response_model=Dict[str, Any], tags=["Events"])
async def create_enhanced_event(
    enhanced_request: EnhancedEventCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "anonymous"
):
    """Create event with comprehensive media support"""
    try:
        # FIXED: The location is already validated and converted to Coordinates by Pydantic
        # No need to check attributes or convert - just use it directly
        basic_request = EventCreateRequest(
            topic=enhanced_request.topic,
            sub_topic=enhanced_request.sub_topic,
            title=enhanced_request.title,
            description=enhanced_request.description,
            location=enhanced_request.location,  # FIXED: Use the validated Coordinates object directly
            address=enhanced_request.address,
            severity=enhanced_request.severity,
            media_urls=enhanced_request.media_urls
        )
        
        # Process media files if provided
        uploaded_urls = []
        if enhanced_request.media_files:
            for media_file in enhanced_request.media_files:
                if media_file.data:
                    url = await storage_client.upload_media(
                        media_file.data,
                        media_file.filename,
                        media_file.content_type,
                        user_id,
                        f"temp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    if url:
                        uploaded_urls.append(url)
        
        # Add uploaded URLs to media URLs
        basic_request.media_urls.extend(uploaded_urls)
        
        # Create the event
        event = await db_manager.process_user_report(basic_request, user_id)
        
        # IMMEDIATELY add to ChromaDB for search indexing
        try:
            from data.database.chroma_client import chroma_client
            indexing_success = await chroma_client.add_event(event)
            if indexing_success:
                logger.info(f"✅ Enhanced event {event.id} successfully indexed in ChromaDB")
            else:
                logger.warning(f"⚠️ Failed to index enhanced event {event.id} in ChromaDB")
        except Exception as e:
            logger.error(f"❌ Error indexing enhanced event {event.id}: {e}")
        
        # Enhanced processing with media analysis
        if uploaded_urls:
            background_tasks.add_task(analyze_event_media, event.id, uploaded_urls)
        
        return {
            "success": True,
            "event_id": event.id,
            "message": "Enhanced event created successfully",
            "media_uploaded": len(uploaded_urls),
            "event": {
                "id": event.id,
                "title": event.content.title,
                "topic": event.topic.value,
                "severity": event.impact_analysis.severity.value,
                "media_count": len(uploaded_urls),
                "created_at": event.temporal_data.created_at.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error creating enhanced event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create enhanced event: {str(e)}")
