from datetime import timedelta

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager
from .base import utcnow


class Role:
    ADMIN = "ADMIN"
    DISTRIBUTOR = "DISTRIBUTOR"
    WHOLESALER = "WHOLESALER"
    CUSTOMER = "CUSTOMER"
    ALL = (ADMIN, DISTRIBUTOR, WHOLESALER, CUSTOMER)
    B2B = (DISTRIBUTOR, WHOLESALER)
    SHOPPERS = (CUSTOMER, WHOLESALER, DISTRIBUTOR)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CUSTOMER, index=True)
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(10))
    gst_number = db.Column(db.String(20))
    company_name = db.Column(db.String(160))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    last_login = db.Column(db.DateTime)

    addresses = db.relationship("Address", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    orders = db.relationship("Order", backref="user", lazy="dynamic")
    notifications = db.relationship("Notification", backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > utcnow())

    def register_failed_login(self):
        self.failed_attempts = (self.failed_attempts or 0) + 1
        if self.failed_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
            self.locked_until = utcnow() + timedelta(minutes=current_app.config["LOCKOUT_MINUTES"])
            self.failed_attempts = 0

    def register_success(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.last_login = utcnow()

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_b2b(self):
        return self.role in Role.B2B

    @property
    def role_label(self):
        return self.role.title()

    @property
    def dashboard_endpoint(self):
        # NOTE: distributor/wholesaler dashboards live in the 'b2b' blueprint,
        # not standalone 'distributor'/'wholesaler' blueprints.
        return {
            Role.ADMIN: "admin.dashboard",
            Role.DISTRIBUTOR: "b2b.distributor_dashboard",
            Role.WHOLESALER: "b2b.wholesaler_dashboard",
        }.get(self.role, "customer.dashboard")

    @property
    def unread_notifications(self):
        return self.notifications.filter_by(is_read=False).count()

    def __repr__(self):
        return f"<User {self.email} {self.role}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Address(db.Model):
    __tablename__ = "addresses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(40), default="Home")
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    line1 = db.Column(db.String(200), nullable=False)
    line2 = db.Column(db.String(200))
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def as_text(self):
        parts = [self.name, self.line1, self.line2, f"{self.city}, {self.state} - {self.pincode}", f"Phone: {self.phone}"]
        return "\n".join(p for p in parts if p)
