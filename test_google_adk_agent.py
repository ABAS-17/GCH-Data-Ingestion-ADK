# test_google_adk_agent.py
"""
Comprehensive test script for Google ADK-based Agentic Layer
Tests both the new ADK implementation and compares with the existing one
"""

import asyncio
import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for the API
BASE_URL = "http://localhost:8000"

class ADKAgentTester:
    """Test suite for Google ADK-based agentic layer"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = {
            "adk_tests": [],
            "comparison_tests": [],
            "performance_metrics": {},
            "user_journeys": []
        }
    
    def log_test_result(self, test_name: str, success: bool, details: Dict[str, Any], test_type: str = "adk_tests"):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        self.test_results[test_type].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
        if not success:
            logger.error(f"  Error: {details.get('error', 'Unknown error')}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            start_time = time.time()
            if method.upper() == "GET":
                response = requests.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": 0
            }
    
    # =========================================================================
    # ADK AGENT STATUS AND SETUP TESTS
    # =========================================================================
    
    def test_adk_installation_status(self):
        """Test if Google ADK is properly installed and configured"""
        result = self.make_request("GET", "/adk/test/status")
        
        if result["success"]:
            data = result["data"]
            adk_available = data.get("adk_installed", False)
            agents_count = len(data.get("agents_available", []))
            
            self.log_test_result(
                "ADK Installation Status",
                adk_available,
                {
                    "adk_installed": adk_available,
                    "agents_available": agents_count,
                    "status": data.get("status"),
                    "response_time_ms": result["response_time_ms"]
                }
            )
            
            return adk_available
        else:
            self.log_test_result(
                "ADK Installation Status",
                False,
                {"error": result["error"]}
            )
            return False
    
    def test_adk_agents_info(self):
        """Test ADK agents information endpoint"""
        result = self.make_request("GET", "/adk/analytics/agents")
        
        if result["success"]:
            data = result["data"]
            agents_count = data.get("agents_count", 0)
            
            self.log_test_result(
                "ADK Agents Information",
                agents_count > 0,
                {
                    "agents_count": agents_count,
                    "agents": data.get("agents", {}),
                    "response_time_ms": result["response_time_ms"]
                }
            )
        else:
            self.log_test_result(
                "ADK Agents Information",
                False,
                {"error": result["error"]}
            )
    
    # =========================================================================
    # ADK CONVERSATION TESTS
    # =========================================================================
    
    def test_adk_chat_basic(self):
        """Test basic ADK chat functionality"""
        chat_data = {
            "user_id": "adk_test_user_001",
            "message": "Hello! How is traffic in Bengaluru today?",
            "location": {
                "lat": 12.9716,
                "lng": 77.5946
            }
        }
        
        result = self.make_request("POST", "/adk/chat", chat_data)
        
        if result["success"]:
            data = result["data"]
            response_length = len(data.get("response", ""))
            
            self.log_test_result(
                "ADK Basic Chat",
                response_length > 10,  # Should have meaningful response
                {
                    "response_length": response_length,
                    "suggested_actions": len(data.get("suggested_actions", [])),
                    "knowledge_used": data.get("knowledge_used", 0),
                    "tools_called": data.get("tools_called", []),
                    "confidence_score": data.get("confidence_score", 0),
                    "response_time_ms": result["response_time_ms"]
                }
            )
        else:
            self.log_test_result(
                "ADK Basic Chat",
                False,
                {"error": result["error"]}
            )
    
    def test_adk_chat_context_aware(self):
        """Test ADK context awareness in conversation"""
        user_id = "adk_test_user_002"
        
        # First message
        first_message = {
            "user_id": user_id,
            "message": "I'm looking for traffic information for Electronic City",
            "location": {"lat": 12.8456, "lng": 77.6603}
        }
        
        result1 = self.make_request("POST", "/adk/chat", first_message)
        
        # Follow-up message (should understand context)
        follow_up = {
            "user_id": user_id,
            "message": "What about alternative routes?"
        }
        
        result2 = self.make_request("POST", "/adk/chat", follow_up)
        
        success = (result1["success"] and result2["success"] and 
                  len(result2["data"].get("response", "")) > 10)
        
        self.log_test_result(
            "ADK Context Awareness",
            success,
            {
                "first_response_length": len(result1["data"].get("response", "")) if result1["success"] else 0,
                "follow_up_response_length": len(result2["data"].get("response", "")) if result2["success"] else 0,
                "context_maintained": success
            }
        )
    
    def test_adk_conversation_history(self):
        """Test conversation history functionality"""
        user_id = "adk_test_user_003"
        
        # Send a message first
        chat_data = {
            "user_id": user_id,
            "message": "Tell me about weather in HSR Layout"
        }
        
        chat_result = self.make_request("POST", "/adk/chat", chat_data)
        
        # Get conversation history
        history_result = self.make_request("GET", f"/adk/chat/{user_id}/history")
        
        if history_result["success"]:
            data = history_result["data"]
            messages_count = len(data.get("conversation_history", []))
            
            self.log_test_result(
                "ADK Conversation History",
                messages_count >= 2,  # Should have user message and assistant response
                {
                    "messages_count": messages_count,
                    "total_messages": data.get("total_messages", 0),
                    "agent_type": data.get("agent_type")
                }
            )
        else:
            self.log_test_result(
                "ADK Conversation History",
                False,
                {"error": history_result["error"]}
            )
    
    # =========================================================================
    # ADK DASHBOARD TESTS
    # =========================================================================
    
    def test_adk_dashboard_generation(self):
        """Test ADK dashboard content generation"""
        dashboard_data = {
            "user_id": "adk_test_user_004",
            "refresh": True,
            "max_cards": 4
        }
        
        result = self.make_request("POST", "/adk/dashboard", dashboard_data)
        
        if result["success"]:
            data = result["data"]
            cards_count = data.get("total_cards", 0)
            personalization_score = data.get("personalization_score", 0)
            
            self.log_test_result(
                "ADK Dashboard Generation",
                cards_count > 0,
                {
                    "cards_generated": cards_count,
                    "personalization_score": personalization_score,
                    "agent_type": data.get("agent_type"),
                    "response_time_ms": result["response_time_ms"]
                }
            )
        else:
            self.log_test_result(
                "ADK Dashboard Generation",
                False,
                {"error": result["error"]}
            )
    
    def test_adk_dashboard_filtering(self):
        """Test dashboard card type filtering"""
        dashboard_data = {
            "user_id": "adk_test_user_005",
            "card_types": ["traffic_alert", "weather_warning"],
            "max_cards": 2
        }
        
        result = self.make_request("POST", "/adk/dashboard", dashboard_data)
        
        if result["success"]:
            data = result["data"]
            cards = data.get("cards", [])
            valid_types = all(card.get("type") in ["traffic_alert", "weather_warning"] for card in cards)
            
            self.log_test_result(
                "ADK Dashboard Filtering",
                valid_types and len(cards) <= 2,
                {
                    "cards_count": len(cards),
                    "types_match_filter": valid_types,
                    "card_types": [card.get("type") for card in cards]
                }
            )
        else:
            self.log_test_result(
                "ADK Dashboard Filtering",
                False,
                {"error": result["error"]}
            )
    
    # =========================================================================
    # ADK INSIGHTS TESTS
    # =========================================================================
    
    def test_adk_insights_generation(self):
        """Test ADK insights generation"""
        insights_data = {
            "user_id": "adk_test_user_006",
            "insight_type": "traffic",
            "timeframe": "24h",
            "include_predictions": True
        }
        
        result = self.make_request("POST", "/adk/insights", insights_data)
        
        if result["success"]:
            data = result["data"]
            insights_length = len(data.get("insights", ""))
            predictions_count = len(data.get("predictions", []))
            
            self.log_test_result(
                "ADK Insights Generation",
                insights_length > 20,  # Should have meaningful insights
                {
                    "insights_length": insights_length,
                    "predictions_count": predictions_count,
                    "confidence_score": data.get("confidence_score", 0),
                    "data_points_used": data.get("data_points_used", 0),
                    "response_time_ms": result["response_time_ms"]
                }
            )
        else:
            self.log_test_result(
                "ADK Insights Generation",
                False,
                {"error": result["error"]}
            )
    
    # =========================================================================
    # COMPARISON TESTS (ADK vs Original)
    # =========================================================================
    
    def test_compare_chat_performance(self):
        """Compare ADK vs original agent chat performance"""
        test_message = {
            "user_id": "comparison_test_user",
            "message": "How is the weather affecting traffic in Koramangala?",
            "location": {"lat": 12.9352, "lng": 77.6245}
        }
        
        # Test original agent
        original_result = self.make_request("POST", "/agent/chat", test_message)
        
        # Test ADK agent  
        adk_result = self.make_request("POST", "/adk/chat", test_message)
        
        comparison = {
            "original_success": original_result["success"],
            "adk_success": adk_result["success"],
            "original_response_time": original_result.get("response_time_ms", 0),
            "adk_response_time": adk_result.get("response_time_ms", 0),
            "original_response_length": len(original_result["data"].get("response", "")) if original_result["success"] else 0,
            "adk_response_length": len(adk_result["data"].get("response", "")) if adk_result["success"] else 0
        }
        
        # Both should work, but we're mainly testing ADK works
        success = adk_result["success"]
        
        self.log_test_result(
            "Chat Performance Comparison",
            success,
            comparison,
            "comparison_tests"
        )
    
    def test_compare_dashboard_performance(self):
        """Compare ADK vs original dashboard generation"""
        test_data = {"user_id": "comparison_dashboard_user", "refresh": True}
        
        # Test original dashboard
        original_result = self.make_request("POST", "/agent/dashboard", test_data)
        
        # Test ADK dashboard
        adk_result = self.make_request("POST", "/adk/dashboard", test_data)
        
        comparison = {
            "original_success": original_result["success"],
            "adk_success": adk_result["success"],
            "original_cards": original_result["data"].get("total_cards", 0) if original_result["success"] else 0,
            "adk_cards": adk_result["data"].get("total_cards", 0) if adk_result["success"] else 0,
            "original_response_time": original_result.get("response_time_ms", 0),
            "adk_response_time": adk_result.get("response_time_ms", 0)
        }
        
        success = adk_result["success"]
        
        self.log_test_result(
            "Dashboard Performance Comparison", 
            success,
            comparison,
            "comparison_tests"
        )
    
    # =========================================================================
    # USER JOURNEY TESTS
    # =========================================================================
    
    def test_user_journey_morning_commute(self):
        """Test complete morning commute user journey with ADK"""
        user_id = "journey_user_morning"
        journey_steps = []
        
        # Step 1: Ask about traffic
        step1 = {
            "user_id": user_id,
            "message": "How is traffic to Electronic City this morning?",
            "location": {"lat": 12.9716, "lng": 77.5946}
        }
        
        result1 = self.make_request("POST", "/adk/chat", step1)
        journey_steps.append({"step": "traffic_inquiry", "success": result1["success"]})
        
        # Step 2: Ask for alternatives
        step2 = {
            "user_id": user_id,
            "message": "What are some alternative routes?"
        }
        
        result2 = self.make_request("POST", "/adk/chat", step2)
        journey_steps.append({"step": "alternatives", "success": result2["success"]})
        
        # Step 3: Generate dashboard
        dashboard_data = {"user_id": user_id, "refresh": True}
        result3 = self.make_request("POST", "/adk/dashboard", dashboard_data)
        journey_steps.append({"step": "dashboard", "success": result3["success"]})
        
        # Step 4: Get insights
        insights_data = {"user_id": user_id, "insight_type": "traffic"}
        result4 = self.make_request("POST", "/adk/insights", insights_data)
        journey_steps.append({"step": "insights", "success": result4["success"]})
        
        all_successful = all(step["success"] for step in journey_steps)
        
        self.log_test_result(
            "Morning Commute Journey",
            all_successful,
            {
                "steps_completed": len([s for s in journey_steps if s["success"]]),
                "total_steps": len(journey_steps),
                "journey_details": journey_steps
            },
            "user_journeys"
        )
    
    def test_user_journey_evening_discovery(self):
        """Test evening event discovery user journey with ADK"""
        user_id = "journey_user_evening"
        journey_steps = []
        
        # Step 1: Ask about evening events
        step1 = {
            "user_id": user_id,
            "message": "What events are happening in Koramangala tonight?",
            "location": {"lat": 12.9352, "lng": 77.6245}
        }
        
        result1 = self.make_request("POST", "/adk/chat", step1)
        journey_steps.append({"step": "event_inquiry", "success": result1["success"]})
        
        # Step 2: Ask about weather
        step2 = {
            "user_id": user_id,
            "message": "Should I carry an umbrella tonight?"
        }
        
        result2 = self.make_request("POST", "/adk/chat", step2)
        journey_steps.append({"step": "weather_check", "success": result2["success"]})
        
        # Step 3: Generate personalized dashboard
        dashboard_data = {
            "user_id": user_id,
            "card_types": ["event_recommendation", "weather_warning"],
            "max_cards": 3
        }
        result3 = self.make_request("POST", "/adk/dashboard", dashboard_data)
        journey_steps.append({"step": "evening_dashboard", "success": result3["success"]})
        
        all_successful = all(step["success"] for step in journey_steps)
        
        self.log_test_result(
            "Evening Discovery Journey",
            all_successful,
            {
                "steps_completed": len([s for s in journey_steps if s["success"]]),
                "total_steps": len(journey_steps),
                "journey_details": journey_steps
            },
            "user_journeys"
        )
    
    # =========================================================================
    # PERFORMANCE AND STRESS TESTS
    # =========================================================================
    
    def test_adk_response_times(self):
        """Test ADK agent response times under normal load"""
        response_times = []
        
        for i in range(5):
            chat_data = {
                "user_id": f"perf_test_user_{i}",
                "message": f"Test message {i}: How is traffic in area {i}?",
                "location": {"lat": 12.9716 + (i * 0.01), "lng": 77.5946 + (i * 0.01)}
            }
            
            result = self.make_request("POST", "/adk/chat", chat_data)
            if result["success"]:
                response_times.append(result["response_time_ms"])
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Consider successful if average response time is under 5 seconds
        success = avg_response_time < 5000 and len(response_times) >= 4
        
        self.performance_metrics["adk_response_times"] = {
            "average_ms": avg_response_time,
            "max_ms": max_response_time,
            "successful_requests": len(response_times),
            "total_requests": 5
        }
        
        self.log_test_result(
            "ADK Response Time Performance",
            success,
            self.performance_metrics["adk_response_times"]
        )
    
    # =========================================================================
    # MAIN TEST RUNNER
    # =========================================================================
    
    def run_all_tests(self):
        """Run all ADK agent tests"""
        logger.info("🚀 Starting Google ADK Agent Test Suite")
        logger.info("=" * 60)
        
        # Check if server is running
        health_check = self.make_request("GET", "/health")
        if not health_check["success"]:
            logger.error("❌ Server is not running. Please start the server first.")
            return False
        
        logger.info("✅ Server is running. Starting tests...")
        logger.info("")
        
        # 1. ADK Installation and Setup Tests
        logger.info("📋 1. ADK Installation and Setup Tests")
        logger.info("-" * 40)
        adk_available = self.test_adk_installation_status()
        if adk_available:
            self.test_adk_agents_info()
        else:
            logger.warning("⚠️  Google ADK not available. Some tests will be skipped.")
        logger.info("")
        
        # 2. ADK Conversation Tests
        logger.info("💬 2. ADK Conversation Tests")
        logger.info("-" * 40)
        self.test_adk_chat_basic()
        self.test_adk_chat_context_aware()
        self.test_adk_conversation_history()
        logger.info("")
        
        # 3. ADK Dashboard Tests
        logger.info("📊 3. ADK Dashboard Tests")
        logger.info("-" * 40)
        self.test_adk_dashboard_generation()
        self.test_adk_dashboard_filtering()
        logger.info("")
        
        # 4. ADK Insights Tests
        logger.info("🔍 4. ADK Insights Tests")
        logger.info("-" * 40)
        self.test_adk_insights_generation()
        logger.info("")
        
        # 5. Comparison Tests
        logger.info("⚖️  5. Comparison Tests (ADK vs Original)")
        logger.info("-" * 40)
        self.test_compare_chat_performance()
        self.test_compare_dashboard_performance()
        logger.info("")
        
        # 6. User Journey Tests
        logger.info("👤 6. User Journey Tests")
        logger.info("-" * 40)
        self.test_user_journey_morning_commute()
        self.test_user_journey_evening_discovery()
        logger.info("")
        
        # 7. Performance Tests
        logger.info("⚡ 7. Performance Tests")
        logger.info("-" * 40)
        self.test_adk_response_times()
        logger.info("")
        
        # Generate summary
        self.generate_test_summary()
        return True
    
    def generate_test_summary(self):
        """Generate comprehensive test summary"""
        logger.info("📈 TEST SUMMARY")
        logger.info("=" * 60)
        
        # Count results by category
        categories = ["adk_tests", "comparison_tests", "user_journeys"]
        
        for category in categories:
            tests = self.test_results[category]
            total = len(tests)
            passed = len([t for t in tests if t["success"]])
            failed = total - passed
            
            category_name = category.replace("_", " ").title()
            logger.info(f"{category_name}: {passed}/{total} passed")
            
            if failed > 0:
                logger.info(f"  Failed tests:")
                for test in tests:
                    if not test["success"]:
                        logger.info(f"    - {test['test_name']}")
        
        # Overall summary
        all_tests = []
        for category in categories:
            all_tests.extend(self.test_results[category])
        
        total_tests = len(all_tests)
        total_passed = len([t for t in all_tests if t["success"]])
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("")
        logger.info(f"🎯 OVERALL RESULTS")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {total_passed}")
        logger.info(f"Failed: {total_tests - total_passed}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        # Performance metrics
        if self.performance_metrics:
            logger.info("")
            logger.info("⚡ PERFORMANCE METRICS")
            for metric_name, metrics in self.performance_metrics.items():
                logger.info(f"{metric_name}:")
                for key, value in metrics.items():
                    logger.info(f"  {key}: {value}")
        
        # Save detailed results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = f"adk_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info("")
        logger.info(f"📄 Detailed results saved to: {results_file}")
        logger.info("🏁 Testing completed!")


def main():
    """Main function to run the test suite"""
    print("🤖 Google ADK Agent Test Suite")
    print("=" * 50)
    print("This test suite will:")
    print("1. Check Google ADK installation status")
    print("2. Test ADK agent functionality")
    print("3. Compare with existing implementation")
    print("4. Run user journey scenarios")
    print("5. Measure performance metrics")
    print("")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running or not healthy")
            print("Please start the server with: python3 main.py")
            return
    except Exception:
        print("❌ Cannot connect to server")
        print("Please start the server with: python3 main.py")
        return
    
    # Run tests
    tester = ADKAgentTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
