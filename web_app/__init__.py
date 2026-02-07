import os
import redis
from rq import Queue
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config import Config
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Route for @login_required
login_manager.login_message_category = 'info'
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # If the app is running behind a proxy (like on Render or HF Spaces), fix the WSGI environment
    if os.environ.get('RENDER') or os.environ.get('SPACE_ID'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1,
                                x_proto=1, x_host=1, x_prefix=1)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Exempt API endpoints from CSRF (they use token auth)
    @csrf.exempt
    def csrf_exempt_api():
        pass

    # Enable CORS for API routes only (not for auth pages)
    # This allows requests from Codespace frontend and mobile app
    allowed_origins = [
        "http://localhost:3000",   # React frontend
        "http://localhost:8081",   # Expo mobile app (web)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8081",
        "http://localhost:19006",  # Expo web
        "http://127.0.0.1:19006",
        "http://localhost:8082",   # Expo web alternate
        "http://127.0.0.1:8082",
    ]
    # Add any additional origins from environment
    extra_origin = os.environ.get('FRONTEND_ORIGIN')
    if extra_origin and extra_origin not in allowed_origins:
        allowed_origins.append(extra_origin)

    # Apply CORS to /api/* and /auth/api/* routes for mobile app support
    CORS(app,
         resources={
             r"/api/*": {"origins": "*"},
             r"/auth/api/*": {"origins": "*"},
             r"/health": {"origins": "*"}
         },
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         supports_credentials=False,
         max_age=3600)

    # Set DEV_MODE from environment
    app.config['DEV_MODE'] = os.environ.get(
        'DEV_MODE', 'False').lower() == 'true'
    if app.config['DEV_MODE']:
        print("\033[93m⚠️  Running in DEV_MODE - API calls will be stubbed!\033[0m")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Initialize Redis connection for RQ
    try:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            raise ValueError(
                "REDIS_URL not set, worker queue will not be available.")
        # ssl_cert_reqs=None is important for managed services like Upstash/Render Redis
        app.redis = redis.from_url(redis_url, ssl_cert_reqs=None)
        app.logger.info("Redis connection for RQ initialized successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Redis connection: {e}")
        app.redis = None

    # Import and register blueprints
    from web_app.main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    from web_app.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from web_app.api_endpoints import api_bp
    app.register_blueprint(api_bp)

    # Assessment API blueprint
    from web_app.assessment_routes import assessment_bp
    app.register_blueprint(assessment_bp)

    # Import models here to ensure they are registered with SQLAlchemy
    from web_app import models

    # Google OAuth blueprint (Flask-Dance)
    from web_app.google_oauth import google_bp, bp as google_auth_bp
    # Register Flask-Dance blueprint at /login/google
    app.register_blueprint(google_bp, url_prefix="/login")
    # Register our auth blueprint for callbacks and helper routes under /auth
    app.register_blueprint(google_auth_bp, url_prefix="/auth")

    # Flask-Dance will use session storage by default
    # This works better for our use case since we create the user in our callback

    return app
