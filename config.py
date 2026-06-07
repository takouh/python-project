import os
from datetime import timedelta
from dotenv import load_dotenv

base_dir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

def _default_sqlite_uri(path: str) -> str:
    return f"sqlite:///{path.replace('\\', '/')}"


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY environment variable must be set and kept secret.')

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        _default_sqlite_uri(os.path.join(base_dir, 'instance', 'housing_platform.db')),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(base_dir, 'app', 'static', 'uploads')
    MAPS_API_KEY = os.getenv('MAPS_API_KEY', '')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    PREFERRED_URL_SCHEME = 'https'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    WTF_CSRF_TIME_LIMIT = 3600
