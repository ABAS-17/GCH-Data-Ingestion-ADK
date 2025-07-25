#!/usr/bin/env python3
"""
FastAPI Test Script for City Pulse Agent
Tests all API endpoints to ensure they work correctly
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
import sys
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

class APITester:
    """Test all FastAPI endpoints"""
    
    def __init__(self):
        self.session = None
        self.test_results = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, method: str, endpoint: str, data=None, files=None):
        """Test a single endpoint"""
        try:
            url = f"{BASE_URL}{endpoint}"
            
            if method.upper() == "GET":
                async with self.session.get(url, params=data) as response:
                    result = await response.json()
                    return response.status, result
            
            elif method.upper() == "POST":
                if files:
                    # For file uploads
                    form_data = aiohttp.FormData()
                    if data:
                        for key, value in data.items():
                            form_data.add_field(key, str(value))
                    # Note: File upload testing would need actual files
                    
                    async with self.session.post(url, data=form_data) as response:
                        result = await response.json()
                        return response.status, result
                else:
                    async with self.session.post(url, json=data) as response:
                        result = await response.json()
                        return response.status, result
            
        except Exception as e:
            logger.error(f"Error testing {method} {endpoint}: {e}")
            return 500, {"error": str(e)}
    
    async def run_all_tests(self):
        """Run comprehensive API tests"""
        print("🧪 Testing City Pulse Agent FastAPI")
        print("=" * 50)
        
        # Test 1: Health Check
        print("\n1. 🏥 Testing Health Check...")
        status, result = await self.test_endpoint("GET", "/health")
        if status == 200:
            print(f"✅ Health check passed: {result.get('status')}")
            self.test_results["health"] = True
        else:
            print(f"❌ Health check failed: {status}")
            self.test_results["health"] = False
        
        # Test 2: Root endpoint
        print("\n2. 🏠 Testing Root Endpoint...")
        status, result = await self.test_endpoint("GET", "/")
        if status == 200:
            print(f"✅ Root endpoint: {result.get('message')}")
            self.test_results["root"] = True
        else:
            print(f"❌ Root endpoint failed: {status}")
            self.test_results["root"] = False
        
        # Test 3: Create Basic Event
        print("\n3. 📝 Testing Basic Event Creation...")
        event_data = {
            "topic": "traffic",
            "sub_topic": "accident",
            "title": "Test traffic accident",
            "description": "Multi-vehicle collision on test road",
            "location": {"lat": 12.9716, "lng": 77.5946},
            "address": "Test Location, Bengaluru",
            "severity": "high",
            "media_urls": []
        }
        
        status, result = await self.test_endpoint("POST", "/events", event_data)
        if status == 200 and result.get("success"):
            print(f"✅ Event created: {result.get('event_id')}")
            self.test_results["create_event"] = True
            self.test_event_id = result.get('event_id')
        else:
            print(f"❌ Event creation failed: {status}")
            self.test_results["create_event"] = False
        
        # Test 4: Enhanced Event Creation
        print("\n4. 🎬 Testing Enhanced Event Creation...")
        enhanced_data = {
            "topic": "infrastructure",
            "sub_topic": "power_outage",
            "title": "Power outage in HSR Layout",
            "description": "Electricity supply disrupted affecting multiple buildings",
            "location": {"lat": 12.9116, "lng": 77.6370},
            "address": "HSR Layout, Bengaluru",
            "severity": "medium",
            "media_files": [],
            "media_urls": [],
            "reporter_context": {"witness": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        status, result = await self.test_endpoint("POST", "/events/enhanced", enhanced_data)
        if status == 200 and result.get("success"):
            print(f"✅ Enhanced event created: {result.get('event_id')}")
            self.test_results["create_enhanced_event"] = True
        else:
            print(f"❌ Enhanced event creation failed: {status}")
            self.test_results["create_enhanced_event"] = False
        
        # Test 5: Event Search
        print("\n5. 🔍 Testing Event Search...")
        search_params = {
            "query": "traffic accident",
            "lat": 12.9716,
            "lng": 77.5946,
            "radius_km": 10,
            "max_results": 5
        }
        
        status, result = await self.test_endpoint("GET", "/events/search", search_params)
        if status == 200 and result.get("success"):
            print(f"✅ Search completed: {result.get('total_results')} results")
            self.test_results["search_events"] = True
        else:
            print(f"❌ Event search failed: {status}")
            self.test_results["search_events"] = False
        
        # Test 6: Nearby Events
        print("\n6. 📍 Testing Nearby Events...")
        nearby_params = {
            "lat": 12.9716,
            "lng": 77.5946,
            "radius_km": 5,
            "max_results": 10
        }
        
        status, result = await self.test_endpoint("GET", "/events/nearby", nearby_params)
        if status == 200 and result.get("success"):
            print(f"✅ Nearby events: {result.get('total_events')} found")
            self.test_results["nearby_events"] = True
        else:
            print(f"❌ Nearby events failed: {status}")
            self.test_results["nearby_events"] = False
        
        # Test 7: Media Formats
        print("\n7. 📁 Testing Media Formats...")
        status, result = await self.test_endpoint("GET", "/media/formats")
        if status == 200 and result.get("success"):
            formats = result.get("formats", {})
            print(f"✅ Media formats: {len(formats.get('images', []))} image, {len(formats.get('videos', []))} video")
            self.test_results["media_formats"] = True
        else:
            print(f"❌ Media formats failed: {status}")
            self.test_results["media_formats"] = False
        
        # Test 8: Media Analysis
        print("\n8. 🤖 Testing Media Analysis...")
        analysis_data = {
            "media_url": "gs://bucket/test_image.jpg",
            "media_type": "image"
        }
        
        status, result = await self.test_endpoint("POST", "/media/analyze", analysis_data)
        if status == 200:
            print(f"✅ Media analysis: confidence {result.get('confidence_score', 0):.2f}")
            self.test_results["media_analysis"] = True
        else:
            print(f"❌ Media analysis failed: {status}")
            self.test_results["media_analysis"] = False
        
        # Test 9: Basic Chat
        print("\n9. 💬 Testing Basic Chat...")
        chat_data = {
            "user_id": "test_user",
            "message": "What's the traffic like on ORR?",
            "location": {"lat": 12.9716, "lng": 77.5946},
            "context": {}
        }
        
        status, result = await self.test_endpoint("POST", "/chat", chat_data)
        if status == 200:
            print(f"✅ Chat response: {len(result.get('suggestions', []))} suggestions")
            self.test_results["chat"] = True
        else:
            print(f"❌ Chat failed: {status}")
            self.test_results["chat"] = False
        
        # Test 10: Enhanced Chat
        print("\n10. 🎥 Testing Enhanced Chat...")
        enhanced_chat_data = {
            "user_id": "test_user",
            "message": "Can you analyze this traffic scene?",
            "location": {"lat": 12.9716, "lng": 77.5946},
            "context": {},
            "media_references": ["gs://bucket/traffic_scene.jpg"],
            "include_media_analysis": True
        }
        
        status, result = await self.test_endpoint("POST", "/chat/enhanced", enhanced_chat_data)
        if status == 200:
            print(f"✅ Enhanced chat: {bool(result.get('media_insights'))} media insights")
            self.test_results["enhanced_chat"] = True
        else:
            print(f"❌ Enhanced chat failed: {status}")
            self.test_results["enhanced_chat"] = False
        
        # Test 11: Analytics Overview
        print("\n11. 📊 Testing Analytics...")
        analytics_params = {"timeframe": "24h"}
        
        status, result = await self.test_endpoint("GET", "/analytics/overview", analytics_params)
        if status == 200 and result.get("success"):
            analytics = result.get("analytics", {})
            print(f"✅ Analytics: {analytics.get('total_events', 0)} total events")
            self.test_results["analytics"] = True
        else:
            print(f"❌ Analytics failed: {status}")
            self.test_results["analytics"] = False
        
        # Test 12: Heatmap Data
        print("\n12. 🗺️ Testing Heatmap...")
        heatmap_params = {"timeframe": "24h"}
        
        status, result = await self.test_endpoint("GET", "/analytics/heatmap", heatmap_params)
        if status == 200 and result.get("success"):
            points = result.get("total_points", 0)
            print(f"✅ Heatmap: {points} data points")
            self.test_results["heatmap"] = True
        else:
            print(f"❌ Heatmap failed: {status}")
            self.test_results["heatmap"] = False
        
        # Test 13: Demo Data Population
        print("\n13. 🎭 Testing Demo Data Population...")
        demo_data = {"events_count": 10, "users_count": 3}
        
        status, result = await self.test_endpoint("POST", "/demo/populate", demo_data)
        if status == 200 and result.get("success"):
            print(f"✅ Demo data: {demo_data['events_count']} events, {demo_data['users_count']} users")
            self.test_results["demo_data"] = True
        else:
            print(f"❌ Demo data failed: {status}")
            self.test_results["demo_data"] = False
        
        # Test 14: Test Scenarios
        print("\n14. 🎯 Testing Demo Scenarios...")
        status, result = await self.test_endpoint("GET", "/demo/test-scenarios")
        if status == 200 and result.get("success"):
            scenarios = len(result.get("scenarios", []))
            print(f"✅ Test scenarios: {scenarios} available")
            self.test_results["test_scenarios"] = True
        else:
            print(f"❌ Test scenarios failed: {status}")
            self.test_results["test_scenarios"] = False
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🏆 API Test Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"\n📊 Results: {passed}/{total} tests passed")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        print("\n✅ Passed Tests:")
        for test, result in self.test_results.items():
            if result:
                print(f"  • {test}")
        
        if passed < total:
            print("\n❌ Failed Tests:")
            for test, result in self.test_results.items():
                if not result:
                    print(f"  • {test}")
        
        if passed == total:
            print("\n🎉 All API endpoints working perfectly!")
            print("🚀 Ready for agentic layer development!")
        else:
            print(f"\n⚠️ {total - passed} tests failed. Check server logs.")

async def main():
    """Run API tests"""
    print("🚀 Starting FastAPI Test Suite")
    print("Make sure the server is running on http://localhost:8000")
    print("Start server with: python3 main.py")
    print()
    
    try:
        async with APITester() as tester:
            await tester.run_all_tests()
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
