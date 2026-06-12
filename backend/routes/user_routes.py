"""
user_routes.py — cross-device persistence.

The frontend keeps the user's journey (intro profile, explore selections,
canvas queue, points...) in localStorage via userstore.js. That data used to
live ONLY in the browser, so logging in on a new device showed an empty app.

userstore.js now pushes a snapshot of the user's keys here (debounced), and
index.html pulls the snapshot back down at login. Two endpoints, one column.
"""
import json
from flask import Blueprint, request, jsonify
from database import get_connection
from routes.auth_routes import get_current_user

user_bp = Blueprint("user", __name__)

# Keys we accept from the client. Anything else is ignored.
ALLOWED_PREFIXES = ("journey_",)
ALLOWED_KEYS = {
    "user_profile", "intro_done", "persona_report", "dna_scores",
    "active_session_id", "explore_selections", "explore_selections_raw",
    "explore_current", "canvas_current_path", "canvas_queue", "points_total",
}
MAX_STATE_BYTES = 200_000  # generous; keeps abuse out


def _filter_state(raw):
    if not isinstance(raw, dict):
        return None
    clean = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        if k in ALLOWED_KEYS or k.startswith(ALLOWED_PREFIXES):
            clean[k] = v
    return clean


@user_bp.route("/state", methods=["GET"])
def get_state():
    payload, err = get_current_user()
    if err:
        return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT app_state FROM users WHERE id = %s", (payload["user_id"],))
        row = cur.fetchone()
        return jsonify({"state": (row["app_state"] if row else None) or {}}), 200
    finally:
        cur.close()
        conn.close()


@user_bp.route("/state", methods=["POST"])
def save_state():
    payload, err = get_current_user()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    state = _filter_state(raw.get("state"))
    if state is None:
        return jsonify({"error": "Expected {state: {key: stringValue}}"}), 400
    if len(json.dumps(state)) > MAX_STATE_BYTES:
        return jsonify({"error": "State too large"}), 413

    # If the snapshot includes the intro profile, mirror name/age onto the
    # users row so reports and the peer network can use them.
    name = None
    try:
        profile = json.loads(state.get("user_profile", "{}"))
        name = (profile.get("name") or "").strip()[:100] or None
    except Exception:
        pass

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Merge: server state || new snapshot (client wins per key)
        cur.execute(
            """UPDATE users
               SET app_state = COALESCE(app_state, '{}'::jsonb) || %s::jsonb
               WHERE id = %s""",
            (json.dumps(state), payload["user_id"]),
        )
        if name:
            cur.execute("UPDATE users SET name = %s WHERE id = %s", (name, payload["user_id"]))
        conn.commit()
        return jsonify({"status": "saved"}), 200
    except Exception as e:
        conn.rollback()
        print(f"save_state error: {e}")
        return jsonify({"error": "Could not save your progress."}), 500
    finally:
        cur.close()
        conn.close()
