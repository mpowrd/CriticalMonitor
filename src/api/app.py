"""
Critical Systems Monitoring API

REST API for real-time sensor data ingestion and anomaly detection.
Integrates with RedisTimeSeries for temporal data storage.
"""

from datetime import datetime
from flask import Flask, jsonify, request
from redis import Redis, RedisError
import os
import socket
import time
import json
import numpy as np
import tensorflow as tf
from keras.models import load_model


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redis = Redis(
    host=REDIS_HOST,
    db=0,
    socket_connect_timeout=2,
    socket_timeout=2
)

app = Flask(__name__)

WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "3"))
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.0"))

try:
    with open("UmbralDeAnomalias.txt", "r") as f:
        ANOMALY_THRESHOLD = float(f.readline().strip())
except FileNotFoundError:
    pass

MODEL_PATH = os.getenv("MODEL_PATH", "modelo.keras")
model = None
try:
    model = load_model(MODEL_PATH)
except Exception as e:
    print(f"Warning: Could not load model: {e}")


@app.route("/health")
def health_check():
    """Health check endpoint for container orchestration."""
    return jsonify({
        "status": "healthy",
        "hostname": socket.gethostname()
    })


@app.route("/metrics")
def metrics():
    """Expose application metrics."""
    try:
        visits = redis.incr("counter")
    except RedisError:
        visits = None
    return jsonify({
        "hostname": socket.gethostname(),
        "visits": visits,
        "model_loaded": model is not None
    })


@app.route("/nuevo", methods=["GET"])
def add_measurement():
    """
    Add new sensor measurement to time series.
    
    Query params:
        dato: float - sensor value
    
    Returns:
        JSON with confirmation and timestamp
    """
    dato = request.args.get("dato")
    if not dato:
        return jsonify({"error": "Missing 'dato' parameter"}), 400
    
    try:
        value = float(dato)
        timestamp = int(time.time() * 1000)
        redis.execute_command("TS.ADD", "mediciones_lista", timestamp, value)
        
        return jsonify({
            "status": "success",
            "value": value,
            "timestamp": timestamp
        })
    except ValueError:
        return jsonify({"error": "Value must be a number"}), 400
    except RedisError:
        return jsonify({"error": "Redis connection failed"}), 503


@app.route("/listar", methods=["GET"])
def list_measurements():
    """
    Retrieve all stored measurements.
    
    Returns:
        JSON array of measurements with timestamps
    """
    try:
        if not redis.exists("mediciones_lista"):
            return jsonify({"measurements": []})
        
        measurements = redis.execute_command("TS.RANGE", "mediciones_lista", "-", "+")
        results = []
        
        for ts, value in measurements:
            results.append({
                "timestamp": ts,
                "value": float(value),
                "datetime": datetime.fromtimestamp(int(ts) / 1000).isoformat()
            })
        
        return jsonify({"measurements": results})
    except RedisError:
        return jsonify({"error": "Redis connection failed"}), 503


@app.route("/eliminarLista", methods=["POST"])
def delete_measurements():
    """Clear all stored measurements."""
    try:
        if not redis.exists("mediciones_lista"):
            return jsonify({"status": "already_empty"})
        
        redis.delete("mediciones_lista")
        return jsonify({"status": "deleted"})
    except RedisError:
        return jsonify({"error": "Redis connection failed"}), 503


@app.route("/detectar", methods=["GET"])
def detect_anomaly():
    """
    Add measurement and detect if it's anomalous.
    
    Query params:
        dato: float - sensor value to check
    
    Returns:
        JSON with detection result, prediction, and error
    """
    dato = request.args.get("dato")
    if not dato:
        return jsonify({"error": "Missing 'dato' parameter"}), 400
    
    try:
        value = float(dato)
        timestamp = int(time.time() * 1000)
        
        measurements_list = []
        if redis.exists("mediciones_lista"):
            measurements_list = redis.execute_command("TS.RANGE", "mediciones_lista", "-", "+")
            measurements_np = np.array(measurements_list)
        
        redis.execute_command("TS.ADD", "mediciones_lista", timestamp, value)
        
        result = {
            "value": value,
            "timestamp": timestamp,
            "anomaly": False,
            "prediction": None,
            "error": 0
        }
        
        if model is not None and len(measurements_list) >= WINDOW_SIZE:
            window_values = [float(m[1]) for m in measurements_list[-WINDOW_SIZE:]]
            window_array = np.array(window_values).reshape((1, WINDOW_SIZE, 1))
            
            prediction = model.predict(window_array, verbose=0)[0][0]
            error = abs(float(prediction) - value)
            
            result["prediction"] = float(prediction)
            result["error"] = float(error)
            result["anomaly"] = error > ANOMALY_THRESHOLD
        
        with open("Resultados.txt", "a") as f:
            f.write(f"{json.dumps(result)}\n")
        
        return jsonify(result)
        
    except ValueError:
        return jsonify({"error": "Value must be a number"}), 400
    except RedisError:
        return jsonify({"error": "Redis connection failed"}), 503


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", "80"))
    app.run(host="0.0.0.0", port=PORT)