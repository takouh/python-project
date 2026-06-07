from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename, safe_join
from app import db
from app.decorators import superadmin_required
from app.models import User, Listing
from app.routes.landlord import is_safe_image_file, is_safe_video_file, MAX_VIDEO_SIZE, MAX_IMAGE_SIZE
import os
import re
import uuid
import bleach
from decimal import Decimal, InvalidOperation

admin_bp = Blueprint('admin', __name__)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov'}
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_RULES = (  # nosec B105 -- not a password, just a human-readable policy description
    'at least 12 characters, including uppercase, lowercase, number, and special character'
)


def sanitize_text(value: str) -> str:
    return bleach.clean((value or '').strip(), strip=True)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.fullmatch(email))


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 12
        and re.search(r'[A-Z]', password)
        and re.search(r'[a-z]', password)
        and re.search(r'[0-9]', password)
        and re.search(r'[^A-Za-z0-9]', password)
    )


ALLOWED_VIDEO_MIMETYPES = {
    'video/mp4',
    'video/webm',
    'video/ogg',
    'video/quicktime',
}


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


@admin_bp.route('/', methods=['GET', 'POST'])
@login_required
@superadmin_required
def dashboard():
    if request.method == 'POST':
        if request.form.get('form_type') == 'listing':
            title = sanitize_text(request.form.get('title', ''))
            description = sanitize_text(request.form.get('description', ''))
            address = sanitize_text(request.form.get('address', ''))
            city = sanitize_text(request.form.get('city', ''))
            price_raw = request.form.get('price', '').strip()
            video = request.files.get('video')
            image = request.files.get('image')
            video_filename = None
            image_filename = None

            if not title or len(title) < 5:
                flash('Provide a valid title with at least 5 characters.', 'warning')
                return redirect(url_for('admin.dashboard'))

            if not description or len(description) < 20:
                flash('Provide a valid description with at least 20 characters.', 'warning')
                return redirect(url_for('admin.dashboard'))

            if not address or len(address) < 5:
                flash('Enter a valid address.', 'warning')
                return redirect(url_for('admin.dashboard'))

            if not city or len(city) < 2:
                flash('Enter a valid city name.', 'warning')
                return redirect(url_for('admin.dashboard'))

            try:
                price = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                flash('Enter a valid numeric price.', 'warning')
                return redirect(url_for('admin.dashboard'))

            if price <= 0:
                flash('Price must be a positive amount.', 'warning')
                return redirect(url_for('admin.dashboard'))

            if video and video.filename:
                if not is_safe_video_file(video):
                    flash('Video must be a safe, valid MP4, WEBM, OGG or MOV file.', 'danger')
                    return redirect(url_for('admin.dashboard'))

                video.stream.seek(0, os.SEEK_END)
                file_size = video.stream.tell()
                video.stream.seek(0)

                if file_size > MAX_VIDEO_SIZE:
                    flash('Video file must be smaller than 50 MB.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                filename = secure_filename(video.filename)
                if not filename:
                    flash('Invalid file name.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = safe_join(current_app.config['UPLOAD_FOLDER'], filename)
                if not upload_path:
                    flash('Invalid file path.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                video.save(upload_path)
                video_filename = filename

            if image and image.filename:
                if not is_safe_image_file(image):
                    flash('Image must be a safe, valid JPEG or PNG file.', 'danger')
                    return redirect(url_for('admin.dashboard'))

                image.stream.seek(0, os.SEEK_END)
                file_size = image.stream.tell()
                image.stream.seek(0)

                if file_size > MAX_IMAGE_SIZE:
                    flash('Image file must be smaller than 5 MB.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                filename = secure_filename(image.filename)
                if not filename:
                    flash('Invalid image file name.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = safe_join(current_app.config['UPLOAD_FOLDER'], filename)
                if not upload_path:
                    flash('Invalid image path.', 'warning')
                    return redirect(url_for('admin.dashboard'))

                image.save(upload_path)
                image_filename = filename

            new_listing = Listing(
                title=title,
                description=description,
                address=address,
                city=city,
                price=price,
                landlord_id=current_user.id,
                video_filename=video_filename,
                image_filename=image_filename,
            )
            db.session.add(new_listing)
            db.session.commit()
            flash('Listing published successfully.', 'success')
            return redirect(url_for('admin.dashboard'))

        name = sanitize_text(request.form.get('name', ''))
        email = sanitize_text(request.form.get('email', '').lower())
        phone_raw = sanitize_text(request.form.get('phone', ''))
        phone = phone_raw if phone_raw else None
        password = request.form.get('password', '')
        role = request.form.get('role', 'tenant')

        if not name or len(name) < 3:
            flash('Enter a valid name with at least 3 characters.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if not email or not is_valid_email(email):
            flash('Enter a valid email address.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if not password or not is_strong_password(password):
            flash(f'Password must be {PASSWORD_RULES}.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if role not in ('tenant', 'landlord', 'agent'):
            flash('Select a valid account type.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if User.query.filter_by(email=email).first():
            flash('A user with that email already exists.', 'warning')
            return redirect(url_for('admin.dashboard'))

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            is_superadmin=False,
            is_landlord=(role == 'landlord'),
            is_agent=(role == 'agent'),
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'{role.title()} account created successfully.', 'success')
        return redirect(url_for('admin.dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    listings = Listing.query.order_by(Listing.created_at.desc()).all()

    total_users = len(users)
    superadmins = sum(1 for user in users if user.is_superadmin)
    landlords = sum(1 for user in users if user.is_landlord and not user.is_superadmin)
    agents = sum(1 for user in users if user.is_agent and not user.is_superadmin)
    tenants = sum(1 for user in users if not user.is_landlord and not user.is_agent and not user.is_superadmin)
    total_listings = len(listings)
    active_listings = sum(1 for listing in listings if listing.available)

    return render_template(
        'admin/dashboard.html',
        users=users,
        listings=listings,
        total_users=total_users,
        superadmins=superadmins,
        landlords=landlords,
        agents=agents,
        tenants=tenants,
        total_listings=total_listings,
        active_listings=active_listings,
    )


@admin_bp.route('/users')
@login_required
@superadmin_required
def manage_users():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot remove your own admin account.', 'warning')
        return redirect(url_for('admin.dashboard'))

    if user.is_superadmin:
        flash('Superadmin accounts cannot be removed through this panel.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # Clean up landlord listings before removing a landlord account.
    if user.is_landlord:
        Listing.query.filter_by(landlord_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()
    flash(f'{user.name or user.email} has been removed.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/toggle_listing/<int:listing_id>', methods=['POST'])
@login_required
@superadmin_required
def toggle_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    listing.available = not listing.available
    db.session.commit()
    status = 'available' if listing.available else 'unavailable'
    flash(f'Listing "{listing.title}" is now marked as {status}.', 'success')
    return redirect(url_for('admin.dashboard'))
