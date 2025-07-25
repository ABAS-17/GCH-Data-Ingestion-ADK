# City Pulse Agent - Data Layer

## 🎯 Complete Data Foundation for AI Agent

This is the complete data layer for the City Pulse Agent - an intelligent system that provides real-time city insights using AI and vector search.

## 🏗️ Architecture

```
City Pulse Data Layer
├── 📊 Data Models (Pydantic Schemas)
├── 🤖 AI Processing (Gemini Integration)  
├── 🔍 Vector Search (ChromaDB)
├── 📍 Geographic Data (Google Maps Ready)
├── 📅 Calendar Integration (Google Calendar)
└── 🧪 Mock Data Generation (Bengaluru Focus)
```

## ✅ What's Implemented

### **1. Complete Data Schemas** (`data/models/schemas.py`)
- **Events**: Traffic, infrastructure, weather, cultural events, safety
- **Users**: Profiles, permissions, Google integrations, locations
- **Conversations**: Chat history, user context, preferences  
- **Geographic Data**: Coordinates, places, administrative areas
- **API Models**: Request/response schemas for FastAPI

### **2. AI-Powered Event Processing** (`data/processors/event_processor.py`)
- **Gemini Integration**: Event classification and analysis
- **Media Analysis**: Image/video processing capabilities
- **Location Enrichment**: Geographic data enhancement
- **Smart Classification**: Topic, severity, and impact analysis

### **3. Vector Search Engine** (`data/database/chroma_client.py`)
- **ChromaDB Integration**: Local vector storage
- **Semantic Search**: Find similar events using AI embeddings
- **Location Filtering**: Geographic-aware search
- **Performance Optimized**: Fast similarity queries

### **4. Mock Data Generator** (`data/mock_data/data_generator.py`)
- **Bengaluru-Specific**: Real locations and scenarios
- **Realistic Events**: Traffic, weather, infrastructure, cultural
- **User Profiles**: Indian names, local preferences
- **Conversation History**: Typical user interactions

### **5. Database Manager** (`data/database/database_manager.py`)
- **Unified Interface**: Single entry point for all data operations
- **Event Creation**: From user reports to processed events
- **Search Operations**: Semantic and location-based queries
- **Health Monitoring**: System status and statistics

## 🚀 Quick Start

### **1. Install Dependencies**
```bash
cd /Users/ab/city_pulse_test
pip install python-dotenv google-generativeai chromadb pydantic
```

### **2. Test the Complete System**
```bash
python3 test_complete_data_layer.py
```

### **3. Expected Output**
```
🚀 Testing Complete City Pulse Data Layer
✅ Databases initialized successfully  
✅ User schema created
✅ Event processed successfully
✅ Mock data generated successfully
✅ Semantic search completed
🎉 Complete Data Layer Test Finished!
```

## 📋 Test Results Summary

When you run the test, you should see:
- ✅ **Database Health**: ChromaDB initialized and working
- ✅ **AI Processing**: Gemini API classifying events correctly  
- ✅ **Vector Search**: Semantic similarity working
- ✅ **Mock Data**: 10+ realistic Bengaluru events generated
- ✅ **Performance**: Fast event processing and search

## 🔑 API Keys Used

- **Gemini API**: `AIzaSyBCAAnb93XEN8jdnLYBUyUvU_ub6BX4U3E` ✅
- **Firebase Project**: `hack-4ad75` ✅
- **ChromaDB**: Local storage (no API key needed) ✅

## 📊 Data Examples

### **Sample Event Generated:**
```json
{
  "id": "event_abc123",
  "topic": "traffic", 
  "title": "Heavy traffic on Old Airport Road",
  "description": "Multiple vehicle breakdown causing 45 min delays",
  "location": {"lat": 12.9716, "lng": 77.5946},
  "severity": "high",
  "impact_analysis": {
    "affected_users_estimated": 500,
    "confidence_score": 0.85
  }
}
```

### **Sample Search Query:**
```python
results = await db_manager.search_events_semantically(
    query="traffic accident causing delays",
    user_location=Coordinates(lat=12.9716, lng=77.5946),
    max_results=5
)
# Returns: List of relevant events with similarity scores
```

## 🎯 Next Steps - FastAPI Backend

Now that the data layer is complete, you can build:

1. **REST API Endpoints**:
   - `POST /events` - Create new events
   - `GET /events/search` - Semantic event search
   - `POST /chat` - Agent conversation
   - `GET /dashboard/{user_id}` - Personalized recommendations

2. **Google ADK Agent Integration**:
   - Agent tools that use `db_manager`
   - Context-aware responses
   - Real-time event queries

3. **WebSocket Real-time Updates**:
   - Live event notifications
   - Real-time chat
   - Location-based alerts

## 🔧 Configuration

All settings in `config.py`:
- **Gemini API**: Event classification and embedding
- **ChromaDB**: Vector storage path and collections
- **Location Settings**: Bengaluru-focused defaults
- **Performance**: Timeouts, limits, and caching

## 📁 File Structure

```
/Users/ab/city_pulse_test/
├── config.py                          # Configuration
├── .env                               # Your API keys  
├── test_complete_data_layer.py        # Complete test suite
├── data/
│   ├── models/schemas.py              # All data models
│   ├── database/
│   │   ├── chroma_client.py          # Vector search
│   │   └── database_manager.py        # Main interface
│   ├── processors/
│   │   └── event_processor.py         # AI processing
│   └── mock_data/
│       └── data_generator.py          # Demo data
```

## 🎉 Ready for Production

This data layer provides:
- ✅ **Scalable Architecture**: Easy to extend with more databases
- ✅ **AI-Powered**: Smart event processing and search
- ✅ **Location-Aware**: Geographic data and queries
- ✅ **Type-Safe**: Full Pydantic validation
- ✅ **Test Coverage**: Comprehensive test suite
- ✅ **Bengaluru-Ready**: Local data and scenarios

**Your data foundation is complete!** 🚀

Ready to build the FastAPI backend that will power your hackathon demo.
