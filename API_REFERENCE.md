# Gami Protocol - Complete API Reference

## 🎮 Quest Generation Agent (Port 8001)

### Core Endpoints

#### `POST /generate-quest`
Generate a personalized quest for a user based on their profile and history.

**Request Body:**
```json
{
  "user_identity": {
    "wallet_id": "0x123...",
    "xp_balance": 1000,
    "reputation_score": 45.5
  },
  "recent_events": [
    {
      "user_id": "0x123...",
      "source": "web3",
      "action_type": "stake_tokens",
      "meta_data": {"xp_earned": 100}
    }
  ],
  "total_quests_completed": 5,
  "average_completion_time": 3600.0
}
```

**Response:**
```json
{
  "quest_id": "uuid",
  "difficulty_rating": 6,
  "reward_xp": 600,
  "reward_gami": 3.0,
  "completion_criteria": {
    "actions_required": 30,
    "action_type": "stake_tokens",
    "time_limit_hours": 48
  }
}
```

**Constraint:** If `reputation_score < 20`, only generates Easy (difficulty 1-3) quests.

---

#### `POST /feedback`
Submit retention feedback to update Q-learning model.

**Request Body:**
```json
{
  "user_id": "0x123...",
  "quest_id": "uuid",
  "retained": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Feedback processed"
}
```

---

#### `GET /quest/{quest_id}`
Retrieve quest details by ID.

**Response:**
```json
{
  "quest_id": "uuid",
  "user_id": "0x123...",
  "difficulty_rating": 6,
  "reward_xp": 600,
  "reward_gami": 3.0,
  "completion_criteria": {...},
  "status": "ACTIVE"
}
```

---

#### `GET /user/{wallet_id}/quests`
Get all quests for a specific user.

**Response:**
```json
[
  {
    "quest_id": "uuid",
    "difficulty_rating": 6,
    "reward_xp": 600,
    "reward_gami": 3.0,
    "status": "ACTIVE",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "quest_generation_agent"
}
```

---

## 💰 Economy Management Agent (Port 8002)

### Core Endpoints

#### `POST /run-simulation`
Run Monte Carlo simulation to forecast inflation and adjust emission rates.

**Request Body:**
```json
{
  "current_supply": 1000000.0,
  "adoption_rate": 5.0,
  "days": 30,
  "iterations": 1000
}
```

**Response:**
```json
{
  "simulation_result": {
    "predicted_inflation": 4.75,
    "inflation_std": 0.82,
    "confidence_interval_95": 6.21,
    "confidence_interval_5": 3.42,
    "mean_final_supply": 1047500.0,
    "forecast_days": 30,
    "iterations": 1000,
    "avg_supply_path": [1000000, 1001500, ...]
  },
  "adjustment_decision": {
    "predicted_inflation": 4.75,
    "trigger_deflationary_protocol": false,
    "previous_rate": 1000.0,
    "new_rate": 1000.0,
    "adjustment_percentage": 0.0,
    "reason": "Inflation 4.75% within threshold"
  },
  "current_emission_rate": 1000.0
}
```

**Logic:** If `predicted_inflation > 5%`, triggers deflationary protocol (increases rate by 10%).

---

#### `GET /get-current-emission-rate`
Get current XP-to-GAMI conversion rate (called by Reward Orchestrator).

**Response:**
```json
{
  "xp_to_gami_rate": 1000.0,
  "description": "1 GAMI = 1000.0 XP",
  "inverse_rate": 0.001
}
```

---

#### `POST /convert-xp-to-gami`
Convert XP amount to GAMI tokens using current rate.

**Request Body:**
```json
{
  "xp_amount": 5000
}
```

