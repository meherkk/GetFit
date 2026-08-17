from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
import anthropic
import base64
import os
import json
import re
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import io
from googleapiclient.discovery import build

router = APIRouter()

# --- Load ResNet18 classifier once at startup ---
CLASS_NAMES = ["Dumbells", "Elliptical Machine", "Home Machine", "Recumbent Bike"]

def load_classifier():
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(CLASS_NAMES))
    model_path = os.path.join(os.path.dirname(__file__), "../ml/gym_classifier.pth")
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model

classifier = load_classifier()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# --- ResNet18 inference ---
def classify_machine(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = classifier(tensor)
        predicted = torch.argmax(output, dim=1).item()
    return CLASS_NAMES[predicted]

# --- Claude Vision for detailed info ---
def identify_machine(image_bytes: bytes, machine_class: str) -> dict:
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
                    "text": f"""This gym equipment has been identified as: {machine_class}.
Respond with ONLY a JSON object, no markdown, no code blocks, no extra text:
{{
    "machine_name": "{machine_class}",
    "muscles_targeted": ["muscle1", "muscle2"],
    "how_to_use": "2-3 sentence description",
    "common_mistakes": "most common mistake to avoid"
}}"""
                }
            ]
        }]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw.strip())

# --- YouTube ---
def get_youtube_videos(machine_name: str):
    youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    response = youtube.search().list(
        q=f"{machine_name} how to use gym tutorial",
        part="snippet",
        maxResults=3,
        type="video"
    ).execute()
    return [item["id"]["videoId"] for item in response["items"]]

# --- Endpoint ---
@router.post("/scan/{user_id}")
async def scan_machine(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_bytes = await file.read()

    profile = db.execute(
        text("SELECT goal FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Step 1: ResNet18 classifies the machine
    machine_class = classify_machine(image_bytes)

    # Step 2: Claude fills in the details
    machine_info = identify_machine(image_bytes, machine_class)

    # Priority scoring
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

    videos = get_youtube_videos(machine_info["machine_name"])

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