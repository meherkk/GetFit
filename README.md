# GetFit

A full-stack iOS fitness app that generates personalized weekly workout goals and identifies gym machines using computer vision.

## Features

- **Personalized Weekly Goals** — onboard with your fitness profile and get a custom weekly workout plan powered by an XGBoost classifier
- **Gym Machine Scanner** — take a photo of any gym machine and get muscles targeted, how to use it, common mistakes, and YouTube tutorials
- **User Authentication** — secure signup/login with JWT tokens and bcrypt password hashing

## Tech Stack

**Backend:** Python, FastAPI, PostgreSQL (Supabase), SQLAlchemy  
**ML:** XGBoost, PyTorch, ResNet18, scikit-learn, Google Colab  
**APIs:** Claude Vision API (Anthropic), YouTube Data API v3  
**Deployment:** Railway  
**iOS:** SwiftUI (in progress)

## ML Pipeline

### Weekly Goal Recommender (XGBoost)
- Generated synthetic fitness dataset with realistic user profiles
- Engineered features: age, BMI, activity level, days available, fitness goal
- Trained XGBoost classifier to recommend one of four workout plans: lose fat, build muscle, endurance, general fitness

### Gym Machine Classifier (ResNet18)
- Fine-tuned a pretrained ResNet18 CNN via transfer learning using PyTorch in Google Colab
- Trained on a gym equipment dataset with 4 classes: Dumbbells, Elliptical Machine, Home Machine, Recumbent Bike
- 93% training accuracy, 100% validation accuracy

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register a new user |
| POST | `/auth/login` | Login and receive JWT token |
| POST | `/profile` | Save user profile and fitness goals |
| GET | `/profile/{user_id}` | Get user profile |
| PUT | `/profile/{user_id}` | Update user profile |
| POST | `/goals/{user_id}` | Generate weekly workout goal |
| POST | `/scan/{user_id}` | Scan a gym machine and get info |
| GET | `/health` | Health check |

## Setup

1. Clone the repo
   git clone https://github.com/meherkk/GetFit.git

2. Set up the backend
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt

3. Create a `.env` file in the `backend` folder
   DATABASE_URL=your_supabase_connection_string
   ANTHROPIC_API_KEY=your_anthropic_key
   YOUTUBE_API_KEY=your_youtube_key

4. Run the server
   uvicorn main:app --reload

## Database Schema

- `users` — email, name, hashed password
- `user_profiles` — age, sex, height, weight, goal, activity level
- `weekly_goals` — sessions per week, session length, focus area
- `machine_scans` — machine name, muscles targeted, priority level