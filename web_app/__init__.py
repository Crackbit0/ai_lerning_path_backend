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
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# 🔹 IMPORTANT: enable type comparison for migrations
migrate = Migrate(compare_type=True)

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 🔹 FIX Render PostgreSQL URL
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    # Proxy fix for Render / Spaces
    if os.environ.get('RENDER') or os.environ.get('SPACE_ID'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_prefix=1
        )

    # CSRF
    csrf.init_app(app)

    # CORS (API only)
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        supports_credentials=False,
        max_age=3600
    )

    # DEV MODE
    app.config['DEV_MODE'] = os.environ.get(
        'DEV_MODE', 'False').lower() == 'true'
    if app.config['DEV_MODE']:
        print("\033[93m⚠️  Running in DEV_MODE - API calls will be stubbed!\033[0m")

    # 🔹 Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # 🔹 IMPORTANT: models must be imported BEFORE migrate.init_app
    from web_app import models  # noqa: F401

    migrate.init_app(app, db)

    # Redis (RQ)
    try:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not set")
        app.redis = redis.from_url(redis_url, ssl_cert_reqs=None)
        app.logger.info("Redis connection initialized.")
    except Exception as e:
        app.logger.error(f"Redis init failed: {e}")
        app.redis = None

    # Blueprints
    from web_app.main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    from web_app.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from web_app.api_endpoints import api_bp
    app.register_blueprint(api_bp)

    from web_app.assessment_routes import assessment_bp
    app.register_blueprint(assessment_bp)

    from web_app.google_oauth import google_bp, bp as google_auth_bp
    app.register_blueprint(google_bp, url_prefix="/login")
    app.register_blueprint(google_auth_bp, url_prefix="/auth")

    return app
