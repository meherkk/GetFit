from sqlalchemy import text
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from db.database import get_db
import os

router = APIRouter()
pwd_context = CryptContext(schemes = ["bcrypt"])
SECRET_KEY = "wowsecretkey"
ALGORITHM = "HS256"

# --- Request shapes ---
class SignupRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

# --- Helper functions ---
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_token(user_id: str):
    expire = datetime.utcnow() + timedelta(days=30)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

# --- Signup endpoint ---
@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": body.email}
    ).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = hash_password(body.password)
    result = db.execute(
        text("INSERT INTO users (email, name) VALUES (:email, :name) RETURNING id"),
        {"email": body.email, "name": body.name}
    )
    db.commit()
    user_id = result.fetchone()[0]
    
    token = create_token(str(user_id))
    return {"token": token, "user_id": str(user_id)}