# Critical Systems Monitoring Platform

Real-time anomaly detection system for industrial sensor data, built with machine learning, containerized microservices, and distributed coordination.

## Overview

This platform monitors industrial device temperatures and detects anomalies using three complementary approaches:

- **LSTM Neural Network**: Sequence prediction-based detection (MAE: 0.696, 77 anomalies detected)
- **Autoencoder**: Reconstruction error-based detection (MAE: 0.737)
- **Isolation Forest**: Statistical outlier detection

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Sensor     │     │   Flask     │     │   Redis     │
│  Nodes      │────▶│   API       │────▶│  TimeSeries │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    LSTM     │
                    │   Model     │
                    └─────────────┘

┌─────────────────────────────────────────────────┐
│              ZooKeeper Cluster                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │ Node 1  │   │ Node 2  │   │ Node 3  │       │
│  │ (Leader)│   │         │   │         │       │
│  └────┬────┘   └─────────┘   └─────────┘       │
└───────┼──────────────────────────────────────────┘
        │
        ▼
   Aggregates & reports to API
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| ML Models | TensorFlow/Keras, scikit-learn |
| API | Flask, Python |
| Time Series Storage | Redis (RedisTimeSeries) |
| Containerization | Docker, Docker Swarm |
| Distributed Coordination | Apache ZooKeeper (Kazoo) |

## Features

- Real-time anomaly detection with configurable thresholds
- Horizontal scaling via Docker Swarm
- Leader election for distributed aggregation
- RESTful API for data ingestion and querying
- Persistent time-series storage

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for local development)

### Run with Docker Compose

```bash
cd docker/api
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

### Run locally

```bash
# ML Models
cd src/ml
pip install -r requirements.txt
python -c "from models.anomaly_detector import LSTMAnomalyDetector; print('ML models ready')"

# API
cd src/api
pip install -r requirements.txt
python app.py

# Distributed
cd src/distributed
pip install -r requirements.txt
python coordinator.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Application metrics |
| `/nuevo?dato=<value>` | GET | Add measurement |
| `/listar` | GET | List all measurements |
| `/detectar?dato=<value>` | GET | Add & detect anomaly |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `REDIS_HOST` | localhost | Redis server hostname |
| `PORT` | 80 | API port |
| `WINDOW_SIZE` | 3 | LSTM input window size |
| `MODEL_PATH` | modelo.keras | Path to trained model |
| `ZOOKEEPER_HOST` | zookeeper:2181 | ZooKeeper connection |
| `API_URL` | http://web:80/nuevo | Central API endpoint |

## Performance

- **LSTM Model**: 77 anomalies detected from 7257 samples
- **Detection Accuracy**: MAE < 0.7
- **Containerized Deployment**: < 100MB image size

## Project Structure

```
├── src/
│   ├── ml/
│   │   ├── models/
│   │   │   └── anomaly_detector.py    # LSTM, Autoencoder, Isolation Forest
│   │   └── requirements.txt
│   ├── api/
│   │   ├── app.py                     # Flask REST API
│   │   └── requirements.txt
│   └── distributed/
│       ├── coordinator.py              # ZooKeeper leader election
│       └── requirements.txt
├── docker/
│   ├── api/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── ml/
│       └── Dockerfile
└── docs/
    └── architecture.md
```

## License

MIT License