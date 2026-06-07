import os
import secrets
from dotenv import load_dotenv
from flask import Flask, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import text
from werkzeug.security import generate_password_hash

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'
csrf = CSRFProtect()

def _get_superadmin_password():
    """Read superadmin password from env; fall back to the requested admin password."""
    password = os.getenv('SUPERADMIN_PASSWORD')
    if not password:
        password = 'Takouh@gmail123'
        print(
            f'\n*** No SUPERADMIN_PASSWORD env var set. '
            f'Using fallback superadmin password: {password}\n'
            f'*** Set SUPERADMIN_PASSWORD in your .env file in production.\n'
        )
    return password


DEFAULT_SUPERADMIN = {
    'name': 'Takouh Hycenth',
    'email': 'takouh@gmail.com',
    'password': _get_superadmin_password(),
}


def ensure_user_columns(app):
    with app.app_context():
        if db.engine.dialect.name != 'sqlite':
            return

        with db.engine.connect() as conn:
            # Check if users table exists first
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users';"))
            if not res.fetchone():
                return

            result = conn.execute(text("PRAGMA table_info(users);"))
            columns = [row[1] for row in result]
            if 'name' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(120);"))
            if 'is_agent' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_agent BOOLEAN DEFAULT 0;"))
            conn.commit()


def ensure_listing_video_column(app):
    with app.app_context():
        if db.engine.dialect.name != 'sqlite':
            return

        with db.engine.connect() as conn:
            # Check if listings table exists first
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='listings';"))
            if not res.fetchone():
                return

            result = conn.execute(text("PRAGMA table_info(listings);"))
            columns = [row[1] for row in result]
            if 'video_filename' not in columns:
                conn.execute(text("ALTER TABLE listings ADD COLUMN video_filename VARCHAR(255);"))
            conn.commit()


def ensure_user_phone_column(app):
    with app.app_context():
        with db.engine.connect() as conn:
            if db.engine.dialect.name == 'sqlite':
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users';"))
                if not res.fetchone():
                    return
                result = conn.execute(text("PRAGMA table_info(users);"))
                columns = [row[1] for row in result]
                if 'phone' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20);"))
                conn.commit()
            elif db.engine.dialect.name == 'postgresql':
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='phone';"))
                if not res.fetchone():
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20);"))
                conn.commit()


def ensure_user_mfa_columns(app):
    with app.app_context():
        with db.engine.connect() as conn:
            if db.engine.dialect.name == 'sqlite':
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users';"))
                if not res.fetchone():
                    return
                result = conn.execute(text("PRAGMA table_info(users);"))
                columns = [row[1] for row in result]
                if 'mfa_secret' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(32);"))
                if 'is_mfa_enabled' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_mfa_enabled BOOLEAN DEFAULT 0;"))
                if 'is_verified_kyc' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_verified_kyc BOOLEAN DEFAULT 0;"))
                conn.commit()
            elif db.engine.dialect.name == 'postgresql':
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='mfa_secret';"))
                if not res.fetchone():
                    conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(32);"))
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_mfa_enabled';"))
                if not res.fetchone():
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_mfa_enabled BOOLEAN DEFAULT FALSE;"))
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_verified_kyc';"))
                if not res.fetchone():
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_verified_kyc BOOLEAN DEFAULT FALSE;"))
                conn.commit()


def seed_default_superadmin(app):
    from app.models import User
    with app.app_context():
        # Remove all other users and their dependent records so only the superadmin remains.
        db.session.execute(text('DELETE FROM payment_logs'))
        db.session.execute(text('DELETE FROM commission_payments'))
        db.session.execute(text('DELETE FROM chat_messages'))
        db.session.execute(text('DELETE FROM listings'))
        db.session.execute(text('DELETE FROM contact_messages'))
        db.session.execute(text('DELETE FROM idempotency_keys'))
        db.session.execute(
            text('DELETE FROM users WHERE email != :email'),
            {'email': DEFAULT_SUPERADMIN['email']}
        )
        db.session.commit()

        existing = User.query.filter_by(email=DEFAULT_SUPERADMIN['email']).first()
        if existing:
            existing.name = DEFAULT_SUPERADMIN['name']
            existing.password_hash = generate_password_hash(DEFAULT_SUPERADMIN['password'])
            existing.is_superadmin = True
            existing.is_landlord = False
            existing.is_agent = False
            existing.phone = None
            db.session.commit()
            return

        superadmin = User(
            name=DEFAULT_SUPERADMIN['name'],
            email=DEFAULT_SUPERADMIN['email'],
            password_hash=generate_password_hash(DEFAULT_SUPERADMIN['password']),
            is_superadmin=True,
            is_landlord=False,
            is_agent=False,
        )
        db.session.add(superadmin)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return db.session.get(User, int(user_id))


def create_app(config_object='config.Config'):
    app = Flask(__name__, static_folder='static', template_folder='templates', instance_relative_config=True)
    app.config.from_object(config_object)
    
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads')), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.before_request
    def rate_limit_before_request():
        # Simple IP-based rate limiting (10 requests per minute for login and API)
        from collections import defaultdict
        from time import time
        if not hasattr(app, '_rate_limit_store'):
            app._rate_limit_store = defaultdict(list)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        now = time()
        # Clean up old timestamps
        timestamps = [t for t in app._rate_limit_store[client_ip] if now - t < 60]
        app._rate_limit_store[client_ip] = timestamps
        # Identify critical endpoints
        path = request.path
        if path.startswith('/auth/login') or path.startswith('/api/'):
            if len(timestamps) >= 10:
                return "Too many requests. Please wait a moment.", 429
            app._rate_limit_store[client_ip].append(now)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(self)')
        response.headers.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        response.headers.setdefault('X-XSS-Protection', '0')
        response.headers.setdefault('Cache-Control', 'no-store, no-cache, must-revalidate, private')
        if not request.host.startswith('127.0.0.1') and not request.host.startswith('localhost'):
            if not app.debug and app.config.get('SESSION_COOKIE_SECURE'):
                response.headers.setdefault('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload')
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' https://maps.googleapis.com https://maps.gstatic.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://maps.gstatic.com https://chart.googleapis.com; connect-src 'self'; frame-src 'none';",
        )
        return response

    with app.app_context():
        from app import models
        db.create_all()
        
    # Run migrations/seeding
    ensure_user_columns(app)
    ensure_user_phone_column(app)
    ensure_user_mfa_columns(app)
    ensure_listing_video_column(app)
    seed_default_superadmin(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.landlord import landlord_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(landlord_bp, url_prefix='/landlord')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    return app
