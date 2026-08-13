from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
import joblib
import numpy as np
import os

router = APIRouter()

# Load model and encoder when backend starts
model = joblib.load(os.path.join(os.path.dirname(__file__), "../../ml/goal_recommender.pkl"))
le = joblib.load(os.path.join(os.path.dirname(__file__), "../../ml/label_encoder.pkl"))

activity_map = {
    "sedentary": 0,
    "lightly_active": 1,
    "moderately_active": 2,
    "very_active": 3
}

plan_details = {
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

@router.post("/goals/{user_id}")
def generate_goal(user_id: str, db: Session = Depends(get_db)):
    # Fetch user profile
    profile = db.execute(
        text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Build feature array matching training data order
    features = np.array([[
        profile.age,
        profile.height_in,
        profile.weight_lb,
        profile.bmi if hasattr(profile, 'bmi') else profile.weight_lb / ((profile.height_in * 0.0254) ** 2),
        profile.days_available if isinstance(profile.days_available, int) else int(profile.days_available.split("-")[0]),
        1,  # experience_level default to beginner
        0,  # gender_encoded default
        activity_map.get(profile.activity_level, 1)
    ]])

    # Predict
    prediction = model.predict(features)[0]
    plan_name = le.inverse_transform([prediction])[0]
    details = plan_details[plan_name]

    # Save to database
    db.execute(
        text("""
            INSERT INTO weekly_goals 
            (user_id, week_start, sessions_per_week, session_length_min, focus_area, description)
            VALUES (:user_id, CURRENT_DATE, :sessions_per_week, :session_length_min, :focus_area, :description)
        """),
        {"user_id": user_id, **details}
    )
    db.commit()

    return {"plan": plan_name, **details}