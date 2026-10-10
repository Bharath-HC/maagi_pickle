from ..extensions import db
from .base import utcnow


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    razorpay_order_id = db.Column(db.String(60), index=True)
    razorpay_payment_id = db.Column(db.String(60), unique=True)
    razorpay_signature = db.Column(db.String(200))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(6), default="INR")
    status = db.Column(db.String(16), default="CREATED", index=True)
    payment_method = db.Column(db.String(20))
    is_simulated = db.Column(db.Boolean, default=False)
    error_description = db.Column(db.String(255))
    reference = db.Column(db.String(80))
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)
