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