import argparse
import time
from video_processor.processor import VideoProcessor
import cv2
import numpy as np
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from kafka import KafkaProducer

# Load environment variables
load_dotenv()

class CameraStreamer:
    def __init__(self):
        self.processor = VideoProcessor()
        self.alert_threshold = float(os.getenv('ALERT_THRESHOLD', '0.8'))
        self.alert_topic = os.getenv('ALERT_TOPIC', 'video_alerts')
        
        # Initialize Kafka producer for alerts
        try:
            self.alert_producer = KafkaProducer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        except Exception as e:
            print(f"Warning: Failed to connect to Kafka: {e}")
            self.alert_producer = None
        
        # Alert history
        self.alert_history = []
        self.max_history = 100
        
        # Frame processing settings
        self.frame_skip = 2  # Process every nth frame
        self.frame_count = 0

    def create_alert(self, event: dict, alert_type: str, severity: str):
        """Create and send an alert."""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'zone': event['zone'],
            'event': event
        }
        
        # Send alert to Kafka if connected
        if self.alert_producer:
            try:
                self.alert_producer.send(self.alert_topic, value=alert)
            except Exception as e:
                print(f"Warning: Failed to send alert to Kafka: {e}")
        
        # Update alert history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
        
        print(f"ALERT: {alert_type} - {severity} - Zone: {event['zone']}")

    def check_alerts(self, event: dict):
        """Check for conditions that should trigger alerts."""
        # Check for high confidence events
        if event['confidence'] > self.alert_threshold:
            self.create_alert(event, 'high_confidence_detection', 'high')
        
        # Check for anomalies
        if event['metadata']['is_anomaly']:
            self.create_alert(event, 'camera_anomaly', 'medium')
        
        # Check for multiple faces
        if event['metadata']['faces_detected'] > 5:
            self.create_alert(event, 'crowd_detected', 'medium')
        
        # Check for sudden lighting changes
        if event['metadata']['lighting_change'] > 0.7:
            self.create_alert(event, 'lighting_anomaly', 'low')
        
        # Check for potential tampering
        if event['metadata']['tampering_score'] > 0.9:
            self.create_alert(event, 'potential_tampering', 'high')

    def display_frame(self, frame: np.ndarray, event: dict):
        """Display the frame with detection information."""
        # Create a copy of the frame
        display = frame.copy()
        
        # Draw detection boxes
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.processor.face_cascade.detectMultiScale(gray, 1.3, 5)
        bodies = self.processor.body_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Draw face boxes
        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.putText(display, 'Face', (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Draw body boxes
        for (x, y, w, h) in bodies:
            cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(display, 'Body', (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Add text overlay with black background for better visibility
        info_text = [
            f"Faces: {event['metadata']['faces_detected']}",
            f"Bodies: {event['metadata']['bodies_detected']}",
            f"Confidence: {event['confidence']:.2f}",
            f"Zone: {event['zone']}",
            f"Motion Score: {event['metadata']['motion_score']:.2f}",
            f"Anomaly: {'Yes' if event['metadata']['is_anomaly'] else 'No'}"
        ]
        
        # Calculate the background rectangle size
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        padding = 10
        
        # Get the size of the text block
        text_sizes = [cv2.getTextSize(text, font, font_scale, thickness)[0] for text in info_text]
        block_width = max(width for (width, height) in text_sizes) + 2 * padding
        block_height = sum(height for (width, height) in text_sizes) + padding * (len(info_text) + 1)
        
        # Draw semi-transparent background
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (block_width, block_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, display, 0.5, 0, display)
        
        # Draw text
        y = padding
        for i, text in enumerate(info_text):
            y += text_sizes[i][1] + padding
            cv2.putText(display, text, (padding, y),
                       font, font_scale, (255, 255, 255), thickness)
        
        return display

    def stream_camera(self, camera_id: int, zone: str, display: bool = True):
        """Stream from a camera with real-time processing and alerting."""
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"Error opening camera {camera_id}")
            return
        
        # Try to set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"Starting camera stream for zone: {zone}")
        print("Press 'q' to quit, 's' to save a snapshot")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error reading frame")
                    break
                
                # Process every nth frame
                if self.frame_count % self.frame_skip == 0:
                    # Process frame
                    event = self.processor.process_frame(frame, zone)
                    
                    # Check for alerts
                    self.check_alerts(event)
                    
                    # Display frame if requested
                    if display:
                        display_frame = self.display_frame(frame.copy(), event)
                        cv2.imshow('Camera Stream', display_frame)
                        
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            break
                        elif key == ord('s'):
                            # Save snapshot
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"snapshot_{timestamp}.jpg"
                            cv2.imwrite(filename, display_frame)
                            print(f"Saved snapshot: {filename}")
                
                self.frame_count += 1
                time.sleep(0.01)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            print("\nStopping camera stream...")
        except Exception as e:
            print(f"Error during streaming: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.alert_producer:
                self.alert_producer.close()

def main():
    parser = argparse.ArgumentParser(description='Stream from a camera with real-time processing and alerting')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID (default: 0)')
    parser.add_argument('--zone', type=str, required=True, help='Zone name (e.g., entrance, exit)')
    parser.add_argument('--no-display', action='store_true', help='Disable frame display')
    parser.add_argument('--skip-frames', type=int, default=2, help='Process every nth frame (default: 2)')
    
    args = parser.parse_args()
    
    streamer = CameraStreamer()
    streamer.frame_skip = args.skip_frames
    streamer.stream_camera(args.camera, args.zone, not args.no_display)

if __name__ == "__main__":
    main() 