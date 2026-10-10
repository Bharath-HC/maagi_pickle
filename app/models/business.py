from ..extensions import db
from .base import utcnow


class ApplicationStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class _ApplicationMixin:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    gst_number = db.Column(db.String(20))
    business_type = db.Column(db.String(60))
    expected_monthly_purchase = db.Column(db.String(60))
    status = db.Column(db.String(12), default=ApplicationStatus.PENDING, index=True)
    admin_notes = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=utcnow)
    reviewed_at = db.Column(db.DateTime)

    @db.declared_attr
    def user_id(cls):
        return db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    @db.declared_attr
    def reviewed_by(cls):
        return db.Column(db.Integer, db.ForeignKey("users.id"))


class DistributorApplication(_ApplicationMixin, db.Model):
    __tablename__ = "distributor_applications"
    user = db.relationship("User", foreign_keys="DistributorApplication.user_id")
    target_role = "DISTRIBUTOR"


class WholesalerApplication(_ApplicationMixin, db.Model):
    __tablename__ = "wholesaler_applications"
    user = db.relationship("User", foreign_keys="WholesalerApplication.user_id")
    target_role = "WHOLESALER"


class BulkOrderRequest(db.Model):
    __tablename__ = "bulk_order_requests"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(24), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(160))
    email = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    gst_number = db.Column(db.String(20))
    delivery_address = db.Column(db.String(300))
    expected_delivery_date = db.Column(db.Date)
    message = db.Column(db.Text)
    status = db.Column(db.String(12), default="NEW", index=True)
    admin_note = db.Column(db.String(500))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    created_at = db.Column(db.DateTime, default=utcnow)
    items = db.relationship("BulkOrderItem", backref="request", cascade="all, delete-orphan")
    user = db.relationship("User")


class BulkOrderItem(db.Model):
    __tablename__ = "bulk_order_items"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("bulk_order_requests.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    variant = db.relationship("ProductVariant")


class PartnerCustomer(db.Model):
    __tablename__ = "partner_customers"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(80))
    notes = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=utcnow)


class SupportTicket(db.Model):
    __tablename__ = "support_tickets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(db.String(20), default="GENERAL")
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(12), default="OPEN", index=True)
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User")
