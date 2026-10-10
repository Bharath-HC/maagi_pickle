from ..extensions import db
from ..models import Notification, Role, User


def notify(user_id, title, message, category="INFO", link=None):
    db.session.add(Notification(user_id=user_id, title=title, message=message, category=category, link=link))
    db.session.commit()


def notify_admins(title, message, link=None):
    admin_ids = [u.id for u in User.query.filter_by(role=Role.ADMIN, is_active=True).all()]
    for uid in admin_ids:
        db.session.add(Notification(user_id=uid, title=title, message=message, category="ADMIN", link=link))
    db.session.commit()
