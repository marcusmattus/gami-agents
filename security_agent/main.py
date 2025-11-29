"""
Security Agent - FastAPI Microservice
Fraud detection and Sybil attack prevention
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas import MCPEvent, FraudAlert
from shared.database import get_db, init_db, UserDB, MCPEventDB, FraudAlertDB, redis_client
from fraud_detector import FraudDetector

app = FastAPI(
    title="Security Agent",
    description="Gami Protocol Fraud Detection Service",
    version="1.0.0"
)

fraud_detector = FraudDetector(
    contamination=0.05,
    xp_multiplier_threshold=3.0
)

event_stream_buffer: List[MCPEvent] = []


@app.on_event("startup")
async def startup_event():
    """Initialize security agent on startup"""
    init_db()
    
    asyncio.create_task(event_monitoring_loop())
    
    print("Security Agent initialized - Fraud detection active")


async def event_monitoring_loop():
    """
    Background task that continuously monitors event stream
    Simulates consuming MCP events from a message queue
    """
    while True:
        try:
            await asyncio.sleep(10)
            
            if len(event_stream_buffer) > 100:
                await process_event_batch(event_stream_buffer.copy())
                event_stream_buffer.clear()
                
        except Exception as e:
            print(f"Event monitoring error: {e}")


async def process_event_batch(events: List[MCPEvent]):
    """Process batch of events for fraud detection"""
    if not fraud_detector.is_trained and len(events) >= 50:
        fraud_detector.train_model(events)
    
    suspicious_users = fraud_detector.detect_sybil_cluster(events, lookback_hours=24)
    
    if suspicious_users:
        print(f"⚠️  Detected {len(suspicious_users)} suspicious users in Sybil cluster")
        for user_id in suspicious_users:
            await handle_fraud_detection(user_id, events, "Sybil cluster detected")


async def handle_fraud_detection(user_id: str, events: List[MCPEvent], reason: str):
    """
    Handle detected fraud - lock user and fire circuit breaker event
    """
    try:
        db = next(get_db())
        
        user = db.query(UserDB).filter(UserDB.wallet_id == user_id).first()
        if user and user.status != "LOCKED":
            user.status = "LOCKED"
            db.commit()
            
            fraud_alert = FraudAlert(
                user_id=user_id,
                anomaly_score=99.0,
                reason=reason,
                action_taken="LOCKED"
            )
            
            alert_db = FraudAlertDB(
                alert_id=str(fraud_alert.alert_id),
                user_id=fraud_alert.user_id,
                anomaly_score=fraud_alert.anomaly_score,
                reason=fraud_alert.reason,
                action_taken=fraud_alert.action_taken
            )
            db.add(alert_db)
            db.commit()
            
            try:
                redis_client.publish(
                    "circuit_breaker",
                    f"FRAUD_DETECTED:{user_id}:{reason}"
                )
            except Exception as e:
                print(f"Redis publish warning: {e}")
            
            print(f"🔒 User {user_id} LOCKED - {reason}")
        
        db.close()
        
    except Exception as e:
        print(f"Fraud handling error: {e}")


@app.post("/ingest-events")
async def ingest_events(events: List[MCPEvent], db: Session = Depends(get_db)):
    """
    Ingest MCP events for fraud detection
    Events are added to buffer and processed asynchronously
    """
    try:
        event_stream_buffer.extend(events)
        
        for event in events:
            event_db = MCPEventDB(
                event_id=str(event.event_id),
                user_id=event.user_id,
                source=event.source,
                action_type=event.action_type,
                meta_data=event.meta_data,
                timestamp=event.timestamp
            )
            db.add(event_db)
        
        db.commit()
        
        return {
            "status": "success",
            "events_ingested": len(events),
            "buffer_size": len(event_stream_buffer)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event ingestion failed: {str(e)}")


@app.post("/detect-anomaly/{user_id}")
async def detect_anomaly(user_id: str, db: Session = Depends(get_db)):
    """
    Run anomaly detection for specific user
    Returns anomaly score and detection result
    """
    try:
        db_events = db.query(MCPEventDB).filter(
            MCPEventDB.user_id == user_id
        ).order_by(MCPEventDB.timestamp.desc()).limit(100).all()
        
        events = [
            MCPEvent(
                event_id=e.event_id,
                user_id=e.user_id,
                source=e.source,
                action_type=e.action_type,
                meta_data=e.meta_data,
                timestamp=e.timestamp
            )
            for e in db_events
        ]
        
        is_anomaly, anomaly_score, reason = fraud_detector.detect_anomaly(events, user_id)
        
        if is_anomaly:
            await handle_fraud_detection(user_id, events, reason)
        
        return {
            "user_id": user_id,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "reason": reason,
            "action_taken": "LOCKED" if is_anomaly else "NONE",
            "events_analyzed": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@app.post("/train-model")
async def train_model(db: Session = Depends(get_db)):
    """
    Train fraud detection model on historical data
    Should be called periodically
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        db_events = db.query(MCPEventDB).filter(
            MCPEventDB.timestamp >= cutoff_time
        ).all()
        
        events = [
            MCPEvent(
                event_id=e.event_id,
                user_id=e.user_id,
                source=e.source,
                action_type=e.action_type,
                meta_data=e.meta_data,
                timestamp=e.timestamp
            )
            for e in db_events
        ]
        
        fraud_detector.train_model(events)
        
        return {
            "status": "success",
            "events_trained": len(events),
            "model_trained": fraud_detector.is_trained
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")


@app.post("/detect-sybil-cluster")
async def detect_sybil_cluster(
    lookback_hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Detect Sybil attack clusters
    Identifies users generating XP 3x faster than standard deviation
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        db_events = db.query(MCPEventDB).filter(
            MCPEventDB.timestamp >= cutoff_time
        ).all()
        
        events = [
            MCPEvent(
                event_id=e.event_id,
                user_id=e.user_id,
                source=e.source,
                action_type=e.action_type,
                meta_data=e.meta_data,
                timestamp=e.timestamp
            )
            for e in db_events
        ]
        
        suspicious_users = fraud_detector.detect_sybil_cluster(events, lookback_hours)
        
        for user_id in suspicious_users:
            await handle_fraud_detection(user_id, events, "Sybil cluster - excessive XP generation")
        
        return {
            "suspicious_users": suspicious_users,
            "count": len(suspicious_users),
            "lookback_hours": lookback_hours,
            "events_analyzed": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sybil detection failed: {str(e)}")


@app.get("/fraud-alerts")
async def get_fraud_alerts(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve recent fraud alerts"""
    try:
        alerts = db.query(FraudAlertDB).order_by(
            FraudAlertDB.timestamp.desc()
        ).limit(limit).all()
        
        return {
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "user_id": a.user_id,
                    "anomaly_score": a.anomaly_score,
                    "reason": a.reason,
                    "action_taken": a.action_taken,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in alerts
            ],
            "count": len(alerts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert retrieval failed: {str(e)}")


@app.get("/user/{user_id}/status")
async def get_user_status(user_id: str, db: Session = Depends(get_db)):
    """Check user security status"""
    try:
        user = db.query(UserDB).filter(UserDB.wallet_id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        alerts = db.query(FraudAlertDB).filter(
            FraudAlertDB.user_id == user_id
        ).order_by(FraudAlertDB.timestamp.desc()).limit(10).all()
        
        return {
            "user_id": user_id,
            "status": user.status,
            "reputation_score": user.reputation_score,
            "recent_alerts": len(alerts),
            "last_alert": alerts[0].timestamp.isoformat() if alerts else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "security_agent",
        "model_trained": fraud_detector.is_trained,
        "buffer_size": len(event_stream_buffer)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
