"""
Supervisor Agent - MCP Server
Bridges Quest, Economy, and Security agents via Model Context Protocol tools.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

# Ensure shared modules are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas import Quest, UserProfile  # noqa: E402

MASTER_CONTEXT = """
You are the Supervisor Agent for the Gami Protocol, a Web3 loyalty and gamification
network built on multi-chain progression (MCP). The protocol operates under these
schema and architectural constraints, which MUST be preserved in every downstream
operation:

Data Models:
- User Identity: { wallet_id: string (EVM/Solana), xp_balance: integer >= 0 (non-transferable),
  reputation_score: float 0-100 }
- Tokens: $GAMI (ERC-20, fixed supply) and XP (soul-bound token, infinite supply)
- MCP Event: { event_id: UUID, user_id: string, source: 'web2'|'web3', action_type: string,
  meta_data: JSON, timestamp: ISO8601 }
- Quest: { quest_id: UUID, difficulty_rating: 1-10, reward_xp: int, reward_gami: float,
  completion_criteria: rule_set JSON }

Architecture:
- Independent FastAPI microservices per agent (Quest Generation, Economy Management, Security)
- Services communicate via REST, orchestrated here through the Model Context Protocol (MCP)
- Datastores: PostgreSQL (relational state) and Redis (hot state / circuit breaker events)
- Language runtime: Python 3.11+, FastAPI + scikit-learn/stable-baselines3 where applicable

This Supervisor Agent exposes the lower-level agents as MCP tools and provides
resiliency policies (health checks, retries, guardrails) so that higher-level
LLMs can safely compose workflows without violating the canonical schemas.
"""

LOG_LEVEL = os.getenv("SUPERVISOR_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gami.supervisor")

QUEST_AGENT_URL = os.getenv("QUEST_AGENT_URL", "http://localhost:8001")
ECONOMY_AGENT_URL = os.getenv("ECONOMY_AGENT_URL", "http://localhost:8002")
SECURITY_AGENT_URL = os.getenv("SECURITY_AGENT_URL", "http://localhost:8003")
HEALTH_CHECK_INTERVAL = int(os.getenv("SUPERVISOR_HEALTH_INTERVAL", "60"))
REQUEST_TIMEOUT = float(os.getenv("SUPERVISOR_REQUEST_TIMEOUT", "20"))

HTTP_CLIENT: Optional[httpx.AsyncClient] = None
health_task: Optional[asyncio.Task] = None


class EconomySimulationInput(BaseModel):
    """Input payload for economy optimization tool."""

    current_supply: float = Field(..., gt=0, description="$GAMI circulating supply")
    adoption_rate: float = Field(
        ..., ge=0, le=100, description="Daily adoption rate percentage"
    )
    days: int = Field(default=30, ge=1, le=365, description="Forecast horizon in days")
    iterations: int = Field(
        default=1000, ge=100, le=10000, description="Monte Carlo iterations"
    )


@dataclass(slots=True)
class MicroserviceClient:
    """Lightweight HTTP client wrapper for downstream services."""

    name: str
    base_url: str
    health_endpoint: str = "/health"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    async def get(self, path: str, **kwargs) -> Any:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Any:
        return await self._request("POST", path, **kwargs)

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        client = get_http_client()
        url = f"{self.base_url}{path}"
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise RuntimeError(
                f"{self.name} responded with {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"{self.name} unreachable at {url}: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text


quest_agent = MicroserviceClient("quest_generation_agent", QUEST_AGENT_URL)
economy_agent = MicroserviceClient("economy_management_agent", ECONOMY_AGENT_URL)
security_agent = MicroserviceClient("security_agent", SECURITY_AGENT_URL)
AGENT_CLIENTS: List[MicroserviceClient] = [quest_agent, economy_agent, security_agent]

service_health: Dict[str, Dict[str, Any]] = {
    client.name: {
        "status": "unknown",
        "last_checked": None,
        "latency_ms": None,
        "details": None,
        "error": None,
    }
    for client in AGENT_CLIENTS
}


def build_http_client() -> httpx.AsyncClient:
    """Instantiate shared HTTP client with sane defaults."""
    timeout = httpx.Timeout(
        connect=5.0,
        read=REQUEST_TIMEOUT,
        write=REQUEST_TIMEOUT,
        pool=REQUEST_TIMEOUT,
    )
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    return httpx.AsyncClient(timeout=timeout, limits=limits)


def get_http_client() -> httpx.AsyncClient:
    if HTTP_CLIENT is None:
        raise RuntimeError("HTTP client not initialized")
    return HTTP_CLIENT


async def update_health(client: MicroserviceClient) -> None:
    """Ping a downstream agent and record the latest health snapshot."""
    start = time.perf_counter()
    try:
        data = await client.get(client.health_endpoint)
        latency = round((time.perf_counter() - start) * 1000, 2)
        new_status = {
            "status": "healthy",
            "last_checked": datetime.utcnow().isoformat(),
            "latency_ms": latency,
            "details": data,
            "error": None,
        }
    except Exception as exc:
        latency = round((time.perf_counter() - start) * 1000, 2)
        new_status = {
            "status": "unreachable",
            "last_checked": datetime.utcnow().isoformat(),
            "latency_ms": latency,
            "details": None,
            "error": str(exc),
        }

    previous_status = service_health.get(client.name, {}).get("status")
    service_health[client.name] = new_status

    if previous_status != new_status["status"]:
        level = logging.INFO if new_status["status"] == "healthy" else logging.WARNING
        logger.log(
            level,
            "Health status for %s changed to %s",
            client.name,
            new_status["status"],
        )


async def health_monitor_loop() -> None:
    """Continuously poll downstream health endpoints."""
    logger.info(
        "Starting health monitor (interval=%ss) for %s agents",
        HEALTH_CHECK_INTERVAL,
        len(AGENT_CLIENTS),
    )
    try:
        while True:
            for client in AGENT_CLIENTS:
                await update_health(client)
            await asyncio.sleep(max(1, HEALTH_CHECK_INTERVAL))
    except asyncio.CancelledError:
        logger.info("Health monitor stopped")
        raise


async def start_health_monitor() -> None:
    global health_task
    if health_task is None or health_task.done():
        health_task = asyncio.create_task(health_monitor_loop())


async def stop_health_monitor() -> None:
    if health_task is not None:
        health_task.cancel()
        with suppress(asyncio.CancelledError):
            await health_task


server = FastMCP(
    "gami_supervisor",
    instructions=MASTER_CONTEXT,
    version="1.0.0",
)


@server.tool(
    name="generate_quest",
    description="Request a personalized quest from the Quest Generation Agent",
    tags={"quest", "engagement"},
)
async def tool_generate_quest(
    user_profile: UserProfile, context: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate a quest tailored to the provided user profile."""
    payload = user_profile.model_dump(mode="json")
    if context:
        await context.log(
            f"Generating quest for wallet {user_profile.user_identity.wallet_id}",
            level="info",
        )
    response = await quest_agent.post("/generate-quest", json=payload)
    quest = Quest(**response)
    return quest.model_dump(mode="json")


