import json
from datetime import datetime
from typing import Dict

from kafka import KafkaConsumer
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class EventProcessor:
    def __init__(self):
        # Kafka configuration
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'video_events')
        
        # MongoDB configuration
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'surveillance_db')
        self.mongodb_collection = os.getenv('MONGODB_COLLECTION', 'events')
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            self.kafka_topic,
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Initialize MongoDB client
        self.mongo_client = MongoClient(self.mongodb_uri)
        self.db = self.mongo_client[self.mongodb_database]
        self.collection = self.db[self.mongodb_collection]

    def process_event(self, event: Dict):
        """Process and store an event in MongoDB."""
        # Add processing timestamp
        event['processed_at'] = datetime.utcnow().isoformat()
        
        # Store in MongoDB
        self.collection.insert_one(event)
        print(f"Processed and stored event: {event}")

    def run(self):
        """Continuously consume and process events from Kafka."""
        print(f"Starting event processor. Consuming from {self.kafka_topic}")
        try:
            for message in self.consumer:
                event = message.value
                self.process_event(event)
        except KeyboardInterrupt:
            print("\nStopping event processor...")
        finally:
            self.consumer.close()
            self.mongo_client.close()

if __name__ == "__main__":
    processor = EventProcessor()
    processor.run() 