"""
Shared data models for Gami Protocol
Strictly adheres to the defined schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Literal, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4


class UserIdentity(BaseModel):
    """User Identity Model"""
    wallet_id: str = Field(..., description="EVM/Solana address")
    xp_balance: int = Field(default=0, ge=0, description="Non-transferable XP")
    reputation_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Reputation 0-100")


class MCPEvent(BaseModel):
    """Model Context Protocol Event"""
    event_id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(..., description="Wallet ID")
    source: Literal['web2', 'web3'] = Field(...)
    action_type: str = Field(..., description="Type of action performed")
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class Quest(BaseModel):
    """Quest Model"""
    quest_id: UUID = Field(default_factory=uuid4)
    difficulty_rating: int = Field(..., ge=1, le=10, description="Difficulty 1-10")
    reward_xp: int = Field(..., ge=0, description="XP reward")
    reward_gami: float = Field(..., ge=0.0, description="GAMI token reward")
    completion_criteria: Dict[str, Any] = Field(..., description="Rule set for completion")
    
    @validator('difficulty_rating')
    def validate_difficulty(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Difficulty must be between 1 and 10')
        return v


class UserProfile(BaseModel):
    """Extended User Profile with history"""
    user_identity: UserIdentity
    recent_events: List[MCPEvent] = Field(default_factory=list)
    total_quests_completed: int = Field(default=0, ge=0)
    average_completion_time: float = Field(default=0.0, ge=0.0)


class TokenomicsState(BaseModel):
    """Current tokenomics state"""
    current_gami_supply: float
    current_xp_supply: int
    xp_to_gami_rate: float
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class FraudAlert(BaseModel):
    """Fraud detection alert"""
    alert_id: UUID = Field(default_factory=uuid4)
    user_id: str
    anomaly_score: float
    reason: str
    action_taken: Literal['LOCKED', 'FLAGGED', 'MONITORED']
    timestamp: datetime = Field(default_factory=datetime.utcnow)
