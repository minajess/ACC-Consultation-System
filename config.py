"""
Application configuration.

Values are pulled from environment variables (see .env.example). This keeps
secrets out of source control and makes it easy to change settings between
development and production without touching code.
"""

import os
from datetime import timedelta

# Absolute path to the project root, used to build reliable file paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # SECRET_KEY signs session cookies and CSRF tokens. Must be kept secret
    # and must be changed before any real deployment.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

    # Database configuration - SQLite file stored in the instance/ folder,
    # which Flask keeps outside of version control by convention.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(BASE_DIR, "instance", "abuyog_consultation.db").replace("\\", "/")
)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / cookie security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Flask-WTF CSRF protection is on by default; token expiry set explicitly.
    WTF_CSRF_TIME_LIMIT = 3600

    # In production this should be True (requires HTTPS). Left False here so
    # the app also runs over plain http on localhost during development.
    SESSION_COOKIE_SECURE = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
