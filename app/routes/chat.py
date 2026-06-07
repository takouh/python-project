from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import ChatMessage, User, Listing
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat/<int:recipient_id>', methods=['GET', 'POST'])
@login_required
def chat(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        listing_id = request.form.get('listing_id')
        if not message:
            flash('Message cannot be empty.', 'warning')
            return redirect(url_for('chat.chat', recipient_id=recipient_id))
        chat_msg = ChatMessage(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            listing_id=int(listing_id) if listing_id else None,
            message=message,
            created_at=datetime.utcnow()
        )
        db.session.add(chat_msg)
        db.session.commit()
        flash('Message sent.', 'success')
        return redirect(url_for('chat.chat', recipient_id=recipient_id))
    # GET: fetch conversation
    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == current_user.id) & (ChatMessage.recipient_id == recipient.id)) |
        ((ChatMessage.sender_id == recipient.id) & (ChatMessage.recipient_id == current_user.id))
    ).order_by(ChatMessage.created_at.asc()).all()
    return render_template('dashboard/chat.html', recipient=recipient, messages=messages)

@chat_bp.route('/chat/api/unread_count')
@login_required
def unread_count():
    # Simple endpoint returning number of unread messages (placeholder)
    # In a real system we would have a read flag.
    count = ChatMessage.query.filter_by(recipient_id=current_user.id).count()
    return jsonify({'unread': count})
