from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, Query
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Surveillance Video Event API",
    description="API for querying and analyzing surveillance video events",
    version="1.0.0"
)

# MongoDB configuration
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
mongodb_database = os.getenv('MONGODB_DATABASE', 'surveillance_db')
mongodb_collection = os.getenv('MONGODB_COLLECTION', 'events')

# Initialize MongoDB client
mongo_client = MongoClient(mongodb_uri)
db = mongo_client[mongodb_database]
collection = db[mongodb_collection]

@app.get("/")
async def root():
    return {"message": "Welcome to the Surveillance Video Event API"}

@app.get("/api/events")
async def get_events(
    limit: int = Query(10, description="Number of events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    zone: Optional[str] = Query(None, description="Filter by zone")
):
    query = {}
    if event_type:
        query['event_type'] = event_type
    if zone:
        query['zone'] = zone
    
    events = list(collection.find(query).sort('timestamp', -1).limit(limit))
    return events

@app.get("/api/events/stats")
async def get_event_stats():
    # Get total number of events
    total_events = collection.count_documents({})
    
    # Get event counts by type
    event_types = collection.distinct('event_type')
    event_counts = {
        event_type: collection.count_documents({'event_type': event_type})
        for event_type in event_types
    }
    
    # Get event counts by zone
    zones = collection.distinct('zone')
    zone_counts = {
        zone: collection.count_documents({'zone': zone})
        for zone in zones
    }
    
    return {
        "total_events": total_events,
        "event_counts": event_counts,
        "zone_counts": zone_counts
    }

@app.get("/api/events/trends")
async def get_event_trends(
    hours: int = Query(24, description="Number of hours to analyze"),
    zone: Optional[str] = Query(None, description="Filter by zone")
):
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Build query
    query = {
        'timestamp': {
            '$gte': start_time.isoformat(),
            '$lte': end_time.isoformat()
        }
    }
    if zone:
        query['zone'] = zone
    
    # Get events
    events = list(collection.find(query))
    
    if not events:
        return {"message": "No events found in the specified time range"}
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(events)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Group by hour and event type
    hourly_trends = df.groupby([
        df['timestamp'].dt.hour,
        'event_type'
    ]).size().unstack(fill_value=0)
    
    return {
        "hourly_trends": hourly_trends.to_dict(orient='index'),
        "total_events": len(events)
    }

@app.on_event("shutdown")
async def shutdown_event():
    mongo_client.close() 