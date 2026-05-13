"""
Distributed Coordinator Service

Provides distributed coordination using Apache ZooKeeper for leader election.
Leader aggregates measurements from all nodes and reports to central API.
"""

from kazoo.client import KazooClient
from kazoo.recipe.election import Election
import threading
import time
import random
import os
import requests
import numpy as np
import uuid
import signal
import sys


class CoordinatorService:
    """Distributed coordination service with leader election."""
    
    def __init__(self):
        self.instance_id = os.getenv('INSTANCE_ID', str(uuid.uuid4()))
        self.zookeeper_host = os.getenv('ZOOKEEPER_HOST', 'zookeeper:2181')
        self.api_url = os.getenv('API_URL', 'http://web:80/nuevo')
        self.client = None
        self.election = None
        self.running = True
        
    def connect(self):
        """Establish connection to ZooKeeper ensemble."""
        self.client = KazooClient(hosts=self.zookeeper_host)
        self.client.start()
        self.election = Election(self.client, "/election", self.instance_id)
        
    def shutdown_handler(self, signum, frame):
        """Handle graceful shutdown."""
        print(f"Instance {self.instance_id} shutting down...")
        self.running = False
        if self.client:
            self.client.stop()
        sys.exit(0)
    
    def aggregate_measurements(self):
        """Collect and aggregate measurements from all nodes."""
        try:
            children = self.client.get_children("/mediciones")
            
            if not children:
                return None
                
            measurements = []
            for child in children:
                try:
                    data, _ = self.client.get(f"/mediciones/{child}")
                    value = int(data.decode("utf-8")) if isinstance(data, bytes) else int(data)
                    measurements.append(value)
                except (ValueError, Exception) as e:
                    print(f"Error reading {child}: {e}")
                    
            if measurements:
                return np.mean(measurements)
            return None
            
        except Exception as e:
            print(f"Aggregation error: {e}")
            return None
    
    def send_to_api(self, value):
        """Send aggregated value to central API."""
        try:
            response = requests.get(self.api_url, params={'dato': value}, timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"API call failed: {e}")
            return False
    
    def leader_task(self):
        """Task executed by elected leader."""
        while self.running:
            print(f"[Leader {self.instance_id}] Computing aggregation...")
            
            mean_value = self.aggregate_measurements()
            
            if mean_value is not None:
                print(f"[Leader] Mean: {mean_value:.2f}")
                self.send_to_api(mean_value)
            
            time.sleep(5)
    
    def run_leader(self):
        """Run leader election and execute leader task."""
        self.election.run(self.leader_task)
    
    def publish_measurement(self):
        """Generate and publish measurement to ZooKeeper."""
        value = random.randint(75, 85)
        
        try:
            self.client.ensure_path("/mediciones")
            node_path = f"/mediciones/value{self.instance_id}"
            
            if self.client.exists(node_path):
                self.client.set(node_path, str(value).encode("utf-8"))
            else:
                self.client.create(node_path, str(value).encode("utf-8"), ephemeral=True)
                
        except Exception as e:
            print(f"Publish error: {e}")
    
    def run(self):
        """Start the coordinator service."""
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        
        self.connect()
        print(f"Instance {self.instance_id} connected to ZooKeeper")
        
        election_thread = threading.Thread(target=self.run_leader, daemon=True)
        election_thread.start()
        
        while self.running:
            self.publish_measurement()
            print(f"[{self.instance_id}] Published: {random.randint(75, 85)}")
            time.sleep(5)


if __name__ == "__main__":
    service = CoordinatorService()
    service.run()