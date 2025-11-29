"""
Database configuration and models for PostgreSQL and Redis
"""
import os
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import redis
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gami:gami@localhost:5432/gami_protocol")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class UserDB(Base):
    """User table in PostgreSQL"""
    __tablename__ = "users"
    
    wallet_id = Column(String, primary_key=True, index=True)
    xp_balance = Column(Integer, default=0, nullable=False)
    reputation_score = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MCPEventDB(Base):
    """MCP Event table"""
    __tablename__ = "mcp_events"
    
    event_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    source = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    meta_data = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class QuestDB(Base):
    """Quest table"""
    __tablename__ = "quests"
    
    quest_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    difficulty_rating = Column(Integer, nullable=False)
    reward_xp = Column(Integer, nullable=False)
    reward_gami = Column(Float, nullable=False)
    completion_criteria = Column(JSON, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class FraudAlertDB(Base):
    """Fraud alert table"""
    __tablename__ = "fraud_alerts"
    
    alert_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    action_taken = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
