import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

# Render/Railway/Neon/Supabase all give ONE connection string: DATABASE_URL.
# Locally you can use the separate values below. Both work automatically.
DATABASE_URL = os.getenv("DATABASE_URL")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "personality_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "Password")


def get_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS,
        cursor_factory=RealDictCursor,
    )


def init_db():
    """Creates every table and column the app uses. Safe to run repeatedly."""
    conn = get_connection()
    cur = conn.cursor()

    # 1. Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            journey_status VARCHAR(50) DEFAULT 'New',
            locked_ecosystems JSONB,
            current_step INTEGER DEFAULT 1,
            age INTEGER,
            gender VARCHAR(50),
            occupation VARCHAR(100),
            occupation_status VARCHAR(50),
            organization VARCHAR(255),
            role VARCHAR(255),
            app_state JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Upgrade path for databases created with the old schema:
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(100);")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation VARCHAR(100);")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS app_state JSONB DEFAULT '{}'::jsonb;")

    # 2. Questions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            trait VARCHAR(50) NOT NULL,
            facet VARCHAR(100) NOT NULL,
            text TEXT NOT NULL,
            is_reverse BOOLEAN DEFAULT FALSE
        )
    """)

    # 3. Quiz sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_complete BOOLEAN DEFAULT FALSE,
            qualitative_context JSONB,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)

    # 4. Responses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            session_id INTEGER REFERENCES quiz_sessions(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            PRIMARY KEY (session_id, question_id)
        )
    """)

    # 5. Summaries — now with ALL the columns the report code actually uses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id SERIAL PRIMARY KEY,
            session_id INTEGER UNIQUE REFERENCES quiz_sessions(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            trait_scores JSONB,
            report_cached_json JSONB,
            accuracy_score INTEGER,
            calibration_feedback_score INTEGER,
            prediction_ratings JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("ALTER TABLE summaries ADD COLUMN IF NOT EXISTS id SERIAL;")
    cur.execute("ALTER TABLE summaries ADD COLUMN IF NOT EXISTS report_cached_json JSONB;")
    cur.execute("ALTER TABLE summaries ADD COLUMN IF NOT EXISTS calibration_feedback_score INTEGER;")
    cur.execute("ALTER TABLE summaries ADD COLUMN IF NOT EXISTS prediction_ratings JSONB;")

    # 6. Blueprint answers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blueprint_answers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            question_key VARCHAR(50) NOT NULL,
            answer_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, question_key)
        )
    """)

    # 7. Canvas entries & library
    cur.execute("""
        CREATE TABLE IF NOT EXISTS canvas_entries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            ecosystem VARCHAR(100) NOT NULL,
            entry_text TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending Review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS library_items (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            ecosystem VARCHAR(100) NOT NULL,
            title VARCHAR(255) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            url TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Canvas steps — used by /quiz/canvas/step but was NEVER created before (crash fix)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS canvas_steps (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            step_id INTEGER NOT NULL,
            step_title VARCHAR(255),
            description TEXT,
            deliverable TEXT,
            resource_url TEXT,
            is_locked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, step_id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Complete database schema initialized / upgraded.")
