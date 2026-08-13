from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
import anthropic
import base64
import os
from googleapiclient.discovery import build

router = APIRouter()

def get_youtube_videos(machine_name: str):
    youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    response = youtube.search().list(
        q=f"{machine_name} how to use gym tutorial",
        part="snippet",
        maxResults=3,
        type="video"
    ).execute()
    return [item["id"]["videoId"] for item in response["items"]]

def identify_machine(image_bytes: bytes):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64
                    }
                },
                {
                    "type": "text",
                    "text": """Identify this gym machine. Respond with ONLY a JSON object, no markdown, no code blocks, no extra text:
                    {
                        "machine_name": "name of machine",
                        "muscles_targeted": ["muscle1", "muscle2"],
                        "how_to_use": "2-3 sentence description",
                        "common_mistakes": "most common mistake to avoid"
                    }"""
                }
            ]
        }]
    )
    
    import json
    import re
    raw = response.content[0].text.strip()
    # Strip markdown code blocks if present
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw.strip())
    
    import json
    return json.loads(response.content[0].text)

@router.post("/scan/{user_id}")
async def scan_machine(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Read the uploaded image
    image_bytes = await file.read()
    
    # Get user profile for priority scoring
    profile = db.execute(
        text("SELECT goal from user_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Identify machine with Claude
    machine_info = identify_machine(image_bytes)

    # Simple priority scoring based on goal and machine
    muscle_goals = {
        "build_muscle": ["chest", "back", "legs", "shoulders", "arms", "glutes"],
        "lose_fat": ["full body", "cardio", "core"],
        "endurance": ["cardio", "core", "legs"],
        "general_fitness": ["full body", "core"]
    }

    targeted = [m.lower() for m in machine_info["muscles_targeted"]]
    goal_muscles = muscle_goals.get(profile.goal, [])
    matches = sum(1 for m in targeted if any(g in m for g in goal_muscles))
    
    if matches >= 2:
        priority = "high"
    elif matches == 1:
        priority = "medium"
    else:
        priority = "low"

    # Get YouTube videos
    videos = get_youtube_videos(machine_info["machine_name"])

    # Save scan to database
    db.execute(
        text("""
            INSERT INTO machine_scans (user_id, machine_name, muscles_targeted, priority_level)
            VALUES (:user_id, :machine_name, :muscles_targeted, :priority_level)
        """),
        {
            "user_id": user_id,
            "machine_name": machine_info["machine_name"],
            "muscles_targeted": machine_info["muscles_targeted"],
            "priority_level": priority
        }
    )
    db.commit()

    return {
        "machine_name": machine_info["machine_name"],
        "muscles_targeted": machine_info["muscles_targeted"],
        "how_to_use": machine_info["how_to_use"],
        "common_mistakes": machine_info["common_mistakes"],
        "priority_level": priority,
        "youtube_video_ids": videos
    }