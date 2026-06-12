import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from routes.auth_routes import auth_bp
from routes.quiz_routes import quiz_bp
from routes.library_routes import library_bp
from routes.canvas_routes import canvas_bp
from routes.network_routes import network_bp
from routes.user_routes import user_bp

app = Flask(__name__)

# CORS: set FRONTEND_ORIGIN to your deployed frontend URL, e.g.
#   FRONTEND_ORIGIN=https://careermap.netlify.app
# Multiple origins: comma-separated. Defaults to * for local development.
_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "*").split(",") if o.strip()]
CORS(app, origins=_origins if _origins != ["*"] else "*")

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(quiz_bp, url_prefix="/api/quiz")
app.register_blueprint(library_bp, url_prefix="/api/library")
app.register_blueprint(canvas_bp, url_prefix="/api/canvas")
app.register_blueprint(network_bp, url_prefix="/api/network")
app.register_blueprint(user_bp, url_prefix="/api/user")


@app.route("/api/health")
def health():
    """Used by the frontend to wake a sleeping free-tier server."""
    return jsonify({"ok": True}), 200


# Make sure the schema exists (idempotent). Runs under gunicorn too.
try:
    init_db()
except Exception as e:
    # Don't kill the process — health endpoint should still respond so you
    # can see the service is up but the DB is misconfigured.
    print(f"[startup] init_db failed: {e}")


if __name__ == "__main__":
    # Local development only. In production use:  gunicorn main:app
    app.run(debug=True, port=5000)
