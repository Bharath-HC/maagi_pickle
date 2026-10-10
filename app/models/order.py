from ..extensions import db
from .base import D, utcnow


class OrderStatus:
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"
    ALL = (PENDING, CONFIRMED, PROCESSING, PACKED, SHIPPED, OUT_FOR_DELIVERY, DELIVERED,
           CANCELLED, RETURN_REQUESTED, RETURNED)
    FLOW = (CONFIRMED, PROCESSING, PACKED, SHIPPED, OUT_FOR_DELIVERY, DELIVERED)
    ACTIVE = (CONFIRMED, PROCESSING, PACKED, SHIPPED, OUT_FOR_DELIVERY)

    @staticmethod
    def label(s):
        return s.replace("_", " ").title()


class PaymentStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class PaymentMethod:
    RAZORPAY = "RAZORPAY"
    COD = "COD"
    CREDIT = "CREDIT"
    MANUAL = "MANUAL"


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    coupon_code = db.Column(db.String(40))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    items = db.relationship("CartItem", backref="cart", cascade="all, delete-orphan", lazy="select",
                            order_by="CartItem.id")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (db.UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),)
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    variant = db.relationship("ProductVariant")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, index=True)
    invoice_number = db.Column(db.String(30), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    price_tier = db.Column(db.String(20), default="CUSTOMER")
    tax_inclusive = db.Column(db.Boolean, default=True)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(12, 2), default=0)
    tax = db.Column(db.Numeric(12, 2), default=0)
    shipping_charge = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    coupon_code = db.Column(db.String(40))
    payment_method = db.Column(db.String(20))
    payment_status = db.Column(db.String(20), default=PaymentStatus.PENDING, index=True)
    order_status = db.Column(db.String(24), default=OrderStatus.PENDING, index=True)
    inventory_state = db.Column(db.String(12), default="NONE")
    customer_name = db.Column(db.String(120))
    customer_email = db.Column(db.String(160))
    customer_phone = db.Column(db.String(20))
    company_name = db.Column(db.String(160))
    gst_number = db.Column(db.String(20))
    shipping_address = db.Column(db.Text)
    billing_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    source = db.Column(db.String(12), default="WEB")
    tracking_note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy="select")
    events = db.relationship("OrderEvent", backref="order", cascade="all, delete-orphan",
                             order_by="OrderEvent.created_at", lazy="select")
    payments = db.relationship("Payment", backref="order", cascade="all, delete-orphan",
                               order_by="Payment.created_at", lazy="select")

    @property
    def is_paid(self):
        return self.payment_status == PaymentStatus.PAID

    @property
    def outstanding(self):
        if self.order_status in (OrderStatus.CANCELLED, OrderStatus.RETURNED, OrderStatus.PENDING):
            return D(0)
        return D(0) if self.is_paid else D(self.total_amount)

    @property
    def can_cancel(self):
        return self.order_status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING)

    @property
    def has_invoice(self):
        return self.order_status not in (OrderStatus.PENDING, OrderStatus.CANCELLED)

    @property
    def status_label(self):
        return OrderStatus.label(self.order_status)

    def timeline(self):
        steps = [("Order Placed", True, self.created_at)]
        paid = self.is_paid or (self.payment_method in ("COD", "CREDIT") and self.order_status != OrderStatus.PENDING)
        ev = {e.status: e.created_at for e in self.events}
        steps.append(("Payment Confirmed" if self.payment_method == "RAZORPAY" else "Order Confirmed",
                      paid, ev.get(OrderStatus.CONFIRMED)))
        order = list(OrderStatus.FLOW)
        cur = order.index(self.order_status) if self.order_status in order else -1
        if self.order_status in (OrderStatus.RETURN_REQUESTED, OrderStatus.RETURNED):
            cur = len(order) - 1
        for label, st in (("Processing", OrderStatus.PROCESSING), ("Packed", OrderStatus.PACKED),
                          ("Shipped", OrderStatus.SHIPPED), ("Out for Delivery", OrderStatus.OUT_FOR_DELIVERY),
                          ("Delivered", OrderStatus.DELIVERED)):
            steps.append((label, cur >= order.index(st), ev.get(st)))
        return steps


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=False)
    product_name = db.Column(db.String(160))
    variant_label = db.Column(db.String(40))
    sku = db.Column(db.String(60))
    hsn_code = db.Column(db.String(12))
    gst_percentage = db.Column(db.Numeric(5, 2), default=0)
    quantity = db.Column(db.Integer, nullable=False)
    mrp = db.Column(db.Numeric(10, 2), default=0)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(12, 2), default=0)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    product = db.relationship("Product")
    variant = db.relationship("ProductVariant")


class OrderEvent(db.Model):
    __tablename__ = "order_events"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    status = db.Column(db.String(24), nullable=False)
    note = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)


class Coupon(db.Model):
    __tablename__ = "coupons"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200))
    discount_type = db.Column(db.String(10), nullable=False, default="PERCENT")
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    min_order = db.Column(db.Numeric(10, 2), default=0)
    max_discount = db.Column(db.Numeric(10, 2))
    start_date = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    usage_limit = db.Column(db.Integer)
    per_user_limit = db.Column(db.Integer, default=1)
    customers_only = db.Column(db.Boolean, default=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    usages = db.relationship("CouponUsage", backref="coupon", cascade="all, delete-orphan", lazy="dynamic")


class CouponUsage(db.Model):
    __tablename__ = "coupon_usages"
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey("coupons.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
