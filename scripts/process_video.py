import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from video_processor.processor import VideoProcessor

def main():
    parser = argparse.ArgumentParser(description='Process a video file and send events to Kafka')
    parser.add_argument('video_path', help='Path to the video file')
    parser.add_argument('zone', help='Zone name (e.g., entrance, exit)')
    
    args = parser.parse_args()
    
    processor = VideoProcessor()
    processor.process_video(args.video_path, args.zone)

if __name__ == "__main__":
    main() 