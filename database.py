import psycopg2

# Update the DATABASE_URL with Google Cloud PostgreSQL connection details
DATABASE_URL = "postgresql://fun_game_user:xOuZ6LLpXDxBGg9WnSRalfc1H1dRAqj6@dpg-ctgsn00gph6c73ckd45g-a.singapore-postgres.render.com/fun_game"

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Create user_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance FLOAT NOT NULL,
            logged_in BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Create user_game_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_game_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            game_name TEXT NOT NULL,
            before_balance FLOAT NOT NULL,
            after_balance FLOAT NOT NULL,
            multiplier FLOAT NOT NULL,
            play_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_data (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()