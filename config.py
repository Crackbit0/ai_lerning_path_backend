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
    IS_PRODUCTION = bool(os.environ.get('RENDER') or os.environ.get('SPACE_ID'))
    
    # SECRET_KEY is CRITICAL for sessions and CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    
    # Database configuration - Simple SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///learning_path.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