@server.tool(
    name="check_fraud_risk",
    description="Run Isolation Forest anomaly detection via the Security Agent",
    tags={"security", "fraud"},
)
async def tool_check_fraud_risk(
    user_id: str, context: Optional[Context] = None
) -> Dict[str, Any]:
    """Check whether a user is exhibiting Sybil/anomalous behavior."""
    if not user_id:
        raise ValueError("user_id is required")
    if context:
        await context.log(f"Evaluating fraud risk for {user_id}", level="info")
    return await security_agent.post(f"/detect-anomaly/{user_id}", json={})


@server.tool(
    name="optimize_economy",
    description="Run the Monte Carlo simulator to adjust XP→$GAMI emission rates",
    tags={"economy", "tokenomics"},
)
async def tool_optimize_economy(
    simulation: EconomySimulationInput, context: Optional[Context] = None
) -> Dict[str, Any]:
    """Invoke the Economy Agent to simulate inflation and return emission decisions."""
    payload = simulation.model_dump(mode="json")
    if context:
        await context.log(
            "Running economy optimization", level="info", extra=payload
        )
    return await economy_agent.post("/run-simulation", json=payload)


async def run_server() -> None:
    """Bootstrap HTTP client, health monitor, and MCP transport."""
    global HTTP_CLIENT
    if HTTP_CLIENT is None:
        HTTP_CLIENT = build_http_client()

    await start_health_monitor()

    transport = os.getenv("MCP_TRANSPORT", "sse")
    transport_kwargs: Dict[str, Any] = {}
    if transport in {"http", "sse", "streamable-http"}:
        transport_kwargs = {
            "host": os.getenv("SUPERVISOR_HOST", "0.0.0.0"),
            "port": int(os.getenv("SUPERVISOR_PORT", "8800")),
            "path": os.getenv("SUPERVISOR_HTTP_PATH", "mcp"),
        }

    try:
        await server.run_async(transport=transport, **transport_kwargs)
    finally:
        await stop_health_monitor()
        if HTTP_CLIENT is not None:
            await HTTP_CLIENT.aclose()
            logger.info("HTTP client closed")
        logger.info("Supervisor Agent shut down")


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Supervisor Agent interrupted by user")
