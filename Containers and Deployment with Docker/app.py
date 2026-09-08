"""Critical Signal: API de monitorización y detección de anomalías.

La aplicación conserva las rutas originales de la práctica y añade una API JSON
para que la demo pueda ser consumida desde el dashboard o desde otros servicios.
"""

from __future__ import annotations

import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from flask import Flask, jsonify, render_template, request
from keras.models import load_model
from redis import Redis, RedisError


BASE_DIR = Path(__file__).resolve().parent
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PORT = int(os.getenv("PORT", "80"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "3"))
SERIES_NAME = os.getenv("SERIES_NAME", "mediciones_lista")
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(BASE_DIR / "modelo.keras")))
THRESHOLD_PATH = Path(
    os.getenv("THRESHOLD_PATH", str(BASE_DIR / "UmbralDeAnomalias.txt"))
)

app = Flask(__name__)

redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def load_threshold() -> float:
    """Carga el umbral generado por el entrenamiento del autoencoder."""
    try:
        return float(THRESHOLD_PATH.read_text(encoding="utf-8").splitlines()[0])
    except (FileNotFoundError, ValueError, IndexError):
        return float(os.getenv("ANOMALY_THRESHOLD", "2.2125982130317277"))


ANOMALY_THRESHOLD = load_threshold()
MODEL: Any | None = None
MODEL_ERROR: str | None = None

try:
    MODEL = load_model(MODEL_PATH)
except (OSError, ValueError, ImportError) as exc:
    MODEL_ERROR = str(exc)


def utc_iso(timestamp_ms: int) -> str:
    """Devuelve una fecha ISO 8601 legible y estable entre entornos."""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def read_measurements(limit: int | None = None) -> list[dict[str, Any]]:
    """Lee la serie temporal y normaliza la respuesta de Redis a JSON."""
    # Una demo recién arrancada todavía no tiene una serie creada.
    # Es un estado vacío válido, no un fallo de Redis.
    if not redis_client.exists(SERIES_NAME):
        return []
    raw = redis_client.execute_command("TS.RANGE", SERIES_NAME, "-", "+")
    measurements = [
        {
            "timestamp": int(timestamp),
            "time": utc_iso(int(timestamp)),
            "value": float(value),
        }
        for timestamp, value in raw
    ]
    return measurements[-limit:] if limit else measurements


def parse_value(source: Any) -> float:
    """Valida y convierte el valor recibido por query string o JSON."""
    if isinstance(source, dict) or hasattr(source, "get"):
        source = source.get("value", source.get("dato"))
    if source is None or str(source).strip() == "":
        raise ValueError("Falta el valor de la medición.")
    value = float(source)
    if not np.isfinite(value):
        raise ValueError("La medición debe ser un número finito.")
    return value


def predict(value: float, previous: list[dict[str, Any]]) -> dict[str, Any]:
    """Predice el siguiente valor y clasifica la medición actual."""
    if len(previous) < WINDOW_SIZE:
        return {
            "status": "warming_up",
            "anomaly": False,
            "anomaly_label": "Recopilando contexto",
            "prediction": None,
            "error": None,
        }

    if MODEL is None:
        return {
            "status": "model_unavailable",
            "anomaly": None,
            "anomaly_label": "Modelo no disponible",
            "prediction": None,
            "error": None,
        }

    window = np.array([item["value"] for item in previous[-WINDOW_SIZE:]])
    model_input = window.reshape((1, WINDOW_SIZE, 1))
    model_output = np.asarray(MODEL.predict(model_input, verbose=0))
    # El artefacto guardado es un autoencoder LSTM que reconstruye la ventana.
    # Usamos el último paso, igual que en el experimento que generó el umbral.
    prediction = (
        float(model_output[0, -1, 0])
        if model_output.ndim == 3
        else float(model_output.reshape(-1)[0])
    )
    error = abs(prediction - value)
    anomaly = error > ANOMALY_THRESHOLD
    return {
        "status": "anomaly" if anomaly else "normal",
        "anomaly": anomaly,
        "anomaly_label": "Anomalía detectada" if anomaly else "Dentro del patrón",
        "prediction": prediction,
        "error": error,
    }


