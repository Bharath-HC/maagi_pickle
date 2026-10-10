from ..extensions import db
from .base import utcnow


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(db.String(24), default="INFO")
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.String(400))
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity = db.Column(db.String(60))
    entity_id = db.Column(db.String(40))
    details = db.Column(db.String(400))
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=utcnow, index=True)
    user = db.relationship("User")


class Banner(db.Model):
    __tablename__ = "banners"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    subtitle = db.Column(db.String(240))
    image = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    cta_label = db.Column(db.String(40))
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(500))


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
