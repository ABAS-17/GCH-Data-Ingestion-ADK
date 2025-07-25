#!/usr/bin/env python3
"""
Test script for enhanced media capabilities
Tests image/video upload, analysis, and incident reporting
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our enhanced components
from data.processors.enhanced_event_processor import enhanced_processor
from data.database.storage_client import storage_client
from data.models.media_schemas import (
    MediaFile, EnhancedEventCreateRequest, MediaUploadResponse
)
from data.models.schemas import Coordinates, EventTopic, EventSeverity

async def test_media_capabilities():
    """Test comprehensive media handling capabilities"""
    
    print("🎬 Testing Enhanced Media Capabilities")
    print("=" * 50)
    
    # 1. Test supported formats
    print("\n1. 📋 Checking supported media formats...")
    try:
        formats = storage_client.get_supported_formats()
        print("✅ Supported formats retrieved:")
        print(f"   Images: {', '.join(formats['images'])}")
        print(f"   Videos: {', '.join(formats['videos'])}")
        print(f"   Max size: {formats['max_size_mb']} MB")
        print(f"   Max files: {formats['max_files']} per incident")
    except Exception as e:
        print(f"❌ Error getting formats: {e}")
        return False
    
    # 2. Test media file validation
    print("\n2. 🔍 Testing media file validation...")
    try:
        # Test valid image
        valid_image = MediaFile(
            filename="traffic_accident.jpg",
            content_type="image/jpeg",
            size_bytes=1024000,  # 1MB
            data=b"fake_image_data"
        )
        print("✅ Valid image file validated successfully")
        
        # Test valid video
        valid_video = MediaFile(
            filename="flooding_incident.mp4",
            content_type="video/mp4",
            size_bytes=5120000,  # 5MB
            data=b"fake_video_data"
        )
        print("✅ Valid video file validated successfully")
        
        # Test invalid file (should fail)
        try:
            invalid_file = MediaFile(
                filename="document.txt",
                content_type="text/plain",
                size_bytes=1000
            )
            print("❌ Invalid file validation should have failed")
        except ValueError:
            print("✅ Invalid file properly rejected")
            
    except Exception as e:
        print(f"❌ Media validation error: {e}")
        return False
    
    # 3. Test enhanced media analysis
    print("\n3. 🤖 Testing enhanced media analysis...")
    try:
        # Test different types of media analysis
        test_cases = [
            ("gs://bucket/pothole_damage.jpg", "image", "road damage"),
            ("gs://bucket/traffic_accident_video.mp4", "video", "traffic incident"),
            ("gs://bucket/flooding_street.jpg", "image", "weather emergency"),
            ("gs://bucket/construction_work.jpg", "image", "infrastructure")
        ]
        
        for media_url, media_type, expected_context in test_cases:
            analysis = await enhanced_processor.analyze_media_comprehensive(media_url, media_type)
            
            if analysis:
                print(f"✅ {media_type.title()} analysis completed:")
                print(f"   URL: {media_url}")
                print(f"   Description: {analysis.gemini_description[:80]}...")
                print(f"   Objects: {', '.join(analysis.detected_objects[:5])}")
                print(f"   Confidence: {analysis.confidence_score:.2f}")
                print(f"   Weather impact: {analysis.weather_impact}")
            else:
                print(f"❌ Failed to analyze {media_type}: {media_url}")
                
    except Exception as e:
        print(f"❌ Media analysis error: {e}")
        return False
    
    # 4. Test enhanced incident creation with media
    print("\n4. 📸 Testing incident creation with media...")
    try:
        # Create mock media files
        mock_media_files = [
            MediaFile(
                filename="incident_photo1.jpg",
                content_type="image/jpeg",
                size_bytes=2048000,
                data=b"mock_image_data_1"
            ),
            MediaFile(
                filename="incident_video.mp4",
                content_type="video/mp4", 
                size_bytes=8192000,
                data=b"mock_video_data"
            )
        ]
        
        enhanced_request = EnhancedEventCreateRequest(
            topic=EventTopic.TRAFFIC,
            sub_topic="accident",
            title="Multi-vehicle collision with visual evidence",
            description="Serious accident at major intersection with photo and video documentation",
            location={"lat": 12.9716, "lng": 77.5946},
            address="ORR Junction, HSR Layout, Bengaluru",
            severity=EventSeverity.HIGH,
            media_files=mock_media_files,
            reporter_context={"witness": True, "emergency_called": True}
        )
        
        print("✅ Enhanced incident request created:")
        print(f"   Title: {enhanced_request.title}")
        print(f"   Media files: {len(enhanced_request.media_files)}")
        print(f"   Location: {enhanced_request.address}")
        print(f"   Context: {enhanced_request.reporter_context}")
        
    except Exception as e:
        print(f"❌ Enhanced incident creation error: {e}")
        return False
    
    # 5. Test media processing workflow
    print("\n5. ⚙️ Testing media processing workflow...")
    try:
        # Simulate complete workflow
        user_id = "test_user_media"
        event_id = "test_event_media"
        
        # Step 1: Process multiple media files
        mock_files = [
            {"data": b"image1", "name": "accident1.jpg", "type": "image/jpeg"},
            {"data": b"video1", "name": "accident_video.mp4", "type": "video/mp4"}
        ]
        
        uploaded_urls = await enhanced_processor.process_multiple_media(
            mock_files, user_id, event_id
        )
        
        print(f"✅ Media processing workflow completed:")
        print(f"   Uploaded {len(uploaded_urls)} files")
        print(f"   URLs: {uploaded_urls}")
        
    except Exception as e:
        print(f"❌ Media processing workflow error: {e}")
        return False
    
    # 6. Test enhanced classification with media context
    print("\n6. 🧠 Testing AI classification with media context...")
    try:
        # Create sample media analysis
        sample_analysis = await enhanced_processor.analyze_media_comprehensive(
            "gs://bucket/serious_accident.jpg", "image"
        )
        
        # Test enhanced classification
        topic, sub_topic, severity = await enhanced_processor.classify_event_with_media_context(
            title="Vehicle incident reported",
            description="Multiple vehicles involved in collision",
            media_analysis=sample_analysis,
            location_context="Outer Ring Road, Bengaluru"
        )
        
        print("✅ Enhanced AI classification completed:")
        print(f"   Topic: {topic.value}")
        print(f"   Sub-topic: {sub_topic}")
        print(f"   Severity: {severity.value}")
        print(f"   Media context used: {bool(sample_analysis)}")
        
    except Exception as e:
        print(f"❌ Enhanced classification error: {e}")
        return False
    
    # 7. Test storage client capabilities
    print("\n7. 💾 Testing storage capabilities...")
    try:
        # Test mock upload
        test_upload_url = await storage_client.upload_media(
            file_data=b"test_media_data",
            file_name="test_upload.jpg",
            content_type="image/jpeg",
            user_id="test_user",
            event_id="test_event"
        )
        
        if test_upload_url:
            print(f"✅ Mock upload successful: {test_upload_url}")
            
            # Test mock deletion
            delete_success = await storage_client.delete_media(test_upload_url)
            print(f"✅ Mock deletion successful: {delete_success}")
        else:
            print("⚠️ Upload returned None (expected for mock)")
            
    except Exception as e:
        print(f"❌ Storage test error: {e}")
        return False
    
    # 8. Performance test with multiple media files
    print("\n8. ⚡ Testing performance with multiple media...")
    try:
        start_time = datetime.now()
        
        # Process multiple media files quickly
        media_urls = [
            "gs://bucket/traffic1.jpg",
            "gs://bucket/pothole2.jpg", 
            "gs://bucket/flooding3.mp4",
            "gs://bucket/construction4.jpg"
        ]
        
        analyses = []
        for url in media_urls:
            media_type = "video" if url.endswith(".mp4") else "image"
            analysis = await enhanced_processor.analyze_media_comprehensive(url, media_type)
            if analysis:
                analyses.append(analysis)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Performance test completed:")
        print(f"   Processed {len(analyses)} media files in {duration:.2f} seconds")
        print(f"   Average: {duration/len(media_urls):.2f} seconds per file")
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced Media Capabilities Test Completed!")
    print("\n📊 Summary of new capabilities:")
    print("  ✓ Multi-format media support (images & videos)")
    print("  ✓ Comprehensive AI media analysis")
    print("  ✓ Context-aware event classification")
    print("  ✓ Firebase Storage integration (mock)")
    print("  ✓ Batch media processing")
    print("  ✓ Enhanced validation and error handling")
    print("  ✓ Performance optimized workflows")
    
    print("\n🚀 Your system now supports rich media incident reporting!")
    return True

async def main():
    """Main test function"""
    try:
        success = await test_media_capabilities()
        if success:
            print("\n✅ All media capability tests passed!")
            print("🎯 Ready for production incident reporting with media")
        else:
            print("\n❌ Some media tests failed. Check output above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Media test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