**Response:**
```json
{
  "xp_amount": 5000,
  "gami_amount": 5.0,
  "conversion_rate": 1000.0,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

#### `POST /forecast-scenarios`
Run multiple scenarios with different adoption rates.

**Request Body:**
```json
{
  "current_supply": 1000000.0,
  "adoption_rates": [1.0, 3.0, 5.0, 10.0],
  "days_per_scenario": 30
}
```

**Response:**
```json
{
  "scenarios": {
    "adoption_1.0%": {
      "predicted_inflation": 2.1,
      "mean_final_supply": 1021000,
      "confidence_95": 2.8
    },
    "adoption_3.0%": {
      "predicted_inflation": 4.3,
      "mean_final_supply": 1043000,
      "confidence_95": 5.1
    }
  },
  "current_emission_rate": 1000.0
}
```

---

#### `GET /simulation-history`
Retrieve recent simulation history.

**Query Parameters:**
- `limit` (int, default=10): Number of simulations to retrieve

**Response:**
```json
{
  "history": [
    {
      "predicted_inflation": 4.75,
      "mean_final_supply": 1047500,
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `POST /manual-rate-adjustment`
Manual override for emission rate (admin only).

**Request Body:**
```json
{
  "new_rate": 1100.0
}
```

**Response:**
```json
{
  "status": "success",
  "old_rate": 1000.0,
  "new_rate": 1100.0,
  "change_percentage": 10.0
}
```

---

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "economy_management_agent",
  "current_rate": 1000.0
}
```

---

## 🔒 Security Agent (Port 8003)

### Core Endpoints

#### `POST /ingest-events`
Ingest MCP events for fraud detection analysis.

**Request Body:**
```json
[
  {
    "user_id": "0x123...",
    "source": "web3",
    "action_type": "complete_quest",
    "meta_data": {"xp_earned": 100},
    "timestamp": "2024-01-01T00:00:00Z"
  }
]
```

**Response:**
```json
{
  "status": "success",
  "events_ingested": 1,
  "buffer_size": 150
}
```

---

#### `POST /detect-anomaly/{user_id}`
Run anomaly detection for a specific user.

**Response:**
```json
{
  "user_id": "0x123...",
  "is_anomaly": true,
  "anomaly_score": 0.87,
  "reason": "High event frequency (120.5 events/hour); Excessive XP generation rate (15000 XP/hour)",
  "action_taken": "LOCKED",
  "events_analyzed": 100
}
```

**Actions:**
- If anomaly detected → User status set to "LOCKED"
- Circuit breaker event published to Redis

---

#### `POST /train-model`
Train Isolation Forest model on historical data.

**Response:**
```json
{
  "status": "success",
  "events_trained": 5000,
  "model_trained": true
}
```

**Training Window:** Last 7 days of events

---

#### `POST /detect-sybil-cluster`
Detect Sybil attack clusters (users generating XP 3× faster than std dev).

**Query Parameters:**
- `lookback_hours` (int, default=24): Time window for analysis

**Response:**
```json
{
  "suspicious_users": ["0xABC...", "0xDEF..."],
  "count": 2,
  "lookback_hours": 24,
  "events_analyzed": 10000
}
```

**Threshold:** XP rate > mean + 3×std

---

#### `GET /fraud-alerts`
Retrieve recent fraud alerts.

**Query Parameters:**
- `limit` (int, default=50): Number of alerts to retrieve

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "uuid",
      "user_id": "0x123...",
      "anomaly_score": 0.87,
      "reason": "Sybil cluster - excessive XP generation",
      "action_taken": "LOCKED",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /user/{user_id}/status`
Check user security status.

**Response:**
```json
{
  "user_id": "0x123...",
  "status": "LOCKED",
  "reputation_score": 15.5,
  "recent_alerts": 3,
  "last_alert": "2024-01-01T00:00:00Z"
}
```

**Status Values:**
- `ACTIVE` - Normal user
- `FLAGGED` - Under review
- `MONITORED` - Increased surveillance
- `LOCKED` - Blocked due to fraud

---

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "security_agent",
  "model_trained": true,
  "buffer_size": 150
}
```

---

## 🔗 Integration Examples

### Example 1: Generate Quest for New User

```bash
curl -X POST http://localhost:8001/generate-quest \
  -H "Content-Type: application/json" \
  -d '{
    "user_identity": {
      "wallet_id": "0xNEWUSER",
      "xp_balance": 0,
      "reputation_score": 10.0
    },
    "recent_events": [],
    "total_quests_completed": 0,
    "average_completion_time": 0.0
  }'
```

Expected: Easy quest (difficulty 1-3) due to low reputation.

---

### Example 2: Run Economic Simulation

```bash
curl -X POST http://localhost:8002/run-simulation \
  -H "Content-Type: application/json" \
  -d '{
    "current_supply": 1000000,
    "adoption_rate": 12.0,
    "days": 30,
    "iterations": 1000
  }'
```

Expected: High inflation → Deflationary protocol triggered.

---

### Example 3: Detect Sybil Attack

```bash
curl -X POST http://localhost:8003/detect-sybil-cluster?lookback_hours=24
```

Expected: List of suspicious users generating excessive XP.

---

## 📊 Swagger UI Documentation

All agents expose interactive API documentation via Swagger UI:

- Quest Agent: http://localhost:8001/docs
- Economy Agent: http://localhost:8002/docs
- Security Agent: http://localhost:8003/docs

**Features:**
- Interactive API testing
- Request/response schemas
- Parameter descriptions
- Try-it-out functionality

---

## 🔐 Authentication (Production)

**Recommended for Production:**

Add JWT authentication middleware:

```python
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    # Implement JWT verification
    pass

@app.post("/generate-quest", dependencies=[Depends(verify_token)])
async def generate_quest(...):
    ...
```

**Admin-only endpoints** (manual adjustments, training):
- `/manual-rate-adjustment`
- `/train-model`

Should require elevated permissions.

---

## 📈 Monitoring & Observability

### Health Check All Services

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Metrics to Monitor

**Quest Agent:**
- Quest acceptance rate
- Difficulty distribution
- Q-table convergence

**Economy Agent:**
- Inflation accuracy
- Deflation trigger frequency
- Conversion volume

**Security Agent:**
- False positive rate
- Alert volume
- Model accuracy

---

## 🚨 Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `400` - Bad request (validation error)
- `404` - Resource not found
- `500` - Internal server error

**Error Response Format:**
```json
{
  "detail": "Error message description"
}
```

---

## 📝 Rate Limiting (Recommended)

Implement rate limiting for production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/generate-quest")
@limiter.limit("100/minute")
async def generate_quest(...):
    ...
```

---

## 🔄 Webhook Support (Future)

For event-driven architecture, add webhooks:

```python
@app.post("/webhooks/quest-completed")
async def quest_completed_webhook(event: QuestCompletedEvent):
    # Trigger feedback update
    # Update user reputation
    pass
```

---

Built for Gami Protocol 🎮
