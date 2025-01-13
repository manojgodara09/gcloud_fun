import random
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
import psycopg2

# Configuration
DATABASE_URL = "postgresql://postgres:Ramram#123@34.131.182.225:5432/Testdata"
SECRET_KEY="d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM="HS256"

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

# Request Model
class GameRequest(BaseModel):
    bet_amount: float
    target_multiplier: float
    token: str  # JWT token for user authentication


# Function to calculate the crash point
def calculate_crash_point():
    int_point = random.randint(1, 100)
    if int_point <= 50:
        return random.uniform(0, 1)  # 50% chance
    elif int_point <= 75:
        return random.uniform(1, 2)  # 25% chance
    elif int_point <= 95:
        return random.uniform(2, 4)  # 20% chance
    elif int_point <= 99:
        return random.uniform(4, 10)  # 4% chance
    else:
        return random.uniform(10, 100)  # 1% chance

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
        """, (user_id, "Limbo Game", round(current_balance,2), round(new_balance,2), round(crash_point,2), datetime.utcnow()))

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
        "multiplier": round(crash_point,2),
        "winnings": round(winnings, 2),
        "new_balance": round(new_balance, 2),
    }
