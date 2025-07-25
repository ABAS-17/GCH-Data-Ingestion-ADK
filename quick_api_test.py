#!/usr/bin/env python3
"""
Quick test with corrected event creation
"""
import requests
import json

# Test the corrected event creation
url = "http://localhost:8000/events"
data = {
    "topic": "traffic",
    "sub_topic": "congestion",  # Add required field
    "title": "Test incident",
    "description": "Testing the API",
    "location": {"lat": 12.9716, "lng": 77.5946},
    "severity": "medium"
}

print("🧪 Testing corrected event creation...")
response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test enhanced event creation
url_enhanced = "http://localhost:8000/events/enhanced"
enhanced_data = {
    "topic": "infrastructure",
    "sub_topic": "power_outage",
    "title": "Power outage test",
    "description": "Testing enhanced event creation",
    "location": {"lat": 12.9116, "lng": 77.6370},
    "severity": "medium",
    "media_files": [],
    "media_urls": []
}

print("\n🎬 Testing enhanced event creation...")
response = requests.post(url_enhanced, json=enhanced_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
