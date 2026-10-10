from functools import wraps

from flask import abort
from flask_login import current_user

from ..models import Role


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            if not current_user.is_active:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(fn):
    return role_required(Role.ADMIN)(fn)


def distributor_required(fn):
    return role_required(Role.DISTRIBUTOR, Role.ADMIN)(fn)


def wholesaler_required(fn):
    return role_required(Role.WHOLESALER, Role.ADMIN)(fn)


def customer_required(fn):
    return role_required(Role.CUSTOMER)(fn)


def b2b_required(fn):
    return role_required(Role.DISTRIBUTOR, Role.WHOLESALER, Role.ADMIN)(fn)
