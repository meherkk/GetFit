from fastapi import FastAPI
from dotenv import load_dotenv
from db.database import engine
from routes import auth

load_dotenv()

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "ok", "database": str(e)}