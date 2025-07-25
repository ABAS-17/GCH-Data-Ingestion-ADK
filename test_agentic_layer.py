            user["location"]
        )
        
        # Step 4: Ask about weather impact
        print(f"\n🌦️ Step 4: Check weather impact on commute")
        chat_result_3 = self.test_agent_chat(
            user["id"],
            "Will the weather affect my commute today?",
            user["location"]
        )
        
        # Step 5: Get personalized traffic insights
        print(f"\n📈 Step 5: Get personalized traffic insights")
        insights_result = self.test_insights_generation(user["id"], "traffic")
        
        # Step 6: Follow-up conversation
        print(f"\n💬 Step 6: Follow-up conversation")
        chat_result_4 = self.test_agent_chat(
            user["id"],
            "Thanks! Can you notify me if there are any incidents on ORR?",
            user["location"]
        )
        
        return {
            "journey": "morning_commute",
            "user": user["name"],
            "steps": {
                "dashboard": dashboard_result["success"],
                "traffic_check": chat_result_1["success"],
                "route_alternatives": chat_result_2["success"],
                "weather_check": chat_result_3["success"],
                "traffic_insights": insights_result["success"],
                "follow_up": chat_result_4["success"]
            }
        }
    
    def run_user_journey_2(self):
        """
        User Journey 2: Evening Event Discovery
        Priya Sharma wants to find events and activities for the evening
        """
        print("\n" + "="*80)
        print("🌆 USER JOURNEY 2: EVENING EVENT DISCOVERY")
        print("User: Priya Sharma (Marketing Manager)")
        print("Scenario: 6:00 PM, looking for evening activities in Koramangala area")
        print("="*80)
        
        user = TEST_USERS[1]  # Priya Sharma
        
        # Step 1: Generate evening dashboard
        print(f"\n📊 Step 1: Generate evening dashboard for {user['name']}")
        dashboard_result = self.test_dashboard_generation(user["id"])
        
        # Step 2: Ask about local events
        print(f"\n🎭 Step 2: Ask about local events")
        chat_result_1 = self.test_agent_chat(
            user["id"],
            "What's happening in Koramangala tonight? Any interesting events or activities?",
            user["location"]
        )
        
        # Step 3: Ask about restaurants and dining
        print(f"\n🍽️ Step 3: Ask about dining options")
        chat_result_2 = self.test_agent_chat(
            user["id"],
            "Any good restaurants open for dinner? Preferably places not affected by traffic or construction.",
            user["location"]
        )
        
        # Step 4: Check weather for evening plans
        print(f"\n🌙 Step 4: Check weather for evening")
        chat_result_3 = self.test_agent_chat(
            user["id"],
            "Should I carry an umbrella? How's the weather looking for tonight?",
            user["location"]
        )
        
        # Step 5: Get personalized event insights
        print(f"\n🎪 Step 5: Get personalized event insights")
        insights_result = self.test_insights_generation(user["id"], "events")
        
        # Step 6: Ask about transportation
        print(f"\n🚕 Step 6: Ask about transportation")
        chat_result_4 = self.test_agent_chat(
            user["id"],
            "What's the best way to get around tonight? Any transportation issues I should know about?",
            user["location"]
        )
        
        return {
            "journey": "evening_discovery",
            "user": user["name"],
            "steps": {
                "dashboard": dashboard_result["success"],
                "event_discovery": chat_result_1["success"],
                "dining_options": chat_result_2["success"],
                "weather_check": chat_result_3["success"],
                "event_insights": insights_result["success"],
                "transportation": chat_result_4["success"]
            }
        }
    
    def run_stress_tests(self):
        """Run stress tests and edge cases"""
        print("\n" + "="*80)
        print("🔥 STRESS TESTS & EDGE CASES")
        print("="*80)
        
        user = TEST_USERS[0]  # Use Arjun for stress tests
        
        # Test 1: Emergency scenario
        print("\n🚨 Test 1: Emergency scenario")
        emergency_result = self.test_agent_chat(
            user["id"],
            "Emergency! There's been an accident on Silk Board junction. Need immediate help!",
            user["location"]
        )
        
        # Test 2: Complex multi-part query
        print("\n🧩 Test 2: Complex multi-part query")
        complex_result = self.test_agent_chat(
            user["id"],
            "I need to get to a meeting in Whitefield by 3 PM, but I also need to pick up documents from Koramangala first. What's the best route considering current traffic, and should I take my car or use public transport? Also, are there any road closures I should know about?",
            user["location"]
        )
        
        # Test 3: Conversational context
        print("\n💬 Test 3: Conversational context (follow-up)")
        context_result_1 = self.test_agent_chat(
            user["id"],
            "How's traffic on ORR?",
            user["location"]
        )
        
        time.sleep(1)  # Brief pause
        
        context_result_2 = self.test_agent_chat(
            user["id"],
            "What about alternative routes to the same destination?",
            user["location"]
        )
        
        # Test 4: Location-specific queries
        print("\n📍 Test 4: Location-specific queries")
        location_result = self.test_agent_chat(
            user["id"],
            "Any infrastructure issues specifically in HSR Layout Sector 2?",
            {"lat": 12.9116, "lng": 77.6370}  # HSR Layout
        )
        
        # Test 5: Dashboard refresh
        print("\n🔄 Test 5: Dashboard refresh")
        refresh_result = self.make_request("GET", f"/agent/dashboard/{user['id']}?refresh=true")
        
        return {
            "stress_tests": {
                "emergency_scenario": emergency_result["success"],
                "complex_query": complex_result["success"],
                "conversational_context": context_result_1["success"] and context_result_2["success"],
                "location_specific": location_result["success"],
                "dashboard_refresh": refresh_result["success"]
            }
        }
    
    def test_system_health(self):
        """Test system health and performance"""
        print("\n" + "="*80)
        print("🏥 SYSTEM HEALTH & PERFORMANCE TESTS")
        print("="*80)
        
        # Test agentic endpoints
        print("\n🔍 Testing agentic endpoints health...")
        
        # Test agent chat endpoint
        print("   - Agent chat test endpoint...")
        chat_health = self.make_request("GET", "/agent/test/chat")
        
        # Test dashboard test endpoint  
        print("   - Dashboard test endpoint...")
        dashboard_health = self.make_request("GET", "/agent/test/dashboard")
        
        # Test analytics endpoint
        print("   - Analytics endpoint...")
        analytics_health = self.make_request("GET", "/agent/analytics/usage")
        
        # Test conversation history
        print("   - Conversation history...")
        user_id = TEST_USERS[0]["id"]
        history_health = self.make_request("GET", f"/agent/chat/{user_id}/history")
        
        health_results = {
            "chat_endpoint": chat_health["success"],
            "dashboard_endpoint": dashboard_health["success"],
            "analytics_endpoint": analytics_health["success"],
            "history_endpoint": history_health["success"]
        }
        
        print(f"✅ Health check results: {health_results}")
        return health_results
    
    def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🚀 STARTING CITY PULSE AGENTIC LAYER TEST SUITE")
        print("=" * 80)
        
        start_time = time.time()
        
        # System health check first
        health_results = self.test_system_health()
        
        # User Journey 1: Morning Commute
        journey_1_results = self.run_user_journey_1()
        
        # User Journey 2: Evening Discovery
        journey_2_results = self.run_user_journey_2()
        
        # Stress tests
        stress_test_results = self.run_stress_tests()
        
        end_time = time.time()
        
        # Summary
        print("\n" + "="*80)
        print("📊 TEST SUITE SUMMARY")
        print("="*80)
        
        print(f"⏱️  Total execution time: {end_time - start_time:.2f} seconds")
        print(f"🏥 System Health: {'✅ PASS' if all(health_results.values()) else '❌ FAIL'}")
        print(f"🌅 Journey 1 (Morning Commute): {'✅ PASS' if all(journey_1_results['steps'].values()) else '❌ FAIL'}")
        print(f"🌆 Journey 2 (Evening Discovery): {'✅ PASS' if all(journey_2_results['steps'].values()) else '❌ FAIL'}")
        print(f"🔥 Stress Tests: {'✅ PASS' if all(stress_test_results['stress_tests'].values()) else '❌ FAIL'}")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        print(f"   Health Checks: {sum(health_results.values())}/{len(health_results)} passed")
        print(f"   Journey 1 Steps: {sum(journey_1_results['steps'].values())}/{len(journey_1_results['steps'])} passed")
        print(f"   Journey 2 Steps: {sum(journey_2_results['steps'].values())}/{len(journey_2_results['steps'])} passed")
        print(f"   Stress Tests: {sum(stress_test_results['stress_tests'].values())}/{len(stress_test_results['stress_tests'])} passed")
        
        # Overall success rate
        total_tests = (len(health_results) + len(journey_1_results['steps']) + 
                      len(journey_2_results['steps']) + len(stress_test_results['stress_tests']))
        passed_tests = (sum(health_results.values()) + sum(journey_1_results['steps'].values()) + 
                       sum(journey_2_results['steps'].values()) + sum(stress_test_results['stress_tests'].values()))
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Your agentic layer is working exceptionally well!")
        elif success_rate >= 75:
            print("👍 GOOD! Your agentic layer is working well with minor issues.")
        elif success_rate >= 50:
            print("⚠️  NEEDS WORK: Several components need attention.")
        else:
            print("🚨 MAJOR ISSUES: Significant problems detected.")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "execution_time": end_time - start_time
            },
            "detailed_results": {
                "health": health_results,
                "journey_1": journey_1_results,
                "journey_2": journey_2_results,
                "stress_tests": stress_test_results
            }
        }


def main():
    """Main test execution"""
    print("🏁 Initializing City Pulse Agentic Layer Tests...")
    print("📋 Make sure your server is running at http://localhost:8000")
    print("👥 Using existing test users: Arjun Kumar and Priya Sharma")
    print("")
    
    # Initialize tester
    tester = AgenticLayerTester()
    
    # Run the full test suite
    results = tester.run_full_test_suite()
    
    # Save results to file
    with open("agentic_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Test results saved to: agentic_test_results.json")
    print("🎯 Test suite complete!")


if __name__ == "__main__":
    main()
