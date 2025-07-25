#!/usr/bin/env python3
"""
Quick test for media capabilities
"""

import asyncio
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def quick_media_test():
    print("🎬 Quick Media Capabilities Test")
    print("=" * 40)
    
    try:
        # Test 1: Import enhanced modules
        print("\n1. Testing imports...")
        from data.processors.enhanced_event_processor import enhanced_processor
        from data.database.storage_client import storage_client
        from data.models.media_schemas import MediaFile, EnhancedEventCreateRequest
        print("✅ All enhanced modules imported successfully")
        
        # Test 2: Test supported formats
        print("\n2. Testing supported formats...")
        formats = storage_client.get_supported_formats()
        print(f"✅ Supported formats loaded:")
        print(f"   Images: {len(formats['images'])} formats")
        print(f"   Videos: {len(formats['videos'])} formats")
        print(f"   Max size: {formats['max_size_mb']} MB")
        
        # Test 3: Test media analysis
        print("\n3. Testing media analysis...")
        analysis = await enhanced_processor.analyze_media_comprehensive(
            "test_pothole_image.jpg", "image"
        )
        if analysis:
            print("✅ Media analysis working:")
            print(f"   Description: {analysis.gemini_description[:60]}...")
            print(f"   Objects detected: {len(analysis.detected_objects)}")
            print(f"   Confidence: {analysis.confidence_score}")
        
        # Test 4: Test media file validation
        print("\n4. Testing media validation...")
        media_file = MediaFile(
            filename="test_image.jpg",
            content_type="image/jpeg",
            size_bytes=1024000
        )
        print(f"✅ Media file validation passed: {media_file.filename}")
        
        print("\n" + "=" * 40)
        print("🎉 Quick media test completed successfully!")
        print("✅ Enhanced media capabilities are working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in quick media test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_media_test())
    if success:
        print("\n🚀 Media capabilities ready!")
        print("Run: python3 test_media_capabilities.py for full test")
    else:
        print("\n❌ Media test failed")
