from flask import Blueprint, request, jsonify
from database import get_connection
from routes.auth_routes import get_current_user

library_bp = Blueprint("library", __name__)

@library_bp.route("/add", methods=["POST"])
def add_resource():
    payload, err = get_current_user()
    if err: return err
    
    data = request.get_json()
    ecosystem = data.get("ecosystem")
    title = data.get("title")
    resource_type = data.get("resource_type")
    url = data.get("url")

    if not all([ecosystem, title, resource_type, url]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO library_items (user_id, ecosystem, title, resource_type, url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, added_at
        """, (payload["user_id"], ecosystem, title, resource_type, url))
        
        conn.commit()
        return jsonify({"message": "Resource saved to Library"}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@library_bp.route("/<ecosystem>", methods=["GET"])
def get_library(ecosystem):
    payload, err = get_current_user()
    if err: return err

    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, resource_type, url, added_at 
        FROM library_items 
        WHERE user_id = %s AND ecosystem = %s
        ORDER BY added_at DESC
    """, (payload["user_id"], ecosystem))
    
    items = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({"items": items}), 200