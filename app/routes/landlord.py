import os
import re
import uuid
import bleach
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename, safe_join
from app.decorators import landlord_required
from app.models import Listing
from app import db

landlord_bp = Blueprint('landlord', __name__)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov'}
ALLOWED_IMAGE_EXTENSIONS = {'jpeg', 'jpg', 'png'}
MAX_VIDEO_SIZE = 50 * 1024 * 1024
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def is_safe_image_file(file_storage) -> bool:
    filename = file_storage.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
        
    file_storage.stream.seek(0)
    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    
    if ext == 'png':
        if not header.startswith(b'\x89PNG\r\n\x1a\n'):
            return False
    elif ext in ('jpg', 'jpeg'):
        if not header.startswith(b'\xff\xd8\xff'):
            return False
            
    file_storage.stream.seek(0)
    body = file_storage.stream.read(2048)
    file_storage.stream.seek(0)
    
    malicious_indicators = [
        b'<?php', b'eval(', b'exec(', b'system(', b'shell_exec(', 
        b'passthru(', b'base64_decode(', b'#!/bin', b'<script', b'onload=', b'onerror='
    ]
    for indicator in malicious_indicators:
        if indicator in body:
            return False
            
    return True


def is_safe_video_file(file_storage) -> bool:
    filename = file_storage.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False
        
    file_storage.stream.seek(0)
    header = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    
    if ext == 'mp4':
        if b'ftyp' not in header:
            return False
    elif ext == 'webm':
        if not header.startswith(b'\x1a\x45\xdf\xa3'):
            return False
            
    file_storage.stream.seek(0)
    body = file_storage.stream.read(2048)
    file_storage.stream.seek(0)
    
    malicious_indicators = [
        b'<?php', b'eval(', b'exec(', b'system(', b'shell_exec(', 
        b'passthru(', b'base64_decode(', b'#!/bin', b'<script'
    ]
    for indicator in malicious_indicators:
        if indicator in body:
            return False
            
    return True


def sanitize_text(value: str) -> str:
    return bleach.clean((value or '').strip(), strip=True)


ALLOWED_VIDEO_MIMETYPES = {
    'video/mp4',
    'video/webm',
    'video/ogg',
    'video/quicktime',
}


def allowed_video_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def validate_listing_form(form):
    title = sanitize_text(form.get('title', ''))
    description = sanitize_text(form.get('description', ''))
    address = sanitize_text(form.get('address', ''))
    city = sanitize_text(form.get('city', ''))
    price_raw = form.get('price', '').strip()

    if not title or len(title) < 5:
        flash('Title must be at least 5 characters long.', 'warning')
        return None

    if not description or len(description) < 20:
        flash('Description must be at least 20 characters long.', 'warning')
        return None

    if not address or len(address) < 5:
        flash('Enter a valid address.', 'warning')
        return None

    if not city or len(city) < 2:
        flash('Enter a valid city name.', 'warning')
        return None

    if not price_raw:
        flash('Price is required.', 'warning')
        return None

    try:
        price = Decimal(price_raw)
    except (InvalidOperation, ValueError):
        flash('Enter a valid numeric price.', 'warning')
        return None

    if price <= 0:
        flash('Price must be a positive amount.', 'warning')
        return None

    return {
        'title': title,
        'description': description,
        'address': address,
        'city': city,
        'price': price,
    }


@landlord_bp.route('/')
@login_required
@landlord_required
def listings():
    listings = Listing.query.filter_by(landlord_id=current_user.id).all()
    return render_template('landlord/listings.html', listings=listings)


@landlord_bp.route('/new', methods=['GET', 'POST'])
@login_required
@landlord_required
def create_listing():
    if request.method == 'POST':
        listing_data = validate_listing_form(request.form)
        if listing_data is None:
            return redirect(url_for('landlord.create_listing'))

        video = request.files.get('video')
        image = request.files.get('image')
        video_filename = None
        image_filename = None

        if video and video.filename:
            if not is_safe_video_file(video):
                flash('Video must be a safe, valid MP4, WEBM, OGG or MOV file.', 'danger')
                return redirect(url_for('landlord.create_listing'))

            video.stream.seek(0, os.SEEK_END)
            file_size = video.stream.tell()
            video.stream.seek(0)

            if file_size > MAX_VIDEO_SIZE:
                flash('Video file must be smaller than 50 MB.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            filename = secure_filename(video.filename)
            if not filename:
                flash('Invalid file name.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            filename = f"{uuid.uuid4().hex}_{filename}"
            upload_path = safe_join(current_app.config['UPLOAD_FOLDER'], filename)
            if not upload_path:
                flash('Invalid file path.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            video.save(upload_path)
            video_filename = filename

        if image and image.filename:
            if not is_safe_image_file(image):
                flash('Image must be a safe, valid JPEG or PNG file.', 'danger')
                return redirect(url_for('landlord.create_listing'))

            image.stream.seek(0, os.SEEK_END)
            file_size = image.stream.tell()
            image.stream.seek(0)

            if file_size > MAX_IMAGE_SIZE:
                flash('Image file must be smaller than 5 MB.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            filename = secure_filename(image.filename)
            if not filename:
                flash('Invalid image file name.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            filename = f"{uuid.uuid4().hex}_{filename}"
            upload_path = safe_join(current_app.config['UPLOAD_FOLDER'], filename)
            if not upload_path:
                flash('Invalid image path.', 'warning')
                return redirect(url_for('landlord.create_listing'))

            image.save(upload_path)
            image_filename = filename

        listing = Listing(
            title=listing_data['title'],
            description=listing_data['description'],
            address=listing_data['address'],
            city=listing_data['city'],
            price=listing_data['price'],
            landlord_id=current_user.id,
            image_filename=image_filename,
            video_filename=video_filename,
        )
        db.session.add(listing)
        db.session.commit()
        flash('Listing created successfully.', 'success')
        return redirect(url_for('landlord.listings'))

    return render_template('landlord/create.html')


@landlord_bp.route('/delete/<int:listing_id>', methods=['POST'])
@login_required
@landlord_required
def delete_listing(listing_id):
    listing = Listing.query.filter_by(id=listing_id, landlord_id=current_user.id).first_or_404()

    if listing.video_filename:
        video_path = safe_join(current_app.config['UPLOAD_FOLDER'], listing.video_filename)
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass

    if listing.image_filename:
        image_path = safe_join(current_app.config['UPLOAD_FOLDER'], listing.image_filename)
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    db.session.delete(listing)
    db.session.commit()
    flash('Listing deleted successfully.', 'success')
    return redirect(url_for('landlord.listings'))
