from database import get_connection

def wipe_database():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        print("🗑️ Initiating database wipe...")
        
        # TRUNCATE deletes all rows. 
        # RESTART IDENTITY resets the IDs (so the next user is ID 1 again).
        # CASCADE tells it to automatically delete all connected data (quiz answers, blueprints, etc).
        cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        
        conn.commit()
        print("✅ Success! All user data, emails, and test results have been deleted.")
        print("✅ Your 75 questions remain safely in the database.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error wiping database: {str(e)}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    wipe_database()