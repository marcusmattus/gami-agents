"""
Quest Generation Agent - FastAPI Microservice
Generates personalized quests using RL-based difficulty optimization
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas import UserProfile, Quest, MCPEvent, UserIdentity
from shared.database import get_db, init_db, UserDB, QuestDB, MCPEventDB
from quest_engine import QuestEngine

app = FastAPI(
    title="Quest Generation Agent",
    description="Gami Protocol Quest Generation Service with RL optimization",
    version="1.0.0"
)

quest_engine = QuestEngine()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Quest Generation Agent initialized")


@app.post("/generate-quest", response_model=Quest)
async def generate_quest(
    user_profile: UserProfile,
    db: Session = Depends(get_db)
):
    """
    Generate a personalized quest for a user
    
    Input: UserProfile with user identity and recent MCP events
    Output: Quest object with difficulty, rewards, and completion criteria
    
    Constraint: If reputation < 20, only generate Easy (1-3) difficulty quests
    """
    try:
        quest = quest_engine.generate_quest(user_profile)
        
        quest_db = QuestDB(
            quest_id=str(quest.quest_id),
            user_id=user_profile.user_identity.wallet_id,
            difficulty_rating=quest.difficulty_rating,
            reward_xp=quest.reward_xp,
            reward_gami=quest.reward_gami,
            completion_criteria=quest.completion_criteria,
            status="ACTIVE"
        )
        db.add(quest_db)
        db.commit()
        
        return quest
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quest generation failed: {str(e)}")


@app.post("/feedback")
async def submit_feedback(
    user_id: str,
    quest_id: str,
    retained: bool,
    db: Session = Depends(get_db)
):
    """
    Submit retention feedback to update Q-learning model
    Called by orchestrator to improve quest recommendations
    """
    try:
        quest = db.query(QuestDB).filter(QuestDB.quest_id == quest_id).first()
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        user = db.query(UserDB).filter(UserDB.wallet_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        rep_bucket = int(user.reputation_score // 20)
        events_count = db.query(MCPEventDB).filter(MCPEventDB.user_id == user_id).count()
        activity_bucket = min(events_count // 5, 4)
        
        quests_completed = db.query(QuestDB).filter(
            QuestDB.user_id == user_id,
            QuestDB.status == "COMPLETED"
        ).count()
        completion_rate = min(int((quests_completed / 10) * 10), 10) if quests_completed else 0
        
        state = f"{rep_bucket}:{activity_bucket}:{completion_rate}"
        
        quest_engine.update_from_feedback(
            user_id=user_id,
            state=state,
            action=quest.difficulty_rating,
            retained=retained
        )
        
        return {"status": "success", "message": "Feedback processed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {str(e)}")


@app.get("/quest/{quest_id}", response_model=dict)
async def get_quest(quest_id: str, db: Session = Depends(get_db)):
    """Retrieve quest by ID"""
    quest = db.query(QuestDB).filter(QuestDB.quest_id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    return {
        "quest_id": quest.quest_id,
        "user_id": quest.user_id,
        "difficulty_rating": quest.difficulty_rating,
        "reward_xp": quest.reward_xp,
        "reward_gami": quest.reward_gami,
        "completion_criteria": quest.completion_criteria,
        "status": quest.status
    }


@app.get("/user/{wallet_id}/quests")
async def get_user_quests(wallet_id: str, db: Session = Depends(get_db)):
    """Get all quests for a user"""
    quests = db.query(QuestDB).filter(QuestDB.user_id == wallet_id).all()
    
    return [
        {
            "quest_id": q.quest_id,
            "difficulty_rating": q.difficulty_rating,
            "reward_xp": q.reward_xp,
            "reward_gami": q.reward_gami,
            "status": q.status,
            "created_at": q.created_at.isoformat()
        }
        for q in quests
    ]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "quest_generation_agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
