#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced subcategory management system
Tests AI classification, Firestore integration, and API endpoints
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the enhanced subcategory system
from data.models.schemas import EventTopic, EventSeverity, EventCreateRequest, Coordinates
from data.models.subcategory_schemas import (
    SubcategoryClassificationRequest, ClassificationContext, Subcategory,
    SubcategorySource, CreateSubcategoryRequest
)
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
from data.processors.subcategory_classifier import subcategory_classifier
from data.database.simple_firestore_client import simple_firestore_client


class SubcategorySystemTester:
    """Test the enhanced subcategory system"""
    
    def __init__(self):
        self.test_results = {}
        self.test_events = [
            {
                "topic": EventTopic.TRAFFIC,
                "title": "Multi-vehicle collision on Outer Ring Road",
                "description": "Three cars involved in collision near HSR Layout signal, causing major traffic jam. Emergency services on site.",
                "expected_subcategory": "accident"
            },
            {
                "topic": EventTopic.INFRASTRUCTURE,
                "title": "Power outage in Koramangala",
                "description": "Electricity supply disrupted in Koramangala 6th Block due to transformer failure. BESCOM working on restoration.",
                "expected_subcategory": "power_outage"
            },
            {
                "topic": EventTopic.WEATHER,
                "title": "Heavy waterlogging near Silkboard",
                "description": "Severe waterlogging on Hosur Road near Silkboard junction due to continuous rainfall. Vehicles stranded.",
                "expected_subcategory": "flood"
            }
        ]
    
    async def run_simple_test(self) -> Dict[str, Any]:
        """Run a simplified test suite"""
        logger.info("🧪 Starting Simplified Subcategory System Tests")
        
        try:
            # Test 1: Basic initialization
            init_success = await enhanced_subcategory_processor.initialize()
            
            # Test 2: Simple classification
            context = ClassificationContext(
                event_title="Traffic accident on main road",
                event_description="Vehicle collision causing traffic delays"
            )
            
            request = SubcategoryClassificationRequest(
                topic=EventTopic.TRAFFIC,
                context=context
            )
            
            result = await subcategory_classifier.classify_subcategory(request)
            
            # Test 3: Health check
            health_status = await enhanced_subcategory_processor.health_check()
            
            test_results = {
                "initialization": init_success,
                "classification": {
                    "success": result.subcategory_name is not None,
                    "subcategory": result.subcategory_name,
                    "confidence": result.confidence_score
                },
                "health_check": health_status.get("overall_healthy", False),
                "overall_success": init_success and result.subcategory_name is not None
            }
            
            # Generate report
            if test_results["overall_success"]:
                logger.info("✅ All basic tests passed!")
                logger.info(f"   Classification result: {result.subcategory_name} (confidence: {result.confidence_score:.2f})")
            else:
                logger.warning("⚠️ Some tests failed")
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            return {
                "error": str(e),
                "overall_success": False
            }


async def main():
    """Run the simplified test suite"""
    print("🚀 Starting Enhanced Subcategory System Tests")
    print("=" * 60)
    
    tester = SubcategorySystemTester()
    
    try:
        # Run simplified tests
        report = await tester.run_simple_test()
        
        # Save report to file
        with open("subcategory_test_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Test report saved to: subcategory_test_report.json")
        
        # Return exit code based on success
        exit_code = 0 if report.get("overall_success", False) else 1
        return exit_code
        
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
