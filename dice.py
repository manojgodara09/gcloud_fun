import random
import psycopg2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime

DATABASE_URL = "postgresql://postgres:Ramram#123@34.131.182.225:5432/Testdata"
SECRET_KEY = "d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM = "HS256"

router = APIRouter()

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if token matches the one stored in the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM user_data WHERE username=%s", (username,))
        result = cursor.fetchone()
        conn.close()

        if not result or result[0] != token:
            raise HTTPException(status_code=401, detail="Invalid token")

        print(f"Verified username: {username}")  # Log the username for debugging
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Request Model
class DiceGameRequest(BaseModel):
    bet_amount: float
    roll_over: int
    token: str

# Function to calculate dice roll and result
def roll_dice():
    return random.choices(range(1, 21), weights=[0.08, 0.07, 0.06, 0.06, 0.06, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.04, 0.04, 0.04, 0.03, 0.02])[0]

# Function to calculate multiplier based on roll-over value
def calculate_multiplier(roll_over):
    if roll_over < 2 or roll_over > 19:
        raise HTTPException(status_code=400, detail="Roll-over value must be between 2 and 19")
    winning_chance = (21 - roll_over) / 20
    return round(1 / winning_chance, 2)

# Function to log game results
def log_game_result(username: str, game_name: str, before_balance: float, after_balance: float, multiplier: float):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_game_history (user_id, game_name, before_balance, after_balance, multiplier, play_time)
        VALUES ((SELECT id FROM user_data WHERE username=%s), %s, %s, %s, %s, %s)
    """, (username, game_name, before_balance, after_balance, multiplier, datetime.utcnow()))
    conn.commit()
    conn.close()

@router.post("/play/dice")
def play_dice(request: DiceGameRequest):
    username = verify_token(request.token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Assuming you have a function to get the user's current balance
    before_balance = get_user_balance(username)
    if before_balance < request.bet_amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Deduct the bet amount from the balance
    after_balance = before_balance - request.bet_amount

    dice_roll = roll_dice()
    win = dice_roll > request.roll_over
    multiplier = calculate_multiplier(request.roll_over) if win else 0
    win_amount = request.bet_amount * multiplier

    # Calculate the new balance after the game result
    after_balance += win_amount if win else 0

    # Update the user's balance again with the win amount if applicable
    update_user_balance(username, round(after_balance,2))

    # Log the game result
    log_game_result(username, "Dice Game", round(before_balance,2), round(after_balance,2), multiplier)

    return {
        "dice_roll": dice_roll,
        "win": win,
        "win_amount": round(win_amount, 2),
        "multiplier": round(multiplier, 2),
        "balance": round(after_balance, 2)
    }

# Assuming you have these utility functions
def get_user_balance(username: str) -> float:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_data WHERE username=%s", (username,))
    balance = cursor.fetchone()[0]
    conn.close()
    return balance

def update_user_balance(username: str, new_balance: float):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_data SET balance=%s WHERE username=%s", (new_balance, username))
    conn.commit()
    conn.close()
