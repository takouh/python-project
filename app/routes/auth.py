import re
import bleach
import pyotp
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_RULES = (  # nosec B105 -- not a password, just a human-readable policy description
    'at least 12 characters, including uppercase, lowercase, number, and special character'
)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.fullmatch(email))


def normalize_phone(phone: str) -> str:
    return re.sub(r'\D', '', phone or '')


def is_valid_phone(phone: str) -> bool:
    digits = normalize_phone(phone)
    return len(digits) >= 8


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 12
        and re.search(r'[A-Z]', password)
        and re.search(r'[a-z]', password)
        and re.search(r'[0-9]', password)
        and re.search(r'[^A-Za-z0-9]', password)
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_landlord:
            return redirect(url_for('dashboard.landlord_dashboard'))
        if current_user.is_agent:
            return redirect(url_for('dashboard.agent_dashboard'))
        return redirect(url_for('dashboard.tenant_dashboard'))

    if request.method == 'POST':
        blocked_until = session.get('login_blocked_until')
        if blocked_until:
            try:
                blocked_until_dt = datetime.fromisoformat(blocked_until)
            except ValueError:
                blocked_until_dt = None

            if blocked_until_dt and blocked_until_dt > datetime.utcnow():
                flash('Too many failed login attempts. Please try again later.', 'danger')
                return redirect(url_for('auth.login'))
            session.pop('login_blocked_until', None)
            session.pop('failed_logins', None)

        identifier = bleach.clean(request.form.get('identifier', '').strip(), strip=True)
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not identifier or not password:
            flash('Please enter both email/phone and password.', 'warning')
            return redirect(url_for('auth.login'))

        if is_valid_email(identifier.lower()):
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            phone = normalize_phone(identifier)
            user = User.query.filter_by(phone=phone).first() if phone else None

        if user and check_password_hash(user.password_hash, password):
            if user.is_mfa_enabled:
                session['mfa_user_id'] = user.id
                session['mfa_pending'] = True
                session['mfa_remember'] = remember
                session.pop('failed_logins', None)
                session.pop('login_blocked_until', None)
                return redirect(url_for('auth.mfa_verify'))

            login_user(user, remember=remember)
            session.permanent = True
            session.pop('failed_logins', None)
            session.pop('login_blocked_until', None)

            if not user.is_mfa_enabled and (user.is_landlord or user.is_superadmin or user.is_agent):
                flash('MFA is required for landlords, agents, and administrators. Please set it up now.', 'warning')
                return redirect(url_for('auth.mfa_setup'))

            if user.is_superadmin:
                return redirect(url_for('admin.dashboard'))
            if user.is_landlord:
                return redirect(url_for('dashboard.landlord_dashboard'))
            if user.is_agent:
                return redirect(url_for('dashboard.agent_dashboard'))
            return redirect(url_for('dashboard.tenant_dashboard'))

        failed_attempts = session.get('failed_logins', 0) + 1
        session['failed_logins'] = failed_attempts
        if failed_attempts >= 5:
            block_until = datetime.utcnow() + timedelta(minutes=5)
            session['login_blocked_until'] = block_until.isoformat()
            flash('Too many failed login attempts. Please try again in 5 minutes.', 'danger')
        else:
            flash('Invalid credentials, please try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_landlord:
            return redirect(url_for('dashboard.landlord_dashboard'))
        if current_user.is_agent:
            return redirect(url_for('dashboard.agent_dashboard'))
        return redirect(url_for('dashboard.tenant_dashboard'))

    if request.method == 'POST':
        name = bleach.clean(request.form.get('name', '').strip(), strip=True)
        email = bleach.clean(request.form.get('email', '').strip().lower(), strip=True)
        phone_raw = bleach.clean(request.form.get('phone', '').strip(), strip=True)
        phone = phone_raw if phone_raw else None
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'tenant')

        if not name or len(name) < 3:
            flash('Enter a valid name with at least 3 characters.', 'warning')
            return redirect(url_for('auth.register'))

        email = bleach.clean(request.form.get('email', '').strip().lower(), strip=True)
        phone_raw = bleach.clean(request.form.get('phone', '').strip(), strip=True)
        phone = normalize_phone(phone_raw) if phone_raw else None

        if not email and not phone:
            flash('Enter either a valid email address or phone number.', 'warning')
            return redirect(url_for('auth.register'))

        if email and not is_valid_email(email):
            flash('Enter a valid email address.', 'warning')
            return redirect(url_for('auth.register'))

        if phone and not is_valid_phone(phone_raw):
            flash('Enter a valid phone number with at least 8 digits.', 'warning')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return redirect(url_for('auth.register'))

        if not is_strong_password(password):
            flash(f'Password must be {PASSWORD_RULES}.', 'warning')
            return redirect(url_for('auth.register'))

        if role not in ('tenant', 'landlord', 'agent'):
            flash('Select a valid account type.', 'warning')
            return redirect(url_for('auth.register'))

        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('auth.register'))

        if phone and User.query.filter_by(phone=phone).first():
            flash('Phone number already registered.', 'warning')
            return redirect(url_for('auth.register'))

        if not email:
            email = f'{phone}@phone.local'

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            is_landlord=(role == 'landlord'),
            is_agent=(role == 'agent'),
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    if current_user.is_mfa_enabled:
        flash('MFA is already enabled on your account.', 'info')
        return redirect(url_for('dashboard.dashboard_home'))

    # Generate a secret key if not already generated
    if not current_user.mfa_secret:
        current_user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(current_user.mfa_secret)
    otpauth_url = totp.provisioning_uri(name=current_user.email, issuer_name="Housing Platform")
    qr_url = f"https://chart.googleapis.com/chart?chs=200x200&chld=M|0&cht=qr&chl={otpauth_url}"

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if totp.verify(code):
            current_user.is_mfa_enabled = True
            db.session.commit()
            flash('MFA has been successfully enabled on your account.', 'success')
            return redirect(url_for('dashboard.dashboard_home'))
        else:
            flash('Invalid MFA code. Please try again.', 'danger')

    return render_template('auth/mfa_setup.html', secret=current_user.mfa_secret, qr_url=qr_url)


@auth_bp.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    if not session.get('mfa_pending') or not session.get('mfa_user_id'):
        return redirect(url_for('auth.login'))

    user = User.query.get(session['mfa_user_id'])
    if not user or not user.is_mfa_enabled:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code):
            login_user(user, remember=session.get('mfa_remember', False))
            session.permanent = True
            session.pop('mfa_pending', None)
            session.pop('mfa_user_id', None)
            session.pop('mfa_remember', None)
            flash('Logged in successfully.', 'success')
            if user.is_superadmin:
                return redirect(url_for('admin.dashboard'))
            if user.is_landlord:
                return redirect(url_for('dashboard.landlord_dashboard'))
            if user.is_agent:
                return redirect(url_for('dashboard.agent_dashboard'))
            return redirect(url_for('dashboard.tenant_dashboard'))
        else:
            flash('Invalid MFA code. Please try again.', 'danger')

    return render_template('auth/mfa_verify.html')
