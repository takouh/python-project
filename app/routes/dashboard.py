from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app, request, flash
import json, hmac, hashlib
import bleach, uuid
from app import db
from flask_login import login_required, current_user
from app.models import Listing, CommissionPayment, IdempotencyKey, PaymentLog

# Existing blueprint

dashboard_bp = Blueprint('dashboard', __name__)

# --- Mobile Money webhook endpoint ---
@dashboard_bp.route('/webhook/momo', methods=['POST'])
@login_required
def momo_webhook():
    """Handle MoMo webhook notifications securely.
    Expected JSON payload:
    {
        "reference_id": "string",
        "listing_id": int,
        "amount": float,
        "status": "SUCCESS|FAILED",
        "idempotency_key": "string"
    }
    Headers must include 'X-MoMo-Signature' using HMAC SHA256 with secret.
    """
    # Verify IP whitelist
    allowed_ips = current_app.config.get('MOMO_ALLOWED_IPS', [])
    client_ip = request.remote_addr
    if allowed_ips and client_ip not in allowed_ips:
        return jsonify({'error': 'IP not allowed'}), 403

    # Verify signature
    signature = request.headers.get('X-MoMo-Signature')
    secret = current_app.config.get('MOMO_WEBHOOK_SECRET')
    if not secret or not signature:
        return jsonify({'error': 'Missing signature or secret'}), 400
    computed_sig = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_sig, signature):
        return jsonify({'error': 'Invalid signature'}), 400

    # Parse JSON body
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Idempotency check
    idem_key = payload.get('idempotency_key')
    if not idem_key:
        return jsonify({'error': 'Missing idempotency key'}), 400
    existing_key = IdempotencyKey.query.filter_by(key=idem_key).first()
    if existing_key:
        if existing_key.used:
            return jsonify({'status': 'already_processed'}), 200
    else:
        existing_key = IdempotencyKey(key=idem_key, used=False)
        db.session.add(existing_key)
        db.session.commit()

    # Basic validation
    listing_id = payload.get('listing_id')
    amount = payload.get('amount')
    reference_id = payload.get('reference_id')
    status = payload.get('status')
    if not all([listing_id, amount, reference_id, status]):
        return jsonify({'error': 'Missing required fields'}), 400

    listing = Listing.query.get(listing_id)
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404
    # Amount must match listing price (or deposit amount logic)
    if float(amount) != float(listing.price):
        return jsonify({'error': 'Amount mismatch'}), 400

    # Verify with MoMo provider (placeholder for real API call)
    # In production, replace with actual provider verification.
    def verify_momo_payment(ref_id):
        # Simulated successful verification
        return True

    if not verify_momo_payment(reference_id) or status != 'SUCCESS':
        return jsonify({'error': 'Payment not successful'}), 400

    # Create payment record if not exists
    payment = CommissionPayment.query.filter_by(
        user_id=current_user.id,
        landlord_id=listing.landlord_id,
        listing_id=listing.id,
        transaction_id=reference_id
    ).first()
    if not payment:
        payment = CommissionPayment(
            user_id=current_user.id,
            landlord_id=listing.landlord_id,
            listing_id=listing.id,
            amount=amount,
            mobile_number=payload.get('mobile_number', ''),
            payment_method='mobile_money',
            transaction_id=reference_id,
            status='completed'
        )
        db.session.add(payment)
        db.session.flush()  # get payment.id for log
        # Log the successful payment event
        log_entry = PaymentLog(
            payment_id=payment.id,
            event='webhook_success',
            data=json.dumps(payload)
        )
        db.session.add(log_entry)
        # Mark idempotency key as used
        existing_key.used = True
        db.session.commit()
    else:
        # Ensure idempotency key is marked used
        existing_key.used = True
        db.session.commit()

    return jsonify({'status': 'processed'}), 200

# Duplicate imports and blueprint removed – continue with existing routes

