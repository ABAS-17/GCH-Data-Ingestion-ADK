# Enhanced Subcategory Management System

## Overview

The Enhanced Subcategory Management System provides intelligent, AI-powered subcategory classification for city events with dynamic creation, Firestore persistence, and comprehensive analytics. This system replaces the basic hardcoded subcategory approach with a scalable, learning solution.

## 🚀 Key Features

### 1. **AI-Powered Classification**
- **Gemini AI Integration**: Uses Google's Gemini 1.5 Flash for intelligent subcategory classification
- **Context-Aware**: Considers event title, description, location, and media analysis
- **Confidence Scoring**: Provides confidence levels for each classification
- **Fallback Mechanism**: Rule-based classification when AI classification fails

### 2. **Dynamic Subcategory Management**
- **Auto-Creation**: Creates new subcategories when existing ones don't fit
- **Alias Support**: Handles multiple names for the same subcategory type
- **Hierarchical Relationships**: Supports parent-child subcategory relationships
- **Status Management**: Active, deprecated, merged, and pending review statuses

### 3. **Firestore Integration**
- **Atomic Operations**: Ensures data consistency with Firestore transactions
- **Real-time Persistence**: All subcategory data stored in Firebase Cloud Firestore
- **Scalable Storage**: Handles growing subcategory datasets efficiently
- **Analytics Storage**: Persistent usage statistics and performance metrics

### 4. **Advanced Analytics**
- **Usage Tracking**: Monitors how often each subcategory is used
- **Confidence Analysis**: Tracks AI classification accuracy over time
- **User Feedback**: Records user confirmations/rejections for learning
- **Performance Reports**: Comprehensive system performance analytics

## 📁 Architecture

```
data/
├── models/
│   └── subcategory_schemas.py         # Pydantic models for subcategories
├── database/
│   └── firestore_client.py           # Firestore operations & transactions
├── processors/
│   ├── subcategory_classifier.py     # AI classification engine
│   └── enhanced_subcategory_processor.py  # Main processing logic
└── api/
    └── subcategory_endpoints.py      # REST API endpoints
```

## 🔧 Setup and Installation

### Prerequisites
- Python 3.8+
- Firebase project with Firestore enabled
- Google AI (Gemini) API key
- Service account key for Firebase

### Quick Setup
```bash
# Run the automated setup script
python setup_subcategory_system.py
```

### Manual Setup
1. **Install dependencies:**
```bash
pip install google-cloud-firestore google-cloud-storage firebase-admin google-api-core
```

2. **Configure environment variables in .env:**
```env
FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GEMINI_API_KEY=your-gemini-api-key
```

3. **Initialize the system:**
```python
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
await enhanced_subcategory_processor.initialize()
```

## 🎯 Usage Examples

### 1. Classify Event Subcategory

```python
from data.models.subcategory_schemas import SubcategoryClassificationRequest, ClassificationContext
from data.processors.subcategory_classifier import subcategory_classifier

# Build classification context
context = ClassificationContext(
    event_title="Multi-vehicle collision on Ring Road",
    event_description="Three cars involved in collision, causing traffic jam",
    location_context={
        "coordinates": {"lat": 12.9716, "lng": 77.5946},
        "address": "HSR Layout, Bengaluru"
    }
)

# Create classification request
request = SubcategoryClassificationRequest(
    topic=EventTopic.TRAFFIC,
    context=context,
    min_confidence_threshold=0.7
)

# Perform classification
result = await subcategory_classifier.classify_subcategory(request)

print(f"Classified as: {result.subcategory_name}")
print(f"Confidence: {result.confidence_score}")
print(f"New subcategory: {result.is_new_subcategory}")
```

### 2. Process Event with Enhanced Subcategories

