from flask import Blueprint, jsonify
from database import get_connection
from routes.auth_routes import get_current_user

network_bp = Blueprint("network", __name__)

@network_bp.route("/<ecosystem>", methods=["GET"])
def get_network(ecosystem):
    payload, err = get_current_user()
    if err: return err

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Fetch peers, using their name or the first part of their email as a display name
        # Order them by who has the highest current_step
        cur.execute("""
            SELECT 
                id, 
                COALESCE(name, split_part(email, '@', 1)) as display_name,
                current_step
            FROM users 
            WHERE journey_status = 'Locked_In'
            ORDER BY current_step DESC
            LIMIT 15
        """)
        peers = cur.fetchall()
        return jsonify({"peers": peers}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()