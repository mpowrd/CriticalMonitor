"""Productor distribuido y elección de líder con ZooKeeper.

Cada instancia publica su última medición como nodo efímero. Solo el líder
calcula la media del conjunto y la envía a la API de Critical Signal.
"""

from __future__ import annotations

import os
import random
import signal
import threading
import time
import uuid

import numpy as np
import requests
from kazoo.client import KazooClient
from kazoo.recipe.election import Election


NODE_ID = os.getenv("ID", str(uuid.uuid4())[:8])
ZOOKEEPER_HOST = os.getenv("ZOOKEEPER_HOST", "zookeeper:2181")
WEB_URL = os.getenv("WEB_URL", "http://web:80/nuevo")
MEASUREMENTS_PATH = "/mediciones"

client = KazooClient(hosts=ZOOKEEPER_HOST)


def connect_zookeeper():
    for attempt in range(1, 13):
        try:
            client.start(timeout=5)
            return
        except Exception as exc:
            print(f"ZooKeeper aún no está listo ({attempt}/12): {exc}")
            time.sleep(2)
    raise RuntimeError("No se pudo conectar con ZooKeeper después de 12 intentos")


connect_zookeeper()
client.ensure_path(MEASUREMENTS_PATH)
election = Election(client, "/election", NODE_ID)


def interrupt_handler(_signal, _frame):
    print(f"La aplicación {NODE_ID} ha terminado")
    client.stop()
    client.close()
    raise SystemExit(0)


signal.signal(signal.SIGINT, interrupt_handler)
signal.signal(signal.SIGTERM, interrupt_handler)


def leader_func():
    """Agrega las mediciones de los nodos mientras esta instancia sea líder."""
    while True:
        children = client.get_children(MEASUREMENTS_PATH)
        measurements = []

        for name in children:
            try:
                data, _ = client.get(f"{MEASUREMENTS_PATH}/{name}")
                measurements.append(float(data.decode("utf-8")))
            except (ValueError, TypeError):
                print(f"Medición inválida en {name}; se ignora")

        if measurements:
            average = float(np.mean(measurements))
            print(f"Líder {NODE_ID} · {len(measurements)} nodos · media {average:.2f}")
            try:
                response = requests.get(WEB_URL, params={"dato": average}, timeout=5)
                response.raise_for_status()
                print("Media enviada a Critical Signal")
            except requests.RequestException as exc:
                print(f"No se pudo enviar la media: {exc}")
        else:
            print("Líder a la espera de mediciones")

        time.sleep(5)


def election_func():
    election.run(leader_func)


election_thread = threading.Thread(target=election_func, daemon=True)
election_thread.start()

try:
    while True:
        value = str(random.randint(75, 85))
        node_path = f"{MEASUREMENTS_PATH}/value{NODE_ID}"
        if client.exists(node_path):
            client.set(node_path, value.encode("utf-8"))
        else:
            client.create(node_path, value.encode("utf-8"), ephemeral=True)
        print(f"Nodo {NODE_ID} · valor {value}")
        time.sleep(5)
except (KeyboardInterrupt, ConnectionError):
    interrupt_handler(None, None)
