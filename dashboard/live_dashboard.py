import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import time
from video_processor.processor import VideoProcessor
import threading
import queue

# Initialize session state
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'frame_queue' not in st.session_state:
    st.session_state.frame_queue = queue.Queue()
if 'events' not in st.session_state:
    st.session_state.events = []
if 'processor' not in st.session_state:
    st.session_state.processor = VideoProcessor()
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

def process_camera_feed():
    """Process camera feed in a separate thread."""
    cap = cv2.VideoCapture(0)
    
    while st.session_state.camera_active:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to read camera frame")
            break
            
        # Process frame
        event = st.session_state.processor.process_frame(frame, "entrance")
        st.session_state.events.append(event)
        
        # Keep only last 100 events
        if len(st.session_state.events) > 100:
            st.session_state.events.pop(0)
        
        # Put frame in queue
        st.session_state.frame_queue.put((frame, event))
        
        time.sleep(0.033)  # ~30 FPS
    
    cap.release()

def create_event_timeline(events):
    """Create timeline of events."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig = px.scatter(df, x='timestamp', y='confidence',
                    color='event_type',
                    title='Event Timeline',
                    hover_data=['zone', 'metadata'])
    
    return fig

def create_heatmap(events):
    """Create heatmap of events by zone and type."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    event_counts = df.groupby(['zone', 'event_type']).size().reset_index(name='count')
    
    fig = px.density_heatmap(event_counts, x='zone', y='event_type',
                           title='Event Heatmap by Zone and Type',
                           color='count')
    
    return fig

def create_confidence_distribution(events):
    """Create distribution of confidence scores."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    
    fig = px.histogram(df, x='confidence',
                      title='Confidence Score Distribution',
                      nbins=20)
    
    return fig

def create_camera_stats(events):
    """Create camera activity and confidence statistics."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    
    # Calculate average confidence by event type
    avg_confidence = df.groupby('event_type')['confidence'].mean().reset_index()
    
    fig = px.bar(avg_confidence, x='event_type', y='confidence',
                 title='Average Confidence by Event Type')
    
    return fig

def create_alert_panel(events):
    """Create panel for high-confidence events."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    high_confidence = df[df['confidence'] > 0.8]
    
    if high_confidence.empty:
        return None
    
    return high_confidence.tail(5)

def create_zone_timeline(events):
    """Create timeline of events by zone."""
    if not events:
        return None
    
    df = pd.DataFrame(events)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig = px.line(df, x='timestamp', y='confidence',
                  color='zone',
                  title='Events by Zone Over Time')
    
    return fig

def display_report(events):
    """Display real-time report of events."""
    if not events:
        return
    
    df = pd.DataFrame(events)
    
    # Calculate statistics
    total_events = len(df)
    high_confidence_events = len(df[df['confidence'] > 0.8])
    face_detections = len(df[df['event_type'] == 'face'])
    body_detections = len(df[df['event_type'] == 'body'])
    motion_detections = len(df[df['event_type'] == 'motion'])
    
    # Create metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Events", total_events)
    with col2:
        st.metric("High Confidence Events", high_confidence_events)
    with col3:
        st.metric("Face Detections", face_detections)
    with col4:
        st.metric("Body Detections", body_detections)
    with col5:
        st.metric("Motion Detections", motion_detections)
    
    # Display recent events
    st.subheader("Recent Events")
    recent_events = df.tail(5)
    for _, event in recent_events.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{event['event_type'].title()}** detected in {event['zone']}")
            with col2:
                st.write(f"Confidence: {event['confidence']:.2f}")
            with col3:
                st.write(f"Time: {event['timestamp']}")

def main():
    st.set_page_config(page_title="Surveillance Dashboard", layout="wide")
    st.title("Surveillance System Dashboard")
    
    # Sidebar controls
    st.sidebar.title("Controls")
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 5)
    
    # Camera controls
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if not st.session_state.camera_active:
            if st.button("Start Camera"):
                st.session_state.camera_active = True
                threading.Thread(target=process_camera_feed, daemon=True).start()
    with col2:
        if st.session_state.camera_active:
            if st.button("Stop Camera"):
                st.session_state.camera_active = False
    
    # Main content
    if st.session_state.camera_active:
        # Live camera feed and report
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("Live Camera Feed")
            camera_placeholder = st.empty()
            
            # Process and display frames
            while st.session_state.camera_active:
                try:
                    frame, event = st.session_state.frame_queue.get(timeout=1)
                    
                    # Convert frame to RGB for display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Draw detection boxes
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = st.session_state.processor.face_cascade.detectMultiScale(gray, 1.3, 5)
                    bodies = st.session_state.processor.body_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    # Draw face boxes
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame_rgb, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    
                    # Draw body boxes
                    for (x, y, w, h) in bodies:
                        cv2.rectangle(frame_rgb, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Display frame
                    camera_placeholder.image(frame_rgb, channels="RGB")
                    
                except queue.Empty:
                    continue
        
        with col2:
            st.header("Real-time Report")
            display_report(st.session_state.events)
    
    # Event statistics
    st.header("Event Statistics")
    
    # Create columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Event timeline
        timeline_fig = create_event_timeline(st.session_state.events)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)
        
        # Heatmap
        heatmap_fig = create_heatmap(st.session_state.events)
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)
    
    with col2:
        # Confidence distribution
        conf_fig = create_confidence_distribution(st.session_state.events)
        if conf_fig:
            st.plotly_chart(conf_fig, use_container_width=True)
        
        # Camera stats
        stats_fig = create_camera_stats(st.session_state.events)
        if stats_fig:
            st.plotly_chart(stats_fig, use_container_width=True)
    
    # Alert panel
    st.header("Recent Alerts")
    alert_df = create_alert_panel(st.session_state.events)
    if alert_df is not None and not alert_df.empty:
        st.dataframe(alert_df)
    else:
        st.info("No high-confidence events detected")
    
    # Zone timeline
    st.header("Events by Zone")
    zone_fig = create_zone_timeline(st.session_state.events)
    if zone_fig:
        st.plotly_chart(zone_fig, use_container_width=True)

if __name__ == "__main__":
    main() 