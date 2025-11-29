# Gami Protocol - Agent Microservices

## Architecture

This repository contains four core components for the Gami Protocol Web3 loyalty and gamification ecosystem:

1. **Quest Generation Agent** (Port 8001) - RL-based personalized quest generation
2. **Economy Management Agent** (Port 8002) - Tokenomics and emission rate control
3. **Security Agent** (Port 8003) - Fraud detection and Sybil attack prevention
4. **Supervisor MCP Server** (Port 8800, SSE path `/mcp`) - Exposes the other agents as MCP tools (`generate_quest`, `optimize_economy`, `check_fraud_risk`) and continuously watches their health

## Data Models

All agents strictly adhere to these schemas:

### User Identity
```json
{
  "wallet_id": "0x...",
  "xp_balance": 1000,
  "reputation_score": 75.5
}
```

### MCP Event
```json
{
  "event_id": "uuid",
  "user_id": "wallet_id",
  "source": "web2|web3",
  "action_type": "string",
  "meta_data": {},
  "timestamp": "ISO8601"
}
```

### Quest
```json
{
  "quest_id": "uuid",
  "difficulty_rating": 7,
  "reward_xp": 700,
  "reward_gami": 3.5,
  "completion_criteria": {}
}
```

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL (relational), Redis (hot state)
- **ML**: scikit-learn, stable-baselines3
- **Communication**: MCP/REST

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis
docker run -d -p 5432:5432 -e POSTGRES_USER=gami -e POSTGRES_PASSWORD=gami -e POSTGRES_DB=gami_protocol postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Start Quest Generation Agent
cd quest_generation_agent
python main.py

# Start Economy Management Agent (new terminal)
cd economy_management_agent
python main.py

# Start Security Agent (new terminal)
cd security_agent
python main.py

# Start Supervisor MCP Server (new terminal)
cd ../supervisor_agent
python main.py
```

## API Endpoints

### Quest Generation Agent (8001)

- `POST /generate-quest` - Generate personalized quest
- `POST /feedback` - Submit retention feedback
- `GET /quest/{quest_id}` - Get quest details
- `GET /user/{wallet_id}/quests` - Get user quests
- `GET /health` - Health check

### Economy Management Agent (8002)

- `POST /run-simulation` - Run Monte Carlo inflation forecast
- `GET /get-current-emission-rate` - Get XP-to-GAMI rate
- `POST /convert-xp-to-gami` - Convert XP to GAMI
- `POST /forecast-scenarios` - Multi-scenario forecasting
- `GET /simulation-history` - Simulation history
- `GET /health` - Health check

### Security Agent (8003)

- `POST /ingest-events` - Ingest MCP events
- `POST /detect-anomaly/{user_id}` - Detect user anomaly
- `POST /train-model` - Train fraud detection model
- `POST /detect-sybil-cluster` - Detect Sybil attacks
- `GET /fraud-alerts` - Get fraud alerts
- `GET /user/{user_id}/status` - User security status
- `GET /health` - Health check

### Supervisor MCP Server (8800 / `mcp`)

- Transport: MCP over SSE (`http://localhost:8800/mcp` by default)
- Tools:
  - `generate_quest` – Calls the Quest Agent with a `UserProfile` payload and returns a schema-compliant `Quest`
  - `optimize_economy` – Runs Monte Carlo simulations via the Economy Agent to adjust XP→$GAMI emission rates
  - `check_fraud_risk` – Invokes the Security Agent’s anomaly detection for a specific wallet
- Background watchdog pings every agent’s `/health` endpoint every 60 seconds and logs state transitions so MCP clients get early warnings if a microservice is degraded.
- Configure alternate transports/hosts through `MCP_TRANSPORT`, `SUPERVISOR_HOST`, `SUPERVISOR_PORT`, and `SUPERVISOR_HTTP_PATH` environment variables.

## Example Usage

### Generate Quest

```bash
curl -X POST http://localhost:8001/generate-quest \
  -H "Content-Type: application/json" \
  -d '{
    "user_identity": {
      "wallet_id": "0x123",
      "xp_balance": 1000,
      "reputation_score": 45.0
    },
    "recent_events": [],
    "total_quests_completed": 5
  }'
```

### Run Economic Simulation

```bash
curl -X POST http://localhost:8002/run-simulation \
  -H "Content-Type: application/json" \
  -d '{
    "current_supply": 1000000,
    "adoption_rate": 5.0,
    "days": 30,
    "iterations": 1000
  }'
```

### Detect Fraud

```bash
curl -X POST http://localhost:8003/detect-sybil-cluster?lookback_hours=24
```

## Key Features

### Quest Generation Agent
- **Q-learning RL** for difficulty optimization
- **User clustering** with K-means
- **Churn prevention**: Auto-generates Easy quests for reputation < 20
- **Personalization** based on user behavior

### Economy Management Agent
- **Monte Carlo simulation** (1000 iterations)
- **Automatic deflation** when inflation > 5%
- **Dynamic emission rates** for $GAMI minting
- **Multi-scenario forecasting**

### Security Agent
- **Isolation Forest** anomaly detection
- **Sybil cluster detection** (3x XP threshold)
- **Auto-lock** malicious users
- **Circuit breaker** event publishing
- **Real-time monitoring** background task

## Database Schema

PostgreSQL tables auto-created on startup:
- `users` - User identity and status
- `mcp_events` - Event stream
- `quests` - Quest tracking
- `fraud_alerts` - Security alerts

## Environment Variables

```bash
DATABASE_URL=postgresql://gami:gami@localhost:5432/gami_protocol
REDIS_URL=redis://localhost:6379/0
```

## Monitoring

Health check all services:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Architecture Notes

- Microservices communicate via REST (MCP protocol support ready)
- Redis used for hot state (emission rates, circuit breaker events)
- PostgreSQL for persistent data
- Async event processing in Security Agent
- Q-table persistence for Quest Agent RL model

## License

MIT
