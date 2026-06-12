"""
auth_routes.py — the ONE auth module (the old root-level auth.py is gone).
Every other route file imports get_current_user from here.
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
import jwt
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
auth_bp = Blueprint("auth", __name__)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Refuse to silently run with a guessable key in production.
    if os.getenv("FLASK_ENV") == "production" or os.getenv("RENDER"):
        raise RuntimeError("SECRET_KEY environment variable is required in production.")
    SECRET_KEY = "dev_only_secret_key"


def generate_token(user_id, email):
    payload = {
        "user_id": user_id,
        "email": email,  # needed for admin checks
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user():
    """Validates the Bearer token. Returns (payload, error_response)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or malformed authorization token"}), 401)
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Your session has expired. Please log in again."}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Invalid session. Please log in again."}), 401)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    hashed_pw = generate_password_hash(password)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO users (email, password_hash, journey_status)
               VALUES (%s, %s, 'New') RETURNING id""",
            (email, hashed_pw),
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
        token = generate_token(user_id, email)
        return jsonify({
            "token": token,
            "journey_status": "New",
            "user": {"id": user_id, "email": email},
        }), 201
    except Exception:
        conn.rollback()
        return jsonify({"error": "That email is already registered. Try signing in instead."}), 400
    finally:
        cur.close()
        conn.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password_hash, journey_status FROM users WHERE email = %s",
        (email,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not user["password_hash"] or ":" not in user["password_hash"]:
        return jsonify({"error": "Invalid email or password"}), 401
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user["id"], user["email"])
    return jsonify({
        "token": token,
        "journey_status": user["journey_status"] or "New",
        "user": {"id": user["id"], "email": user["email"]},
    }), 200
