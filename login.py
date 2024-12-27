from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import psycopg2

DATABASE_URL = "postgresql://fun_game_user:xOuZ6LLpXDxBGg9WnSRalfc1H1dRAqj6@dpg-ctgsn00gph6c73ckd45g-a.singapore-postgres.render.com/fun_game"
SECRET_KEY = "d6A9bE3cAf2D6E5d8eFb6d8A6Bc9D1d5F7A2"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
router = APIRouter()

# Request Model
class LoginRequest(BaseModel):
    username: str
    password: str

# Response Model
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    balance: float

# Function to authenticate user
def authenticate_user(username: str, password: str):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM user_data WHERE username=%s", (username,))
        result = cursor.fetchone()
        conn.close()
        if result and pwd_context.verify(password, result[0]):
            return True
        return False
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Function to create access token
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Login Endpoint
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    try:
        if not authenticate_user(request.username, request.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": request.username}, expires_delta=access_token_expires
        )
        
        # Fetch user balance
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM user_data WHERE username=%s", (request.username,))
        user_balance = cursor.fetchone()[0]
        conn.close()

        return {"access_token": access_token, "token_type": "bearer", "balance": user_balance}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")