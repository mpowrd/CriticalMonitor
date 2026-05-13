# System Architecture

## Overview

The Critical Systems Monitoring Platform implements a three-tier architecture for real-time anomaly detection in industrial environments.

## Components

### 1. ML Detection Layer

| Model | Approach | Performance |
|-------|----------|-------------|
| LSTM | Sequence prediction | MAE: 0.696, 77 anomalies |
| Autoencoder | Reconstruction error | MAE: 0.737, 72 anomalies |
| Isolation Forest | Statistical outliers | 73 anomalies detected |

**LSTM Architecture:**
- Input: Window of 3 time steps
- Layer 1: LSTM 50 units, ReLU activation, return sequences
- Layer 2: LSTM 50 units, ReLU activation
- Output: Dense(1) for single value prediction

**Autoencoder Architecture:**
- Encoder: LSTM 100 units
- Latent: RepeatVector (window_size)
- Decoder: LSTM 100 units, return sequences
- Output: TimeDistributed(Dense(1))

### 2. API Layer

- **Flask REST API** for data ingestion
- **RedisTimeSeries** for temporal storage with millisecond precision
- Synchronous anomaly detection on ingestion
- Health check endpoint for orchestration

### 3. Distributed Coordination Layer

- **ZooKeeper** for leader election using Kazoo
- **Ephemeral nodes** for measurement publishing
- **Leader** aggregates and reports to API
- Automatic failover on leader crash

## Data Flow

```
Sensor Data → Flask API → RedisTimeSeries
                         ↓
                    LSTM Prediction
                         ↓
                    Anomaly Check → Alert/Log
```

## Scaling Strategy

1. **Horizontal API Scaling**: Deploy multiple Flask instances behind Swarm router
2. **Redis Clustering**: Use Redis Cluster for high availability
3. **Stateless ML Inference**: Model loaded in each container

## Failure Modes

| Component | Failure | Recovery |
|-----------|---------|----------|
| Redis | Unavailable | API returns 503, retries on client |
| ZooKeeper | Partition | Elect new leader, continue operation |
| ML Model | Load failure | API operates without detection |
| Leader Node | Crash | New leader elected within seconds |

## API Contract

### POST /nuevo
Add sensor measurement
- Input: `?dato=<float>`
- Output: `{status, value, timestamp}`

### GET /detectar
Add and check for anomaly
- Input: `?dato=<float>`
- Output: `{value, timestamp, anomaly, prediction, error}`

### GET /listar
Retrieve all measurements
- Output: `{measurements: [{timestamp, value, datetime}]}`

## Deployment

The system deploys as a Docker Swarm stack with:
- 5 API replicas (configurable)
- Redis with RedisTimeSeries module
- ZooKeeper ensemble
- Grafana for visualization (optional)