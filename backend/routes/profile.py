from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from db.database import get_db
from typing import Optional
from enum import Enum

router = APIRouter()

class GoalEnum(str, Enum):
    lose_fat = "lose_fat"
    build_muscle = "build_muscle"
    endurance = "endurance"
    general = "general_fitness"

class ActivityEnum(str, Enum):
    sedentary = "sedentary"
    light = "lightly_active"
    moderate = "moderately_active"
    active = "very_active"

class DaysEnum(str, Enum):
    low = "1-2 days"
    medium = "3-4 days"
    high = "5-6 days"
    every_day = "7 days"

class ProfileRequest(BaseModel):
    user_id: str
    age: int
    sex: str
    height_in: float
    weight_lb: float
    goal: GoalEnum
    activity_level: ActivityEnum
    days_available: DaysEnum
    injuries: Optional[str] = None

@router.post("/profile")
def create_profile(body: ProfileRequest, db: Session = Depends(get_db)):
    db.execute(
        text("""
            INSERT INTO user_profiles 
            (user_id, age, sex, height_in, weight_lb, goal, activity_level, days_available, injuries)
            VALUES (:user_id, :age, :sex, :height_in, :weight_lb, :goal, :activity_level, :days_available, :injuries)
        """),
        body.model_dump()
    )
    db.commit()
    return {"message": "Profile saved successfully"}

@router.get("/profile/{user_id}")
def get_profile(user_id: str, db: Session = Depends(get_db)):
    profile = db.execute(
        text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return dict(profile._mapping)

@router.put("/profile/{user_id}")
def update_profile(user_id: str, body: ProfileRequest, db: Session = Depends(get_db)):
    db.execute(
        text("""
            UPDATE user_profiles 
            SET age=:age, sex=:sex, height_in=:height_in, weight_lb=:weight_lb,
                goal=:goal, activity_level=:activity_level, days_available=:days_available,
                injuries=:injuries, updated_at=NOW()
            WHERE user_id=:user_id
        """),
        {**body.model_dump(), "user_id": user_id}
    )
    db.commit()
    return {"message": "Profile updated successfully"}