```python
from data.processors.enhanced_subcategory_processor import enhanced_subcategory_processor
from data.models.schemas import EventCreateRequest, EventTopic, Coordinates

# Create event request
event_request = EventCreateRequest(
    topic=EventTopic.TRAFFIC,
    sub_topic="",  # Will be auto-classified
    title="Traffic accident on MG Road",
    description="Vehicle breakdown causing congestion",
    location=Coordinates(lat=12.9716, lng=77.5946),
    address="MG Road, Bengaluru",
    severity=EventSeverity.MEDIUM
)

# Process event with intelligent subcategory classification
event = await enhanced_subcategory_processor.process_user_report(event_request, "user123")

print(f"Event created with subcategory: {event.sub_topic}")
print(f"Classification confidence: {event.metadata['classification_confidence']}")
```

### 3. Get Available Subcategories

```python
# Get all subcategories for a topic
subcategories = await enhanced_subcategory_processor.get_available_subcategories(EventTopic.TRAFFIC)

for sc in subcategories:
    print(f"{sc['name']}: {sc['display_name']} (used {sc['usage_count']} times)")
```

### 4. Search Similar Subcategories

```python
from data.database.firestore_client import firestore_subcategory_client

# Search for similar subcategories
results = await firestore_subcategory_client.search_similar_subcategories(
    EventTopic.TRAFFIC, "car crash collision", max_results=5
)

for subcategory, similarity_score in results:
    print(f"{subcategory.name}: {similarity_score:.2f} similarity")
```

## 🌐 API Endpoints

### Classification
```http
POST /subcategories/classify
{
    "topic": "traffic",
    "title": "Vehicle accident on highway",
    "description": "Multiple vehicles involved in collision",
    "location_lat": 12.9716,
    "location_lng": 77.5946
}
```

### Get Subcategories
```http
GET /subcategories/?topic=traffic&status=active
```

### Analytics
```http
GET /subcategories/analytics/overview
GET /subcategories/analytics/performance
GET /subcategories/analytics/topic/traffic
```

### Health Check
```http
GET /subcategories/health
```

## 📊 Analytics and Monitoring

### Usage Statistics
- **Total Usage**: Number of times each subcategory is used
- **Confidence Tracking**: Average AI classification confidence
- **User Feedback**: Confirmation/rejection rates from users
- **Trend Analysis**: Usage patterns over time

### Performance Metrics
- **Classification Accuracy**: Percentage of correct classifications
- **Response Time**: Average time for classification
- **Success Rate**: Percentage of successful operations
- **System Health**: Component status monitoring

### Access Analytics
```python
# Get comprehensive analytics
analytics = await enhanced_subcategory_processor.get_subcategory_analytics()

# Get performance report
report = await enhanced_subcategory_processor.get_subcategory_performance_report()

print(f"Total subcategories: {analytics['total_subcategories']}")
print(f"AI success rate: {report['summary']['overall_satisfaction_rate']:.1%}")
```

## 🔍 Predefined Subcategories

The system initializes with these predefined subcategories:

### Traffic
- `accident` - Vehicle accidents and collisions
- `congestion` - Traffic jams and slow movement
- `closure` - Road closures and blockages
- `construction` - Road work and maintenance
- `breakdown` - Vehicle breakdowns
- `signal_issue` - Traffic signal problems

### Infrastructure
- `power_outage` - Electricity supply disruption
- `water_supply` - Water availability issues
- `road_damage` - Damaged roads and potholes
- `maintenance` - Scheduled infrastructure work
- `network_issue` - Internet and telecom problems
- `waste_management` - Garbage collection issues

### Weather
- `rain` - Rainfall and precipitation
- `flood` - Waterlogging and flooding
- `storm` - Severe weather conditions
- `heat` - High temperature conditions
- `wind` - Strong wind conditions
- `fog` - Low visibility due to fog

### Events
- `cultural` - Cultural festivals and celebrations
- `sports` - Sports events and competitions
- `tech` - Technology events and meetups
- `music` - Concerts and musical events
- `political` - Political rallies and meetings
- `religious` - Religious gatherings and festivals

### Safety
- `fire` - Fire emergencies and incidents
- `emergency` - General emergency situations
- `security` - Security and safety concerns
- `medical` - Medical emergencies
- `crime` - Criminal activities
- `accident` - Safety-related accidents

## 🧪 Testing

