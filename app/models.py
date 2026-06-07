from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False)
    is_landlord = db.Column(db.Boolean, default=False)
    is_agent = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    is_mfa_enabled = db.Column(db.Boolean, default=False)
    is_verified_kyc = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    listings = db.relationship('Listing', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Listing(db.Model):
    __tablename__ = 'listings'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    available = db.Column(db.Boolean, default=True)
    image_filename = db.Column(db.String(255), nullable=True)
    video_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    landlord_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.title}>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    listing = db.relationship('Listing', backref='chat_messages')

    def __repr__(self):
        return f'<ChatMessage {self.id} from {self.sender_id} to {self.recipient_id}>'

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ContactMessage {self.email}>'

class IdempotencyKey(db.Model):
    __tablename__ = 'idempotency_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<IdempotencyKey {self.key} used={self.used}>'

class PaymentLog(db.Model):
    __tablename__ = 'payment_logs'

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('commission_payments.id'), nullable=False)
    event = db.Column(db.String(50), nullable=False)
    data = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    payment = db.relationship('CommissionPayment', backref='logs')

    def __repr__(self):
        return f'<PaymentLog {self.event} for payment {self.payment_id}>'


class CommissionPayment(db.Model):
    __tablename__ = 'commission_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    landlord_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    amount = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    mobile_number = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], backref='commission_payments')
    landlord = db.relationship('User', foreign_keys=[landlord_id])
    listing = db.relationship('Listing', backref='commission_payments')

    def __repr__(self):
        return f'<CommissionPayment {self.transaction_id}>'
