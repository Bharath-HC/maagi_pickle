from ..extensions import db
from ..models import AuditLog


def log_action(action, entity=None, entity_id=None, details=None):
    user_id = None
    ip = None
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
    except Exception:
        pass
    try:
        from flask import request
        from ..utils.helpers import client_ip
        ip = client_ip(request)
    except Exception:
        pass
    try:
        db.session.add(AuditLog(user_id=user_id, action=action, entity=entity, entity_id=str(entity_id) if entity_id else None,
                                details=str(details)[:400] if details else None, ip_address=ip))
        db.session.commit()
    except Exception:
        db.session.rollback()
