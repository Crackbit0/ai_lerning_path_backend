import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env only in local development
if not os.environ.get("RENDER") and not os.environ.get("SPACE_ID"):
    load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # --------------------------------------------------
    # Environment
    # --------------------------------------------------
    IS_PRODUCTION = bool(os.environ.get("RENDER")
                         or os.environ.get("SPACE_ID"))

    # --------------------------------------------------
    # Security
    # --------------------------------------------------
    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or "dev-secret-key-change-in-production"
    )

    # --------------------------------------------------
    # Database
    # --------------------------------------------------
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        # Render uses postgres://, SQLAlchemy needs postgresql://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace(
                "postgres://", "postgresql://", 1
            )
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local fallback
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'learning_path.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --------------------------------------------------
    # CSRF (temporarily disabled)
    # --------------------------------------------------
    WTF_CSRF_ENABLED = False
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False

    # --------------------------------------------------
    # Session / Cookies
    # --------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "learning_path_session"
    PERMANENT_SESSION_LIFETIME = 7200  # 2 hours

    # HF Spaces + Render internal traffic
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # --------------------------------------------------
    # Logging
    # --------------------------------------------------
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT")