### Run Comprehensive Tests
```bash
python test_subcategory_system.py
```

### Test Categories
1. **System Initialization** - Component startup and health checks
2. **Firestore Integration** - Database operations and transactions
3. **AI Classification** - Gemini AI accuracy and performance
4. **Subcategory Management** - CRUD operations and relationships
5. **Enhanced Event Processing** - End-to-end event handling
6. **Analytics and Reporting** - Data analysis and metrics
7. **Edge Cases** - Error handling and boundary conditions

### Sample Test Results
```
🧪 ENHANCED SUBCATEGORY SYSTEM TEST REPORT
============================================================
Overall Status: ✅ PASS
Success Rate: 85.7%
Test Categories: 6/7
AI Classification: 90.0% accuracy
Event Processing: 3/3 events
============================================================
```

## 🔧 Configuration

### Environment Variables
```env
# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Google AI Configuration
GEMINI_API_KEY=your-gemini-api-key

# Firestore Collections (optional - defaults provided)
SUBCATEGORIES_COLLECTION=subcategories
SUBCATEGORY_ANALYTICS_COLLECTION=subcategory_analytics
```

### Classification Settings
```python
# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.6
LOW_CONFIDENCE_THRESHOLD = 0.4

# Minimum confidence for auto-classification
MIN_CONFIDENCE_THRESHOLD = 0.7
```

## 🚨 Error Handling

### Classification Failures
- Falls back to rule-based classification
- Uses predefined subcategories as alternatives
- Records failure reasons for analysis

### Database Errors
- Implements retry logic for transient failures
- Maintains data consistency with transactions
- Provides graceful degradation

### AI Service Outages
- Automatic fallback to rule-based classification
- Caches recent classifications for offline operation
- Health monitoring with alerts

## 📈 Performance Optimization

### Caching Strategy
- In-memory caching of frequently used subcategories
- Query result caching for similar classification requests
- Vector embedding caching for similarity searches

### Database Optimization
- Compound indexes for efficient queries
- Batch operations for multiple updates
- Connection pooling for high throughput

### AI Optimization
- Request batching for multiple classifications
- Prompt optimization for better accuracy
- Response parsing optimization

## 🔮 Future Enhancements

### Planned Features
1. **Vector Embeddings**: Semantic similarity using embeddings
2. **Learning System**: Continuous improvement from user feedback
3. **Multi-language Support**: Classification in multiple languages
4. **Geographic Context**: Location-aware subcategory suggestions
5. **Integration APIs**: Webhook support for external systems

### Roadmap
- **Q1 2024**: Vector similarity and semantic search
- **Q2 2024**: Machine learning feedback loop
- **Q3 2024**: Multi-language and regional customization
- **Q4 2024**: Advanced analytics and prediction

## 🛠️ Troubleshooting

### Common Issues

**1. Firestore Connection Failed**
```
Solution: Check FIREBASE_PROJECT_ID and service account key
Verify: gcloud auth list
Test: python -c "from google.cloud import firestore; print('OK')"
```

**2. Gemini API Errors**
```
Solution: Verify GEMINI_API_KEY is valid
Check: API quota and billing settings
Test: python -c "import google.generativeai as genai; print('OK')"
```

**3. Classification Accuracy Low**
```
Solution: Review and optimize classification prompts
Action: Analyze failed classifications in analytics
Tune: Confidence thresholds and fallback rules
```

**4. Performance Issues**
```
Monitor: Database query performance
Optimize: Add appropriate indexes
Scale: Increase Firestore capacity
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging for troubleshooting
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Run the health check: `GET /subcategories/health`
3. Review test results: `python test_subcategory_system.py`
4. Check logs for detailed error messages

## 🏗️ Contributing

To extend the system:
1. Add new subcategory models in `subcategory_schemas.py`
2. Implement additional classification logic in `subcategory_classifier.py`
3. Extend API endpoints in `subcategory_endpoints.py`
4. Add comprehensive tests in `test_subcategory_system.py`

---

**System Status**: ✅ Production Ready  
**Last Updated**: July 2025  
**Version**: 1.0.0
