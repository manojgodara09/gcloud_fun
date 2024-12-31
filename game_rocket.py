from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt, JWTError
import psycopg2
import random
from datetime import datetime

# Configuration
DATABASE_URL = "postgresql://fun_game_user:xOuZ6LLpXDxBGg9WnSRalfc1H1dRAqj6@dpg-ctgsn00gph6c73ckd45g-a.singapore-postgres.render.com/fun_game"
SECRET_KEY = "d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM = "HS256"

router = APIRouter()

# JWT Verification
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

# Function to calculate multipliers without house edge
def calculate_multipliers():
    multipliers = [0, 0.5, 1, 1.5, 2, 3, 5, 10]
    probabilities = [0.22, 0.313, 0.1, 0.20, 0.14, 0.025, 0.001, 0.001]  # Original probabilities

    # Normalize probabilities to sum to 1
    total = sum(probabilities)
    normalized_probabilities = [p / total for p in probabilities]

    return multipliers, normalized_probabilities

# Function to pick a multiplier based on probabilities
def get_weighted_multiplier():
    multipliers, probabilities = calculate_multipliers()
    return random.choices(multipliers, weights=probabilities, k=1)[0]

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

# Request Model
class GameRequest(BaseModel):
    bet_amount: float
    token: str  # JWT token for user authentication

# Rocket Game Endpoint
@router.post("/play/rocket")
def play_rocket(request: GameRequest):
    # Verify JWT Token
    username = verify_token(request.token)

    # Connect to the database
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Fetch user balance
        cursor.execute("SELECT id, balance FROM user_data WHERE username=%s", (username,))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        user_id, current_balance = result

        # Check if user has sufficient balance
        if request.bet_amount > current_balance:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Deduct bet amount upfront
        new_balance = current_balance - request.bet_amount

        # Generate multiplier and calculate winnings
        multiplier = get_weighted_multiplier()
        winnings = request.bet_amount * multiplier

        # Update balance with winnings
        new_balance += winnings

        # Update user balance in the database
        cursor.execute("UPDATE user_data SET balance=%s WHERE id=%s", (round(new_balance, 2), user_id))

        # Save game history
        cursor.execute("""
            INSERT INTO user_game_history (user_id, game_name, before_balance, after_balance, multiplier, play_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, "Rocket Game", round(current_balance, 2), round(new_balance, 2), multiplier, datetime.utcnow()))

        # Commit transaction
        conn.commit()

    except psycopg2.DatabaseError as db_error:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    finally:
        conn.close()

    # Return response
    return {
        "multiplier": multiplier,
        "winnings": round(winnings, 2),
        "new_balance": round(new_balance, 2),
    }