from fastapi import FastAPI
from login import router as login_router
from wheel import router as wheel_router
from game_rocket import router as rocket_router
from dice import router as dice_router
from limbo import router as limbo_router
from database import init_db


app = FastAPI()

# Initialize database
init_db()

# Include routers
app.include_router(login_router)
app.include_router(rocket_router)
app.include_router(dice_router)
app.include_router(limbo_router)
app.include_router(wheel_router)

@app.get("/")
def root():
    return {"message": "Welcome to the Casino Backend"}

# Run with: uvicorn main:app --reload
