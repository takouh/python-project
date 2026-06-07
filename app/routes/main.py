import bleach
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from app.models import Listing, ContactMessage

main_bp = Blueprint('main', __name__)


def sanitize_text(value: str) -> str:
    return bleach.clean((value or '').strip(), tags=[], attributes={}, strip=True)


@main_bp.route('/')
def index():
    query = request.args.get('q', '')
    if query:
        query_text = sanitize_text(query)
        listings = Listing.query.filter(
            (Listing.title.contains(query_text)) | 
            (Listing.city.contains(query_text)) | 
            (Listing.address.contains(query_text))
        ).filter_by(available=True).all()
    else:
        listings = Listing.query.filter_by(available=True).all()
    
    return render_template('main/index.html', listings=listings, query=query)


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = sanitize_text(request.form.get('name', ''))
        email = sanitize_text(request.form.get('email', '').lower())
        message = sanitize_text(request.form.get('message', ''))

        if not name or len(name) < 3:
            flash('Please enter a valid name.', 'warning')
            return redirect(url_for('main.contact'))

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'warning')
            return redirect(url_for('main.contact'))

        if not message or len(message) < 10:
            flash('Please enter a longer message.', 'warning')
            return redirect(url_for('main.contact'))

        contact_message = ContactMessage(name=name, email=email, message=message)
        db.session.add(contact_message)
        db.session.commit()

        flash('Your message has been received. We will contact you shortly.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('main/contact.html')