def enrich_measurements(
    measurements: list[dict[str, Any]], limit: int = 40
) -> list[dict[str, Any]]:
    """Añade el estado de anomalía de cada señal para la visualización."""
    start = max(0, len(measurements) - limit)
    enriched = []
    for index in range(start, len(measurements)):
        item = measurements[index]
        analysis = predict(item["value"], measurements[:index])
        enriched.append(
            item
            | {
                "anomaly": analysis["anomaly"],
                "status": analysis["status"],
            }
        )
    return enriched


def base_payload() -> dict[str, Any]:
    return {
        "service": "critical-signal-api",
        "hostname": socket.gethostname(),
        "threshold": ANOMALY_THRESHOLD,
        "window_size": WINDOW_SIZE,
        "model_loaded": MODEL is not None,
    }


@app.get("/")
def dashboard():
    return render_template(
        "index.html",
        threshold=ANOMALY_THRESHOLD,
        window_size=WINDOW_SIZE,
        model_loaded=MODEL is not None,
        hostname=socket.gethostname(),
    )


@app.get("/api/health")
def health():
    try:
        redis_client.ping()
        redis_status = "connected"
    except RedisError:
        redis_status = "unavailable"

    ready = redis_status == "connected" and MODEL is not None
    response = base_payload() | {
        "status": "ok" if ready else "degraded",
        "redis": redis_status,
        "model_error": MODEL_ERROR,
    }
    return jsonify(response), 200 if ready else 503


@app.get("/api/measurements")
def measurements():
    try:
        limit = min(max(int(request.args.get("limit", 40)), 1), 200)
        history = read_measurements()
        return jsonify(
            base_payload()
            | {"measurements": enrich_measurements(history, limit)}
        )
    except (RedisError, ValueError) as exc:
        return jsonify({"error": f"No se pudieron leer las mediciones: {exc}"}), 503


def store_measurement(value: float) -> dict[str, Any]:
    previous = read_measurements()
    timestamp = int(time.time() * 1000)
    redis_client.execute_command("TS.ADD", SERIES_NAME, timestamp, value)
    analysis = predict(value, previous)
    measurement = {"timestamp": timestamp, "time": utc_iso(timestamp), "value": value}
    result = base_payload() | {
        "measurement": measurement,
        "analysis": analysis,
        "measurements": enrich_measurements(previous + [measurement]),
    }

    with (BASE_DIR / "Resultados.txt").open("a", encoding="utf-8") as file:
        file.write(f"{result}\n")
    return result


@app.post("/api/detect")
def detect_api():
    try:
        payload = request.get_json(silent=True) or request.args.to_dict()
        value = parse_value(payload)
        return jsonify(store_measurement(value))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RedisError:
        return jsonify({"error": "RedisTimeSeries no está disponible."}), 503


@app.post("/api/reset")
def reset_api():
    try:
        deleted = bool(redis_client.delete(SERIES_NAME))
        return jsonify({"deleted": deleted, "message": "Serie reiniciada."})
    except RedisError:
        return jsonify({"error": "RedisTimeSeries no está disponible."}), 503


# Compatibilidad con las rutas utilizadas en las prácticas y en ZooKeeper.
@app.get("/nuevo")
def add_legacy():
    try:
        value = parse_value(request.args)
        previous = read_measurements()
        timestamp = int(time.time() * 1000)
        redis_client.execute_command("TS.ADD", SERIES_NAME, timestamp, value)
        return jsonify(
            {"ok": True, "value": value, "timestamp": timestamp, "context": len(previous)}
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except RedisError:
        return jsonify({"ok": False, "error": "RedisTimeSeries no está disponible."}), 503


@app.route("/detectar", methods=["GET", "POST"])
def detect_legacy():
    return detect_api()


@app.get("/listar")
def list_legacy():
    return measurements()


@app.get("/eliminarLista")
def delete_legacy():
    return reset_api()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
