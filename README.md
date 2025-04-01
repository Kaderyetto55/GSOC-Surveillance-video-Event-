# Surveillance Video Event Detection System

A real-time video surveillance system that detects and analyzes events using computer vision and machine learning techniques.

## Features

- Real-time video processing and event detection
- Face and body detection using OpenCV
- Motion detection and analysis
- Real-time dashboard with live camera feed
- Event statistics and analytics
- Alert system for high-confidence events
- RESTful API for data access
- MongoDB integration for event storage
- Kafka for event streaming

## System Architecture

The system consists of several interconnected components:
1. Video Processing Module
2. Event Detection Engine
3. Data Storage System
4. Real-time Monitoring Dashboard
5. API Server
6. Alert System

For detailed technical specifications, see [Technical Architecture](docs/technical_architecture.md).

## Prerequisites

- Python 3.11 or higher
- OpenCV 4.x
- MongoDB 5.x
- Kafka 3.x
- Docker (optional)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Kaderyetto55/GSOC-Surveillance-video-Event-.git
cd GSOC-Surveillance-video-Event-
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

1. Start the required services (MongoDB, Kafka):
```bash
docker-compose up -d
```

2. Start the FastAPI server:
```bash
uvicorn api.main:app --reload
```

3. Launch the Streamlit dashboard:
```bash
streamlit run dashboard/live_dashboard.py
```

4. Process a video file:
```bash
python scripts/process_video.py path/to/your/video.mp4 entrance
```

5. Stream from camera:
```bash
python scripts/stream_camera.py --zone entrance
```

## API Documentation

The API documentation is available at `http://localhost:8000/docs` when the FastAPI server is running.

### Main Endpoints

- `/api/events`: Get events with filtering options
- `/api/events/recent`: Get recent events
- `/api/events/stats`: Get event statistics
- `/api/dashboard-stats`: Get dashboard statistics
- `/api/access-logs`: Get access logs
- `/api/intrusion-alerts`: Get intrusion alerts

## Dashboard Features

- Live camera feed with detection boxes
- Real-time event statistics
- Event timeline visualization
- Heatmap of events by zone and type
- Confidence score distribution
- Alert panel for high-confidence events
- Recent events table

## Development

### Project Structure

```
surveillance-video-event/
├── api/                    # FastAPI server
├── dashboard/             # Streamlit dashboard
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── tests/                 # Test files
├── video_processor/       # Video processing module
├── .env.example          # Example environment variables
├── docker-compose.yml    # Docker services configuration
├── requirements.txt      # Python dependencies
└── README.md            # Project documentation
```

### Running Tests

```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenCV for computer vision capabilities
- FastAPI for the API framework
- Streamlit for the dashboard
- MongoDB for data storage
- Kafka for event streaming 