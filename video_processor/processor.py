import cv2
import numpy as np
from datetime import datetime
import json
from typing import Dict, Tuple, Optional
import os
from dotenv import load_dotenv
from kafka import KafkaProducer
import threading
import queue
import time

# Load environment variables
load_dotenv()

class VideoProcessor:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'video_events')
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Initialize OpenCV components
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Motion detection parameters
        self.prev_frame = None
        self.motion_threshold = 1000  # Adjust based on sensitivity needed
        
        # Streaming parameters
        self.stream_queue = queue.Queue()
        self.is_streaming = False
        self.stream_thread = None

    def detect_motion(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Detect motion in the frame using frame differencing."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return False, 0.0
        
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Calculate motion score
        motion_score = np.sum(thresh) / thresh.size
        
        self.prev_frame = gray
        return motion_score > self.motion_threshold, motion_score

    def detect_objects(self, frame: np.ndarray) -> Dict:
        """Detect faces, bodies, and eyes in the frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        bodies = self.body_cascade.detectMultiScale(gray, 1.3, 5)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Calculate object sizes for better context
        face_sizes = [w * h for (x, y, w, h) in faces]
        body_sizes = [w * h for (x, y, w, h) in bodies]
        
        return {
            'faces': len(faces),
            'bodies': len(bodies),
            'eyes': len(eyes),
            'avg_face_size': np.mean(face_sizes) if face_sizes else 0,
            'avg_body_size': np.mean(body_sizes) if body_sizes else 0,
            'confidence': min(1.0, (len(faces) + len(bodies)) / 10)  # Normalize confidence
        }

    def detect_anomalies(self, frame: np.ndarray) -> Dict:
        """Detect potential anomalies in the frame."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame statistics
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # Detect sudden changes in lighting
        lighting_change = abs(mean_intensity - 128) / 128  # Normalize to [0,1]
        
        # Detect potential tampering (sudden changes in frame statistics)
        tampering_score = std_intensity / 128  # Normalize to [0,1]
        
        return {
            'lighting_change': float(lighting_change),
            'tampering_score': float(tampering_score),
            'is_anomaly': lighting_change > 0.5 or tampering_score > 0.8
        }

    def process_frame(self, frame: np.ndarray, zone: str) -> Dict:
        """Process a single frame and extract metadata."""
        # Detect motion
        motion_detected, motion_score = self.detect_motion(frame)
        
        # Detect objects
        objects = self.detect_objects(frame)
        
        # Detect anomalies
        anomalies = self.detect_anomalies(frame)
        
        # Create event
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'motion_detected' if motion_detected else 'object_detected',
            'zone': zone,
            'confidence': objects['confidence'],
            'metadata': {
                'faces_detected': objects['faces'],
                'bodies_detected': objects['bodies'],
                'eyes_detected': objects['eyes'],
                'avg_face_size': float(objects['avg_face_size']),
                'avg_body_size': float(objects['avg_body_size']),
                'motion_score': float(motion_score),
                'lighting_change': anomalies['lighting_change'],
                'tampering_score': anomalies['tampering_score'],
                'is_anomaly': anomalies['is_anomaly'],
                'frame_size': f"{frame.shape[1]}x{frame.shape[0]}"
            }
        }
        
        return event

    def process_video(self, video_path: str, zone: str):
        """Process a video file and send events to Kafka."""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Error opening video file: {video_path}")
            return
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Process every 30th frame (adjust as needed)
            if frame_count % 30 == 0:
                event = self.process_frame(frame, zone)
                self.producer.send(self.kafka_topic, value=event)
                print(f"Sent event: {event}")
            
            frame_count += 1
        
        cap.release()
        self.producer.close()

    def start_stream(self, camera_id: int, zone: str):
        """Start real-time video streaming from a camera."""
        self.is_streaming = True
        self.stream_thread = threading.Thread(
            target=self._stream_worker,
            args=(camera_id, zone)
        )
        self.stream_thread.start()

    def stop_stream(self):
        """Stop the video stream."""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join()

    def _stream_worker(self, camera_id: int, zone: str):
        """Worker thread for processing video stream."""
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"Error opening camera {camera_id}")
            return
        
        frame_count = 0
        while self.is_streaming:
            ret, frame = cap.read()
            if not ret:
                print(f"Error reading frame from camera {camera_id}")
                break
            
            # Process every 30th frame
            if frame_count % 30 == 0:
                event = self.process_frame(frame, zone)
                self.producer.send(self.kafka_topic, value=event)
                print(f"Sent stream event: {event}")
            
            frame_count += 1
            time.sleep(0.033)  # ~30 FPS
        
        cap.release()

if __name__ == "__main__":
    processor = VideoProcessor()
    # Example usage with a video file
    # processor.process_video("path/to/video.mp4", "entrance")
    
    # Example usage with webcam
    # processor.start_stream(0, "entrance")  # 0 is usually the default webcam
    # time.sleep(60)  # Run for 60 seconds
    # processor.stop_stream() 