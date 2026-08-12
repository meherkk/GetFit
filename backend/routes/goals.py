from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db

router = APIRouter()

@router.post("/goals/{user_id}")
def generate_goal(user_id: str, db: Session = Depends(get_db)):
    # Fetch user profile
    profile = db.execute(
        text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Placeholder logic — will be replaced with XGBoost model later
    goal_map = {
        "lose_fat": {
            "sessions_per_week": 4,
            "session_length_min": 45,
            "focus_area": "Cardio + Full Body",
            "description": "Focus on calorie burn with cardio and compound movements."
        },
        "build_muscle": {
            "sessions_per_week": 4,
            "session_length_min": 60,
            "focus_area": "Strength Training",
            "description": "Progressive overload with compound lifts. Prioritize recovery."
        },
        "endurance": {
            "sessions_per_week": 5,
            "session_length_min": 45,
            "focus_area": "Cardio + Core",
            "description": "Build aerobic base with steady state and interval cardio."
        },
        "general_fitness": {
            "sessions_per_week": 3,
            "session_length_min": 45,
            "focus_area": "Full Body",
            "description": "Balanced mix of strength and cardio for overall fitness."
        }
    }

    plan = goal_map.get(profile.goal, goal_map["general_fitness"])

    # Save to database
    db.execute(
        text("""
            INSERT INTO weekly_goals 
            (user_id, week_start, sessions_per_week, session_length_min, focus_area, description)
            VALUES (:user_id, CURRENT_DATE, :sessions_per_week, :session_length_min, :focus_area, :description)
        """),
        {"user_id": user_id, **plan}
    )
    db.commit()

    return plan