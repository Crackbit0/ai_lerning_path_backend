import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Load .env file only if not on Render or Hugging Face
if not os.environ.get('RENDER') and not os.environ.get('SPACE_ID'):
    load_dotenv(os.path.join(basedir, '.env'))

# Set Flask app for CLI commands (needed for flask db upgrade)
os.environ.setdefault('FLASK_APP', 'run.py')


class Config:
    # Check if running in production (Render or HF Spaces)
    IS_PRODUCTION = bool(os.environ.get('RENDER')
                         or os.environ.get('SPACE_ID'))

    # SECRET_KEY is CRITICAL for sessions and CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get(
        'FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production-2024'

    # Database configuration - Use PostgreSQL (Neon) in production, SQLite locally
    # Set DATABASE_URL environment variable for production PostgreSQL connection
    # Example: postgresql://user:password@hostname/database?sslmode=require
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL') or 'sqlite:///learning_path.db'

    # Fix for Heroku/Render style postgres:// URLs (SQLAlchemy requires postgresql://)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Enable connection health checks
        'pool_recycle': 300,    # Recycle connections every 5 minutes
    }

    # WTF CSRF Settings - Temporarily disabled due to HF Spaces session issues
    # TODO: Re-enable after figuring out session persistence
    WTF_CSRF_ENABLED = False  # Disable CSRF for now - will re-enable with fix
    WTF_CSRF_TIME_LIMIT = None  # No time limit if needed
    WTF_CSRF_SSL_STRICT = False

    # Session configuration - CRITICAL for CSRF to work
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 7200  # 2 hours
    SESSION_COOKIE_NAME = 'learning_path_session'

    # HF Spaces internal traffic is HTTP even though external is HTTPS
    # Setting SECURE=False allows cookies to be set over internal HTTP
    SESSION_COOKIE_SECURE = False  # Must be False for HF Spaces
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
