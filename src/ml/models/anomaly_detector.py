"""
Anomaly Detection Models for Critical Systems Monitoring

This module provides three anomaly detection approaches:
1. LSTM Neural Network - sequence prediction based detection
2. Autoencoder - reconstruction error based detection
3. Isolation Forest - statistical outlier detection
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout, Input, RepeatVector, TimeDistributed
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest
import joblib


class LSTMAnomalyDetector:
    """LSTM-based anomaly detector using sequence prediction."""
    
    def __init__(self, window_size=3, n_features=1):
        self.window_size = window_size
        self.n_features = n_features
        self.model = None
        self.scaler = None
        
    def create_model(self):
        """Build stacked LSTM model architecture."""
        model = Sequential([
            Input(shape=(self.window_size, self.n_features)),
            LSTM(50, activation='relu', return_sequences=True),
            LSTM(50, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def prepare_data(self, data, window_size=None):
        """Create sliding windows from time series data."""
        ws = window_size or self.window_size
        raw_values = data.flatten()
        windows = np.lib.stride_tricks.sliding_window_view(raw_values, window_shape=ws)
        X = np.array(windows[:-1])
        y = np.array(raw_values[ws:])
        return X.reshape((X.shape[0], X.shape[1], self.n_features)), y
    
    def fit(self, data, epochs=200, batch_size=32):
        """Train the LSTM model."""
        X, y = self.prepare_data(data)
        self.model = self.create_model()
        self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=0)
        return self
    
    def predict(self, data):
        """Predict next values for anomaly detection."""
        X, _ = self.prepare_data(data)
        return self.model.predict(X, verbose=0).flatten()
    
    def detect_anomalies(self, data, threshold_multiplier=3):
        """Identify anomalies based on prediction error."""
        predicted = self.predict(data)
        _, y = self.prepare_data(data)
        mae = np.mean(np.abs(y - predicted))
        threshold = mae * threshold_multiplier
        anomalies = np.abs(y - predicted) > threshold
        return anomalies, threshold
    
    def save(self, path):
        """Save trained model."""
        self.model.save(path)
    
    @classmethod
    def load(cls, path, window_size=3):
        """Load pre-trained model."""
        instance = cls(window_size=window_size)
        instance.model = load_model(path)
        return instance


class AutoencoderAnomalyDetector:
    """Autoencoder-based anomaly detector using reconstruction error."""
    
    def __init__(self, window_size=3):
        self.window_size = window_size
        self.model = None
        
    def create_model(self):
        """Build encoder-decoder architecture."""
        model = Sequential([
            Input(shape=(self.window_size, 1)),
            LSTM(100, activation='relu'),
            RepeatVector(self.window_size),
            LSTM(100, activation='relu', return_sequences=True),
            TimeDistributed(Dense(1))
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def fit(self, data, epochs=100):
        """Train autoencoder to reconstruct normal patterns."""
        X = data.reshape((data.shape[0], data.shape[1], 1))
        self.model = self.create_model()
        self.model.fit(X, X, epochs=epochs, verbose=0)
        return self
    
    def detect_anomalies(self, data, threshold_multiplier=3):
        """Detect anomalies based on reconstruction error."""
        X = data.reshape((data.shape[0], data.shape[1], 1))
        reconstructed = self.model.predict(X, verbose=0)
        mse = np.mean(np.abs(X - reconstructed), axis=(1, 2))
        threshold = np.mean(mse) * threshold_multiplier
        anomalies = mse > threshold
        return anomalies, threshold
    
    def save(self, path):
        """Save trained model."""
        self.model.save(path)
    
    @classmethod
    def load(cls, path, window_size=3):
        """Load pre-trained model."""
        instance = cls(window_size=window_size)
        instance.model = load_model(path)
        return instance


class IsolationForestDetector:
    """Statistical anomaly detector using tree-based isolation."""
    
    def __init__(self, contamination=0.01, random_state=42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state
        )
    
    def fit(self, data):
        """Fit isolation forest to training data."""
        X = data.reshape(-1, 1)
        self.model.fit(X)
        return self
    
    def detect_anomalies(self, data):
        """Predict anomalous points."""
        X = data.reshape(-1, 1)
        predictions = self.model.predict(X)
        anomalies = predictions == -1
        return anomalies, None
    
    def save(self, path):
        """Save trained model."""
        joblib.dump(self.model, path)
    
    @classmethod
    def load(cls, path, contamination=0.01):
        """Load pre-trained model."""
        instance = cls(contamination=contamination)
        instance.model = joblib.load(path)
        return instance