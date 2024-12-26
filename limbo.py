import random
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
import psycopg2

# Configuration
DATABASE_URL = "postgresql://fun_game_user:xOuZ6LLpXDxBGg9WnSRalfc1H1dRAqj6@dpg-ctgsn00gph6c73ckd45g-a.singapore-postgres.render.com/fun_game"
SECRET_KEY="d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM="HS256"

router = APIRouter()

# JWT Verification
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        print(f"Verified username: {username}")  # Log the username for debugging
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Request Model
class GameRequest(BaseModel):
    bet_amount: float
    target_multiplier: float
    token: str  # JWT token for user authentication

# Function to generate random float point
def generate_float_point():
    random_bytes = random.getrandbits(64).to_bytes(8, 'big')
    float_point = int.from_bytes(random_bytes, 'big') / (2**64 - 1)
    return float_point

# Function to calculate the crash point
def calculate_crash_point():
    max_payout = 1000000.0
    house_edge = 0.01
    float_point = generate_float_point()
    crash_point = max_payout / (float_point * (1 - house_edge))
    return crash_point

# Limbo Game Endpoint
@router.post("/play/limbo")
def play_limbo(request: GameRequest):
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

        # Calculate game result
        crash_point = calculate_crash_point()
        if crash_point >= request.target_multiplier:
            winnings = request.bet_amount * request.target_multiplier
        else:
            winnings = 0

        new_balance += winnings

        # Update user balance in the database
        cursor.execute("UPDATE user_data SET balance=%s WHERE id=%s", (round(new_balance,2), user_id))

        # Save game history
        cursor.execute("""
            INSERT INTO user_game_history (user_id, game_name, before_balance, after_balance, multiplier, play_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, "Limbo Game", round(current_balance,2), round(new_balance,2), crash_point, datetime.utcnow()))

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
        "multiplier": crash_point,
        "winnings": round(winnings, 2),
        "new_balance": round(new_balance, 2),
    }