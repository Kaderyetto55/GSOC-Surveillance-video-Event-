import json
import random
import time
from datetime import datetime
from typing import Dict, List

from kafka import KafkaProducer
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class VideoEventGenerator:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'video_events')
        self.interval = float(os.getenv('GENERATOR_INTERVAL', '1.0'))
        self.zones = json.loads(os.getenv('GENERATOR_ZONES', '["entrance", "parking", "lobby", "elevator"]'))
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def generate_event(self) -> Dict:
        """Generate a random video event."""
        event_types = ['motion_detected', 'person_detected', 'object_detected', 'face_detected']
        confidence = round(random.uniform(0.5, 1.0), 2)
        
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': random.choice(event_types),
            'zone': random.choice(self.zones),
            'confidence': confidence,
            'metadata': {
                'camera_id': f'cam_{random.randint(1, 10)}',
                'resolution': f'{random.choice([720, 1080, 1440])}p',
                'frame_number': random.randint(1, 1000)
            }
        }
        
        return event

    def run(self):
        """Continuously generate and send events to Kafka."""
        print(f"Starting video event generator. Sending events to {self.kafka_topic}")
        try:
            while True:
                event = self.generate_event()
                self.producer.send(self.kafka_topic, value=event)
                print(f"Sent event: {event}")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nStopping event generator...")
        finally:
            self.producer.close()

if __name__ == "__main__":
    generator = VideoEventGenerator()
    generator.run() 