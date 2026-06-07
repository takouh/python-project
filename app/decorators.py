from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def superadmin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            flash('Access denied. SuperAdmin only.', 'warning')
            return redirect(url_for('main.index'))
        return view_func(*args, **kwargs)

    return wrapped_view


def landlord_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_landlord or current_user.is_agent):
            flash('Only landlords or assigned agents may access this page.', 'warning')
            return redirect(url_for('main.index'))
        return view_func(*args, **kwargs)

    return wrapped_view
