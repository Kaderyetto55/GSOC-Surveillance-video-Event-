import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import time
from collections import defaultdict

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
mongodb_database = os.getenv('MONGODB_DATABASE', 'surveillance_db')
mongodb_collection = os.getenv('MONGODB_COLLECTION', 'events')

# Initialize MongoDB client
mongo_client = MongoClient(mongodb_uri)
db = mongo_client[mongodb_database]
collection = db[mongodb_collection]

def get_recent_events(hours=24):
    """Get events from the last N hours."""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    events = list(collection.find({
        'timestamp': {'$gte': start_time.isoformat()}
    }))
    return pd.DataFrame(events)

def create_event_timeline(df):
    """Create a timeline of events."""
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    timeline = df.groupby(['timestamp', 'event_type']).size().unstack(fill_value=0)
    
    fig = px.line(timeline, title='Event Timeline')
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Number of Events',
        hovermode='x unified'
    )
    return fig

def create_zone_heatmap(df):
    """Create a heatmap of events by zone and type."""
    pivot_table = pd.pivot_table(
        df,
        values='_id',
        index='zone',
        columns='event_type',
        aggfunc='count'
    )
    
    fig = px.imshow(
        pivot_table,
        title='Event Heatmap by Zone and Type',
        aspect='auto'
    )
    fig.update_layout(
        xaxis_title='Event Type',
        yaxis_title='Zone'
    )
    return fig

def create_confidence_distribution(df):
    """Create a distribution plot of confidence scores."""
    fig = px.box(
        df,
        x='event_type',
        y='confidence',
        title='Confidence Distribution by Event Type'
    )
    fig.update_layout(
        xaxis_title='Event Type',
        yaxis_title='Confidence Score'
    )
    return fig

def create_camera_stats(df):
    """Create camera statistics visualization."""
    camera_stats = df.groupby('metadata.camera_id').agg({
        '_id': 'count',
        'confidence': 'mean'
    }).reset_index()
    
    fig = px.scatter(
        camera_stats,
        x='_id',
        y='confidence',
        size='_id',
        hover_data=['metadata.camera_id'],
        title='Camera Activity and Confidence'
    )
    fig.update_layout(
        xaxis_title='Number of Events',
        yaxis_title='Average Confidence'
    )
    return fig

def create_alert_panel(df):
    """Create an alert panel for high-priority events."""
    high_confidence_events = df[df['confidence'] > 0.9]
    
    if not high_confidence_events.empty:
        st.warning("⚠️ High Confidence Events Detected!")
        for _, event in high_confidence_events.iterrows():
            st.error(f"""
            **Event Type:** {event['event_type']}
            **Zone:** {event['zone']}
            **Confidence:** {event['confidence']:.2f}
            **Time:** {event['timestamp']}
            """)
    else:
        st.success("✅ No high-priority alerts")

def create_zone_timeline(df):
    """Create a timeline of events by zone."""
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    zone_timeline = df.groupby(['timestamp', 'zone']).size().unstack(fill_value=0)
    
    fig = px.area(
        zone_timeline,
        title='Events by Zone Over Time',
        groupnorm='percent'
    )
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Percentage of Events',
        hovermode='x unified'
    )
    return fig

def main():
    st.set_page_config(page_title="Surveillance Dashboard", layout="wide")
    
    # Add auto-refresh
    st.sidebar.header("Controls")
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 60, 30)
    hours = st.sidebar.slider("Time Range (hours)", 1, 72, 24)
    
    # Main title and description
    st.title("Surveillance Video Event Dashboard")
    st.markdown("""
    This dashboard provides real-time monitoring and analysis of surveillance events.
    Data is automatically refreshed every {} seconds.
    """.format(refresh_interval))
    
    # Get data
    df = get_recent_events(hours)
    
    # Alert Panel
    st.subheader("Alert Panel")
    create_alert_panel(df)
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Events", len(df))
    with col2:
        st.metric("Unique Zones", df['zone'].nunique())
    with col3:
        st.metric("Event Types", df['event_type'].nunique())
    with col4:
        st.metric("High Confidence Events", len(df[df['confidence'] > 0.9]))
    
    # Main visualizations
    st.subheader("Event Timeline")
    st.plotly_chart(create_event_timeline(df), use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Event Heatmap")
        st.plotly_chart(create_zone_heatmap(df), use_container_width=True)
    
    with col2:
        st.subheader("Confidence Distribution")
        st.plotly_chart(create_confidence_distribution(df), use_container_width=True)
    
    # Additional visualizations
    st.subheader("Camera Statistics")
    st.plotly_chart(create_camera_stats(df), use_container_width=True)
    
    st.subheader("Events by Zone")
    st.plotly_chart(create_zone_timeline(df), use_container_width=True)
    
    # Recent events table with filtering
    st.subheader("Recent Events")
    event_types = st.multiselect(
        "Filter by Event Type",
        options=df['event_type'].unique(),
        default=df['event_type'].unique()
    )
    
    zones = st.multiselect(
        "Filter by Zone",
        options=df['zone'].unique(),
        default=df['zone'].unique()
    )
    
    filtered_df = df[
        (df['event_type'].isin(event_types)) &
        (df['zone'].isin(zones))
    ]
    
    st.dataframe(
        filtered_df[['timestamp', 'event_type', 'zone', 'confidence']].tail(10),
        use_container_width=True
    )
    
    # Auto-refresh
    time.sleep(refresh_interval)
    st.experimental_rerun()

if __name__ == "__main__":
    main() 