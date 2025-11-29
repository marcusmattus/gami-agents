"""
Quest Generation Engine with Reinforcement Learning
Uses Q-learning to optimize quest difficulty for user retention
"""
import numpy as np
import pickle
import os
from typing import Dict, List, Tuple
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json

from shared.schemas import UserProfile, Quest, MCPEvent


class QuestEngine:
    """
    Quest generation engine using Q-learning for difficulty optimization
    """
    
    def __init__(self, q_table_path: str = "q_table.pkl"):
        self.q_table_path = q_table_path
        self.q_table = self._load_q_table()
        self.scaler = StandardScaler()
        self.user_clusters = None
        
        # Q-learning parameters
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        
        # State space: [reputation_bucket, activity_level, quest_completion_rate]
        # Action space: difficulty levels 1-10
        self.actions = list(range(1, 11))
        
    def _load_q_table(self) -> Dict:
        """Load Q-table from disk or initialize new one"""
        if os.path.exists(self.q_table_path):
            with open(self.q_table_path, 'rb') as f:
                return pickle.load(f)
        return {}
    
    def _save_q_table(self):
        """Persist Q-table to disk"""
        with open(self.q_table_path, 'wb') as f:
            pickle.dump(self.q_table, f)
    
    def _get_state_key(self, user_profile: UserProfile) -> str:
        """
        Convert user profile to state representation
        Returns: "rep_bucket:activity_level:completion_rate"
        """
        reputation = user_profile.user_identity.reputation_score
        rep_bucket = int(reputation // 20)
        
        activity_level = len(user_profile.recent_events)
        activity_bucket = min(activity_level // 5, 4)
        
        completion_rate = 0
        if user_profile.total_quests_completed > 0:
            completion_rate = min(int((user_profile.total_quests_completed / 10) * 10), 10)
        
        return f"{rep_bucket}:{activity_bucket}:{completion_rate}"
    
    def _get_q_value(self, state: str, action: int) -> float:
        """Get Q-value for state-action pair"""
        return self.q_table.get((state, action), 0.0)
    
    def _update_q_value(self, state: str, action: int, reward: float, next_state: str):
        """Update Q-table using Q-learning algorithm"""
        current_q = self._get_q_value(state, action)
        
        max_next_q = max([self._get_q_value(next_state, a) for a in self.actions])
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[(state, action)] = new_q
        self._save_q_table()
    
    def predict_difficulty(self, user_profile: UserProfile) -> int:
        """
        Predict optimal difficulty using Q-learning with epsilon-greedy
        Constraint: If reputation < 20, return difficulty 1-3 (Easy)
        """
        if user_profile.user_identity.reputation_score < 20:
            return np.random.randint(1, 4)
        
        state = self._get_state_key(user_profile)
        
        if np.random.random() < self.epsilon:
            return np.random.choice(self.actions)
        
        q_values = {action: self._get_q_value(state, action) for action in self.actions}
        
        if all(v == 0.0 for v in q_values.values()):
            return self._fallback_difficulty(user_profile)
        
        return max(q_values, key=q_values.get)
    
    def _fallback_difficulty(self, user_profile: UserProfile) -> int:
        """Heuristic fallback when Q-table is cold"""
        rep = user_profile.user_identity.reputation_score
        
        if rep < 20:
            return 2
        elif rep < 40:
            return 4
        elif rep < 60:
            return 6
        elif rep < 80:
            return 8
        else:
            return 9
    
    def _calculate_rewards(self, difficulty: int, user_profile: UserProfile) -> Tuple[int, float]:
        """
        Calculate XP and GAMI rewards based on difficulty
        Formula: XP = difficulty * 100, GAMI = difficulty * 0.5
        """
        base_xp = difficulty * 100
        base_gami = difficulty * 0.5
        
        reputation_multiplier = 1 + (user_profile.user_identity.reputation_score / 100)
        
        reward_xp = int(base_xp * reputation_multiplier)
        reward_gami = round(base_gami * reputation_multiplier, 2)
        
        return reward_xp, reward_gami
    
    def _generate_completion_criteria(self, difficulty: int, user_profile: UserProfile) -> Dict:
        """
        Generate quest completion criteria based on difficulty and user behavior
        """
        recent_actions = [event.action_type for event in user_profile.recent_events[-10:]]
        most_common_action = max(set(recent_actions), key=recent_actions.count) if recent_actions else "generic_action"
        
        criteria_templates = {
            "easy": {
                "actions_required": difficulty * 3,
                "action_type": most_common_action,
                "time_limit_hours": 72,
                "min_transaction_value": 0
            },
            "medium": {
                "actions_required": difficulty * 5,
                "action_type": most_common_action,
                "time_limit_hours": 48,
                "min_transaction_value": 10,
                "chain_required": True
            },
            "hard": {
                "actions_required": difficulty * 7,
                "action_type": most_common_action,
                "time_limit_hours": 24,
                "min_transaction_value": 50,
                "chain_required": True,
                "streak_required": difficulty
            }
        }
        
        if difficulty <= 3:
            return criteria_templates["easy"]
        elif difficulty <= 6:
            return criteria_templates["medium"]
        else:
            return criteria_templates["hard"]
    
    def generate_quest(self, user_profile: UserProfile) -> Quest:
        """
        Main method: Generate personalized quest for user
        """
        difficulty = self.predict_difficulty(user_profile)
        
        reward_xp, reward_gami = self._calculate_rewards(difficulty, user_profile)
        
        completion_criteria = self._generate_completion_criteria(difficulty, user_profile)
        
        quest = Quest(
            difficulty_rating=difficulty,
            reward_xp=reward_xp,
            reward_gami=reward_gami,
            completion_criteria=completion_criteria
        )
        
        return quest
    
    def update_from_feedback(self, user_id: str, state: str, action: int, retained: bool):
        """
        Update Q-table based on user retention feedback
        Called by reward orchestrator after tracking user behavior
        """
        reward = 10.0 if retained else -5.0
        
        next_state = state
        self._update_q_value(state, action, reward, next_state)
    
    def cluster_users(self, user_profiles: List[UserProfile], n_clusters: int = 5) -> np.ndarray:
        """
        Cluster users using K-means for personalization
        Features: reputation, xp_balance, activity_level, completion_rate
        """
        features = []
        for profile in user_profiles:
            features.append([
                profile.user_identity.reputation_score,
                profile.user_identity.xp_balance,
                len(profile.recent_events),
                profile.total_quests_completed
            ])
        
        X = np.array(features)
        X_scaled = self.scaler.fit_transform(X)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        self.user_clusters = kmeans
        return clusters
