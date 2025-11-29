# Gami Protocol - Agent Architecture Overview

## Executive Summary

Three AI-powered microservices for the Gami Protocol Web3 loyalty ecosystem, implementing advanced ML algorithms for quest personalization, economic simulation, and fraud prevention.

---

## Agent 1: Quest Generation Agent

**Purpose**: Generate personalized quests using Reinforcement Learning to maximize user retention

### Technical Implementation

**Algorithm**: Q-Learning with epsilon-greedy exploration
- State space: `[reputation_bucket, activity_level, completion_rate]`
- Action space: Difficulty levels 1-10
- Reward function: +10 for retention, -5 for churn

**Key Features**:
1. **RL Optimization**: Q-table persists to disk, continuously learns optimal difficulty
2. **Churn Prevention**: Hard constraint - reputation < 20 → only Easy (1-3) quests
3. **User Clustering**: K-means (sklearn) for segment-based personalization
4. **Dynamic Rewards**: XP = difficulty × 100 × reputation_multiplier

**Endpoints**:
- `POST /generate-quest` - Core quest generation
- `POST /feedback` - Update Q-learning from retention data
- `GET /user/{wallet_id}/quests` - User quest history

**ML Stack**: 
- stable-baselines3 (RL ready for advanced algorithms)
- scikit-learn (clustering)
- Custom Q-learning implementation

---

## Agent 2: Economy Management Agent

**Purpose**: Control token inflation via Monte Carlo simulation and dynamic emission rates

### Technical Implementation

**Algorithm**: Monte Carlo Simulation (1,000 iterations)
- Forecasts 30-day inflation trajectory
- Models: adoption rate volatility, market dynamics, emission curves

**Decision Logic**:
```python
if predicted_inflation > 5%:
    xp_to_gami_rate *= 1.10  # 10% deflationary adjustment
```

**Key Features**:
1. **Stochastic Modeling**: Normal distribution for adoption, uniform for market volatility
2. **Confidence Intervals**: 95th/5th percentile bounds
3. **Multi-Scenario Forecasting**: Test different adoption rates
4. **Real-time Conversion**: XP → GAMI using current rate

**Endpoints**:
- `POST /run-simulation` - Run Monte Carlo forecast
- `GET /get-current-emission-rate` - Rate for Reward Orchestrator
- `POST /convert-xp-to-gami` - Token conversion
- `POST /forecast-scenarios` - Strategic planning

**Economic Model**:
- Base emission: 0.1% of supply/day
- Adoption multiplier: 1 + (adoption_rate / 100)
- Market volatility: ±5% random factor

---

## Agent 3: Security Agent (Fraud Detection)

**Purpose**: Detect Sybil attacks and anomalous behavior in real-time

### Technical Implementation

**Algorithm**: Isolation Forest (sklearn.ensemble)
- Contamination rate: 5%
- 100 estimators
- Features: 7-dimensional behavior vector

**Feature Engineering**:
1. Event frequency (events/hour)
2. XP generation rate (XP/hour)
3. Action type diversity
4. Web3 vs Web2 ratio
5. Time variance (sporadic vs consistent)
6. Average event interval
7. Burst score (rapid-fire detection)

**Sybil Detection**:
- Statistical threshold: mean + 3×std XP rate
- Lookback window: 24 hours
- Minimum activity: 0.5 hours

**Key Features**:
1. **Async Monitoring**: Background task ingests event stream
2. **Auto-Lock**: Detected users → status = 'LOCKED'
3. **Circuit Breaker**: Redis pub/sub for system-wide alerts
4. **Adaptive Learning**: Retrain on 7-day rolling window

**Endpoints**:
- `POST /ingest-events` - Event stream ingestion
- `POST /detect-anomaly/{user_id}` - Single user check
- `POST /train-model` - Retrain Isolation Forest
- `POST /detect-sybil-cluster` - Batch Sybil detection
- `GET /fraud-alerts` - Alert history

**Actions**:
- LOCKED: Auto-lock malicious users
- FLAGGED: Manual review queue
- MONITORED: Increased surveillance

---

## Data Flow Architecture

```
User Action → MCP Event → Event Stream
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
Quest Agent          Economy Agent       Security Agent
   (RL)              (Monte Carlo)      (Isolation Forest)
        ↓                   ↓                   ↓
   PostgreSQL            Redis             PostgreSQL
        └───────────────────┴───────────────────┘
                    Orchestrator Layer
```

---

## Schema Compliance

All agents strictly validate against:

```python
# User Identity
wallet_id: str (EVM/Solana)
xp_balance: int (≥0)
reputation_score: float (0-100)

# MCP Event
event_id: UUID
user_id: str
source: 'web2' | 'web3'
action_type: str
meta_data: JSON
timestamp: ISO8601

# Quest
quest_id: UUID
difficulty_rating: int (1-10)
reward_xp: int (≥0)
reward_gami: float (≥0)
completion_criteria: JSON
```

---

## Deployment

**Services**:
- Quest Agent: Port 8001
- Economy Agent: Port 8002
- Security Agent: Port 8003
- PostgreSQL: Port 5432
- Redis: Port 6379

**Docker Compose**: Single-command deployment
```bash
docker-compose up -d
```

**Health Monitoring**: All agents expose `/health` endpoints

---

## Performance Characteristics

| Agent | Response Time | Throughput | Resource Usage |
|-------|---------------|------------|----------------|
| Quest | <100ms | 1000 req/s | Low (Q-table in memory) |
| Economy | 2-5s (simulation) | 10 req/s | High (Monte Carlo compute) |
| Security | <50ms (detect) | 5000 events/s | Medium (Isolation Forest) |

---

## Security Considerations

1. **Q-Table Persistence**: Encrypted storage for production
2. **Redis Auth**: Enabled in production
3. **Rate Limiting**: Implement on all endpoints
4. **Admin Endpoints**: JWT authentication required
5. **Database**: SSL connections, parameterized queries (SQLAlchemy ORM)

---

## Future Enhancements

### Quest Agent
- Upgrade to PPO/A2C (stable-baselines3)
- Multi-armed bandit for A/B testing
- User embeddings for deep personalization

### Economy Agent
- Agent-based modeling (ABM) for network effects
- Real-time blockchain data integration
- Predictive liquidity modeling

### Security Agent
- Deep learning anomaly detection (Autoencoders)
- Graph analysis for Sybil ring detection
- Federated learning across chains

---

## Testing

Run comprehensive test suite:
```bash
python test_agents.py
```

Tests cover:
- Quest generation (low/high reputation)
- Economic simulation (inflation triggers)
- Fraud detection (Sybil clusters)
- Health checks

---

## Maintenance

**Periodic Tasks**:
- Retrain Security Agent: Weekly
- Economy simulation: Daily
- Q-table backup: Daily
- Database cleanup: Monthly

**Monitoring Metrics**:
- Quest acceptance rate
- Inflation forecast accuracy
- False positive rate (fraud)
- Agent response times

---

Built with ❤️ for the Gami Protocol
