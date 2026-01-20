"""
Unified Flask + React Application
Serves React frontend at root, Flask API routes, and OAuth
"""
from backend.routes import api_bp
from web_app import create_app
import os
from flask import jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the main app using the existing web_app factory (includes DB, OAuth, routes)
app = create_app()

# Register the lightweight API blueprint for RQ task orchestration under /api
app.register_blueprint(api_bp, url_prefix='/api')

# Enable CORS for the React frontend, mobile app, and allow cookies for auth
frontend_origin = os.getenv('FRONTEND_ORIGIN', 'http://localhost:3000')
allowed_origins = [
    frontend_origin,
    "http://localhost:3000",
    "http://localhost:8081",   # Expo mobile app
    "http://127.0.0.1:8081",
    "http://localhost:19006",  # Expo web
]
CORS(
    app,
    resources={r"/*": {"origins": allowed_origins}},
    supports_credentials=True,
)


@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "api+web"}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
