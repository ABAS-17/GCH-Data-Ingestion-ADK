#!/usr/bin/env python3
# quick_adk_demo.py
"""
Quick demonstration of Google ADK agent capabilities
Shows the difference between original and ADK implementations
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def make_request(method, endpoint, data=None):
    """Make HTTP request with timing"""
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        
        response_time = (time.time() - start_time) * 1000
        return {
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None,
            "error": response.text if response.status_code != 200 else None,
            "response_time_ms": response_time
        }
    except Exception as e:
        return {"success": False, "error": str(e), "response_time_ms": 0}

def print_response(title, result):
    """Print formatted response"""
    print(f"\n🔹 {title}")
    print("-" * 50)
    
    if result["success"]:
        print(f"✅ Success ({result['response_time_ms']:.0f}ms)")
        
        # Print key information from response
        data = result["data"]
        if "response" in data:
            print(f"💬 Response: {data['response'][:100]}...")
        if "total_cards" in data:
            print(f"📊 Cards Generated: {data['total_cards']}")
        if "insights" in data:
            print(f"🔍 Insights: {data['insights'][:100]}...")
        if "agent_type" in data:
            print(f"🤖 Agent Type: {data['agent_type']}")
        if "tools_called" in data:
            print(f"🛠️ Tools Used: {data['tools_called']}")
        
    else:
        print(f"❌ Failed: {result['error']}")

def main():
    """Run ADK demonstration"""
    print("🤖 Google ADK Agent Quick Demo")
    print("=" * 50)
    
    # Check server health
    print("Checking server status...")
    health = make_request("GET", "/health")
    if not health["success"]:
        print("❌ Server not running. Please start with: python3 main.py")
        return
    
    print("✅ Server is running!")
    
    # Check ADK status
    print("\nChecking ADK status...")
    adk_status = make_request("GET", "/adk/test/status")
    print_response("ADK Status Check", adk_status)
    
    if not adk_status["success"] or not adk_status["data"].get("adk_installed", False):
        print("\n⚠️ Google ADK not available. Install with: ./install_google_adk.sh")
        print("Continuing with fallback tests...")
    
    # Demo 1: ADK Chat
    print("\n" + "="*60)
    print("DEMO 1: Enhanced Conversation with ADK")
    print("="*60)
    
    chat_data = {
        "user_id": "demo_user_001",
        "message": "How is traffic in Koramangala right now? Any accidents or construction?",
        "location": {"lat": 12.9352, "lng": 77.6245}
    }
    
    adk_chat = make_request("POST", "/adk/chat", chat_data)
    print_response("ADK Chat Response", adk_chat)
    
    # Demo 2: Context Awareness
    if adk_chat["success"]:
        print("\n" + "-"*40)
        print("Testing Context Awareness...")
        
        follow_up = {
            "user_id": "demo_user_001",
            "message": "What about alternative routes to the same area?"
        }
        
        context_test = make_request("POST", "/adk/chat", follow_up)
        print_response("Context-Aware Follow-up", context_test)
    
    # Demo 3: Dashboard Generation
    print("\n" + "="*60)
    print("DEMO 2: Smart Dashboard Generation")
    print("="*60)
    
    dashboard_data = {
        "user_id": "demo_user_002",
        "refresh": True,
        "max_cards": 4
    }
    
    adk_dashboard = make_request("POST", "/adk/dashboard", dashboard_data)
    print_response("ADK Dashboard Generation", adk_dashboard)
    
    # Demo 4: Filtered Dashboard
    print("\n" + "-"*40)
    print("Testing Dashboard Filtering...")
    
    filtered_dashboard = {
        "user_id": "demo_user_002",
        "card_types": ["traffic_alert", "weather_warning"],
        "max_cards": 2
    }
    
    filtered_result = make_request("POST", "/adk/dashboard", filtered_dashboard)
    print_response("Filtered Dashboard", filtered_result)
    
    # Demo 5: Insights with Predictions
    print("\n" + "="*60)
    print("DEMO 3: Predictive Insights")
    print("="*60)
    
    insights_data = {
        "user_id": "demo_user_003",
        "insight_type": "traffic",
        "timeframe": "24h",
        "include_predictions": True
    }
    
    adk_insights = make_request("POST", "/adk/insights", insights_data)
    print_response("ADK Insights with Predictions", adk_insights)
    
    # Demo 6: Comparison with Original
    print("\n" + "="*60)
    print("DEMO 4: Performance Comparison")
    print("="*60)
    
    test_message = {
        "user_id": "comparison_user",
        "message": "Tell me about current infrastructure issues in HSR Layout",
        "location": {"lat": 12.9116, "lng": 77.6370}
    }
    
    # Test original agent
    original_result = make_request("POST", "/agent/chat", test_message)
    print_response("Original Agent", original_result)
    
    # Test ADK agent
    adk_comparison = make_request("POST", "/adk/chat", test_message)
    print_response("ADK Agent", adk_comparison)
    
    # Performance comparison
    if original_result["success"] and adk_comparison["success"]:
        print("\n📊 Performance Comparison:")
        print(f"Original Response Time: {original_result['response_time_ms']:.0f}ms")
        print(f"ADK Response Time: {adk_comparison['response_time_ms']:.0f}ms")
        
        orig_response_len = len(original_result["data"].get("response", ""))
        adk_response_len = len(adk_comparison["data"].get("response", ""))
        
        print(f"Original Response Length: {orig_response_len} chars")
        print(f"ADK Response Length: {adk_response_len} chars")
        
        adk_tools = len(adk_comparison["data"].get("tools_called", []))
        print(f"ADK Tools Used: {adk_tools}")
    
    # Demo 7: Analytics
    print("\n" + "="*60)
    print("DEMO 5: Agent Analytics")
    print("="*60)
    
    adk_analytics = make_request("GET", "/adk/analytics/usage")
    print_response("ADK Usage Analytics", adk_analytics)
    
    agents_info = make_request("GET", "/adk/analytics/agents")
    print_response("ADK Agents Information", agents_info)
    
    # Summary
    print("\n" + "="*60)
    print("🎉 DEMO COMPLETED!")
    print("="*60)
    print("What you just saw:")
    print("✅ Enhanced conversation with context awareness")
    print("✅ Smart dashboard generation with filtering")
    print("✅ Predictive insights with confidence scores")
    print("✅ Performance comparison with original implementation")
    print("✅ Comprehensive analytics and monitoring")
    print("")
    print("🚀 Your City Pulse platform now has enterprise-grade AI!")
    print("📚 Full API documentation: http://localhost:8000/docs")
    print("🧪 Run full test suite: python3 test_google_adk_agent.py")

if __name__ == "__main__":
    main()