@dashboard_bp.route('/')
@login_required
def dashboard_home():
    if current_user.is_superadmin:
        return redirect(url_for('admin.dashboard'))
    if current_user.is_landlord:
        return redirect(url_for('dashboard.landlord_dashboard'))
    if current_user.is_agent:
        return redirect(url_for('dashboard.agent_dashboard'))
    return redirect(url_for('dashboard.tenant_dashboard'))


@dashboard_bp.route('/api/profile')
@login_required
def api_profile():
    role = 'tenant'
    if current_user.is_superadmin:
        role = 'superadmin'
    elif current_user.is_landlord:
        role = 'landlord'
    elif current_user.is_agent:
        role = 'agent'

    profile = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'role': role,
    }
    return jsonify({'status': 'success', 'profile': profile})


@dashboard_bp.route('/landlord')
@login_required
def landlord_dashboard():
    if not current_user.is_landlord:
        return redirect(url_for('dashboard.dashboard_home'))

    listings = Listing.query.filter_by(landlord_id=current_user.id).all()
    active_count = Listing.query.filter_by(landlord_id=current_user.id, available=True).count()
    all_listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template(
        'dashboard/landlord.html',
        listings=listings,
        all_listings=all_listings,
        listing_count=len(listings),
        active_count=active_count,
    )


@dashboard_bp.route('/listing/<int:listing_id>')
@login_required
def listing_detail(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    maps_api_key = current_app.config.get('MAPS_API_KEY', '')
    
    has_paid = False
    if current_user.is_superadmin or current_user.id == listing.landlord_id:
        has_paid = True
    else:
        payment = CommissionPayment.query.filter_by(
            user_id=current_user.id,
            landlord_id=listing.landlord_id,
            status='completed'
        ).first()
        if payment:
            has_paid = True

    return render_template('dashboard/listing_detail.html', listing=listing, maps_api_key=maps_api_key, has_paid=has_paid)


@dashboard_bp.route('/pay_commission/<int:listing_id>', methods=['POST'])
@login_required
def pay_commission(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    if current_user.is_superadmin or current_user.id == listing.landlord_id:
        flash("You already have access to this landlord's information.", 'info')
        return redirect(url_for('dashboard.listing_detail', listing_id=listing_id))
        
    payment = CommissionPayment.query.filter_by(
        user_id=current_user.id,
        landlord_id=listing.landlord_id,
        status='completed'
    ).first()
    
    if payment:
        flash('You have already paid the commission for this landlord.', 'info')
        return redirect(url_for('dashboard.listing_detail', listing_id=listing_id))

    mobile_number = bleach.clean((request.form.get('mobile_number') or '').strip())
    payment_method = bleach.clean((request.form.get('payment_method') or '').strip())
    
    if len(mobile_number) < 8:
        flash('Please enter a valid mobile number.', 'warning')
        return redirect(url_for('dashboard.listing_detail', listing_id=listing_id))
        
    if not payment_method:
        flash('Please select a payment method.', 'warning')
        return redirect(url_for('dashboard.listing_detail', listing_id=listing_id))


    new_payment = CommissionPayment(
        user_id=current_user.id,
        landlord_id=listing.landlord_id,
        listing_id=listing.id,
        amount=2000.00,
        mobile_number=mobile_number,
        payment_method=payment_method,
        transaction_id=uuid.uuid4().hex,
        status='completed'
    )
    db.session.add(new_payment)
    db.session.commit()
    
    flash('Payment successful! Landlord contact information is now unlocked.', 'success')
    return redirect(url_for('dashboard.listing_detail', listing_id=listing_id))


@dashboard_bp.route('/agent')
@login_required
def agent_dashboard():
    if not current_user.is_agent:
        return redirect(url_for('dashboard.dashboard_home'))

    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template('dashboard/agent.html', listings=listings)


@dashboard_bp.route('/tenant')
@login_required
def tenant_dashboard():
    listings = Listing.query.filter_by(available=True).order_by(Listing.created_at.desc()).all()
    return render_template('dashboard/tenant.html', listings=listings)
