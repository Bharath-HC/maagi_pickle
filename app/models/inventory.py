from ..extensions import db
from .base import utcnow


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"
    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    txn_type = db.Column(db.String(16), nullable=False)
    stock_change = db.Column(db.Integer, default=0)
    reserved_change = db.Column(db.Integer, default=0)
    stock_after = db.Column(db.Integer)
    note = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    variant = db.relationship("ProductVariant")
