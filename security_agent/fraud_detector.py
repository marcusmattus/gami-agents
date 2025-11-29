"""
Security Agent - Fraud Detection Engine
Detects Sybil attacks and anomalies using Isolation Forest
"""
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas import MCPEvent, FraudAlert


class FraudDetector:
    """
    Fraud detection using Isolation Forest
    Detects Sybil clusters and anomalous behavior patterns
    """
    
    def __init__(
        self,
        contamination: float = 0.05,
        xp_multiplier_threshold: float = 3.0
    ):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.xp_multiplier_threshold = xp_multiplier_threshold
        self.user_profiles = {}
        self.is_trained = False
        
    def extract_features(self, events: List[MCPEvent], user_id: str) -> np.ndarray:
        """
        Extract features from event stream for anomaly detection
        
        Features:
        - Event frequency (events per hour)
        - XP generation rate
        - Action type diversity
        - Source distribution (web2 vs web3)
        - Time variance (consistent vs sporadic)
        """
        if not events:
            return np.zeros(7)
        
        user_events = [e for e in events if e.user_id == user_id]
        
        if not user_events:
            return np.zeros(7)
        
        time_span = (max(e.timestamp for e in user_events) - 
                     min(e.timestamp for e in user_events)).total_seconds()
        time_span_hours = max(time_span / 3600, 0.1)
        
        event_frequency = len(user_events) / time_span_hours
        
        total_xp = sum(e.meta_data.get('xp_earned', 0) for e in user_events)
        xp_rate = total_xp / time_span_hours
        
        action_types = set(e.action_type for e in user_events)
        action_diversity = len(action_types)
        
        web2_count = sum(1 for e in user_events if e.source == 'web2')
        web3_count = len(user_events) - web2_count
        web3_ratio = web3_count / len(user_events)
        
        timestamps = [e.timestamp.timestamp() for e in user_events]
        time_variance = np.var(np.diff(timestamps)) if len(timestamps) > 1 else 0
        
        avg_event_interval = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else 0
        
        event_burst_score = sum(
            1 for i in range(len(timestamps) - 1)
            if timestamps[i+1] - timestamps[i] < 10
        ) / max(len(timestamps) - 1, 1)
        
        features = np.array([
            event_frequency,
            xp_rate,
            action_diversity,
            web3_ratio,
            time_variance,
            avg_event_interval,
            event_burst_score
        ])
        
        return features
    
    def train_model(self, all_events: List[MCPEvent]):
        """
        Train Isolation Forest on event data
        Should be called periodically with historical data
        """
        user_ids = list(set(e.user_id for e in all_events))
        
        features_list = []
        for user_id in user_ids:
            features = self.extract_features(all_events, user_id)
            features_list.append(features)
        
        if len(features_list) < 10:
            print("Warning: Not enough data to train model effectively")
            return
        
        X = np.array(features_list)
        X_scaled = self.scaler.fit_transform(X)
        
        self.model.fit(X_scaled)
        self.is_trained = True
        
        print(f"Fraud detector trained on {len(user_ids)} users")
    
    def detect_anomaly(
        self,
        events: List[MCPEvent],
        user_id: str
    ) -> Tuple[bool, float, str]:
        """
        Detect if user exhibits anomalous behavior
        
        Returns:
            Tuple[is_anomaly: bool, anomaly_score: float, reason: str]
        """
        if not self.is_trained:
            return False, 0.0, "Model not trained"
        
        features = self.extract_features(events, user_id)
        
        if np.all(features == 0):
            return False, 0.0, "Insufficient data"
        
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = -self.model.score_samples(features_scaled)[0]
        
        is_anomaly = prediction == -1
        
        reason = self._generate_reason(features, is_anomaly)
        
        return is_anomaly, float(anomaly_score), reason
    
    def detect_sybil_cluster(
        self,
        all_events: List[MCPEvent],
        lookback_hours: int = 24
    ) -> List[str]:
        """
        Detect Sybil attack clusters
        Identifies users generating XP 3x faster than standard deviation
        
        Returns:
            List of suspicious user IDs
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent_events = [e for e in all_events if e.timestamp >= cutoff_time]
        
        user_xp_rates = defaultdict(float)
        user_time_spans = defaultdict(float)
        
        for user_id in set(e.user_id for e in recent_events):
            user_events = [e for e in recent_events if e.user_id == user_id]
            
            if len(user_events) < 2:
                continue
            
            total_xp = sum(e.meta_data.get('xp_earned', 0) for e in user_events)
            
            time_span = (max(e.timestamp for e in user_events) - 
                        min(e.timestamp for e in user_events)).total_seconds()
            time_span_hours = max(time_span / 3600, 0.1)
            
            user_xp_rates[user_id] = total_xp / time_span_hours
            user_time_spans[user_id] = time_span_hours
        
        if not user_xp_rates:
            return []
        
        xp_rates = list(user_xp_rates.values())
        mean_rate = np.mean(xp_rates)
        std_rate = np.std(xp_rates)
        
        threshold = mean_rate + (self.xp_multiplier_threshold * std_rate)
        
        suspicious_users = [
            user_id for user_id, rate in user_xp_rates.items()
            if rate > threshold and user_time_spans[user_id] > 0.5
        ]
        
        return suspicious_users
    
    def _generate_reason(self, features: np.ndarray, is_anomaly: bool) -> str:
        """Generate human-readable reason for anomaly detection"""
        if not is_anomaly:
            return "Normal behavior"
        
        reasons = []
        
        event_frequency, xp_rate, action_diversity, web3_ratio, \
            time_variance, avg_interval, burst_score = features
        
        if event_frequency > 100:
            reasons.append(f"High event frequency ({event_frequency:.1f} events/hour)")
        
        if xp_rate > 10000:
            reasons.append(f"Excessive XP generation rate ({xp_rate:.0f} XP/hour)")
        
        if action_diversity < 2:
            reasons.append("Low action diversity (potential bot)")
        
        if burst_score > 0.5:
            reasons.append(f"Suspicious event bursts ({burst_score:.1%})")
        
        if avg_interval < 5:
            reasons.append(f"Unnaturally consistent timing ({avg_interval:.1f}s intervals)")
        
        if not reasons:
            reasons.append("Statistical anomaly detected")
        
        return "; ".join(reasons)
    
    def create_fraud_alert(
        self,
        user_id: str,
        anomaly_score: float,
        reason: str,
        action: str = "LOCKED"
    ) -> FraudAlert:
        """Create fraud alert object"""
        return FraudAlert(
            user_id=user_id,
            anomaly_score=anomaly_score,
            reason=reason,
            action_taken=action
        )
