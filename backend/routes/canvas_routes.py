from flask import Blueprint, request, jsonify
from database import get_connection
from routes.auth_routes import get_current_user 

canvas_bp = Blueprint("canvas", __name__)

@canvas_bp.route("/entries", methods=["POST"])
def create_entry():
    payload, err = get_current_user()
    if err: return err
    
    data = request.get_json()
    ecosystem = data.get("ecosystem")
    entry_text = data.get("entry_text")
    day_number = data.get("day_number")

    if not ecosystem or not entry_text:
        return jsonify({"error": "Ecosystem and text are required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO canvas_entries (user_id, ecosystem, entry_text, day_number)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at, status
        """, (payload["user_id"], ecosystem, entry_text, day_number))
        
        new_entry = cur.fetchone()
        conn.commit()
        return jsonify({"message": "Saved to Canvas", "entry": new_entry}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@canvas_bp.route("/entries/<ecosystem>", methods=["GET"])
def get_entries(ecosystem):
    payload, err = get_current_user()
    if err: return err

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get all past entries for this specific user and ecosystem, newest first
        cur.execute("""
            SELECT id, entry_text, day_number, status, created_at 
            FROM canvas_entries 
            WHERE user_id = %s AND ecosystem = %s
            ORDER BY created_at DESC
        """, (payload["user_id"], ecosystem))
        
        entries = cur.fetchall()
        return jsonify({"entries": entries}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()