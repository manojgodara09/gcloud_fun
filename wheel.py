import random
import psycopg2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from datetime import datetime

DATABASE_URL = "postgresql://fun_game_user:xOuZ6LLpXDxBGg9WnSRalfc1H1dRAqj6@dpg-ctgsn00gph6c73ckd45g-a.singapore-postgres.render.com/fun_game"
SECRET_KEY = "d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM = "HS256"

router = APIRouter()

# JWT Verification
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Request Model
class WheelGameRequest(BaseModel):
    bet_amount: float
    risk: str  # low, medium, or high
    token: str

# Function to calculate segments and winning index
def generate_wheel(risk: str):
    if risk == "low":
        segment_count = 10
        multiplier = 10
    elif risk == "medium":
        segment_count = 20
        multiplier = 5
    elif risk == "high":
        segment_count = 30
        multiplier = 3
    else:
        raise HTTPException(status_code=400, detail="Invalid risk level")
    
    winning_index = random.randint(0, segment_count - 1)
    return segment_count, multiplier, winning_index

# Function to log game results
def log_game_result(username: str, game_name: str, before_balance: float, after_balance: float, multiplier: float, win: bool):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_game_history (user_id, game_name, before_balance, after_balance, multiplier, win, play_time)
        VALUES ((SELECT id FROM user_data WHERE username=%s), %s, %s, %s, %s, %s, %s)
    """, (username, game_name, before_balance, after_balance, multiplier, win, datetime.utcnow()))
    conn.commit()
    conn.close()

@router.post("/play/wheel")
def play_wheel(request: WheelGameRequest):
    username = verify_token(request.token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Generate wheel and winning index
    segment_count, multiplier, winning_index = generate_wheel(request.risk)
    win = winning_index == 0  # Assume segment 0 is the winning segment
    win_amount = request.bet_amount * multiplier if win else 0

    # Get user's current balance
    before_balance = get_user_balance(username)
    if before_balance < request.bet_amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Calculate the new balance
    after_balance = before_balance + win_amount if win else before_balance - request.bet_amount

    # Update the user's balance
    update_user_balance(username, after_balance)

    # Log the game result
    log_game_result(username, "wheel", before_balance, after_balance, multiplier if win else 0, win)

    return {
        "winning_index": winning_index,
        "win_amount": round(win_amount, 2),
        "balance": round(after_balance, 2)
    }

# Utility functions for database operations
def get_user_balance(username: str) -> float:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_data WHERE username=%s", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    raise HTTPException(status_code=404, detail="User not found")

def update_user_balance(username: str, new_balance: float):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_data SET balance=%s WHERE username=%s", (new_balance, username))
    conn.commit()
    conn.close()
