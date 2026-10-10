from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property

from ..extensions import db
from .base import D, utcnow


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.String(300))
    image = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    products = db.relationship("Product", backref="category", lazy="dynamic")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(300))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), index=True)
    brand = db.Column(db.String(80), default="Maagi")
    ingredients = db.Column(db.Text)
    nutritional_information = db.Column(db.Text)
    shelf_life = db.Column(db.String(120))
    storage_instructions = db.Column(db.Text)
    manufacturer = db.Column(db.String(200))
    sku = db.Column(db.String(60), unique=True, nullable=False)
    hsn_code = db.Column(db.String(12), default="2001")
    gst_percentage = db.Column(db.Numeric(5, 2), default=12)
    base_price = db.Column(db.Numeric(10, 2), default=0)
    customer_price = db.Column(db.Numeric(10, 2), default=0)
    distributor_price = db.Column(db.Numeric(10, 2), default=0)
    wholesaler_price = db.Column(db.Numeric(10, 2), default=0)
    stock_quantity = db.Column(db.Integer, default=0)
    minimum_order_quantity = db.Column(db.Integer, default=1)
    featured = db.Column(db.Boolean, default=False, index=True)
    active = db.Column(db.Boolean, default=True, index=True)
    is_demo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    variants = db.relationship(
        "ProductVariant", backref="product", cascade="all, delete-orphan",
        order_by="ProductVariant.weight_grams", lazy="select",
    )
    images = db.relationship(
        "ProductImage", backref="product", cascade="all, delete-orphan",
        order_by="ProductImage.sort_order", lazy="select",
    )
    reviews = db.relationship("Review", backref="product", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def active_variants(self):
        return [v for v in self.variants if v.active]

    @property
    def primary_image(self):
        return self.images[0].path if self.images else None

    @property
    def total_stock(self):
        return sum(v.available_stock for v in self.variants if v.active)

    @property
    def in_stock(self):
        return self.total_stock > 0

    def approved_reviews(self):
        return self.reviews.filter_by(status="APPROVED")

    @property
    def rating_summary(self):
        row = db.session.query(func.avg(Review.rating), func.count(Review.id)).filter(
            Review.product_id == self.id, Review.status == "APPROVED").one()
        avg = float(row[0]) if row[0] else 0.0
        return {"average": round(avg, 1), "count": row[1]}

    def sync_stock(self):
        self.stock_quantity = sum(v.stock_quantity for v in self.variants)


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    path = db.Column(db.String(255), nullable=False)
    alt = db.Column(db.String(200))
    sort_order = db.Column(db.Integer, default=0)


class ProductVariant(db.Model):
    __tablename__ = "product_variants"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    weight = db.Column(db.Numeric(8, 2), nullable=False)
    unit = db.Column(db.String(4), nullable=False, default="g")
    sku = db.Column(db.String(60), unique=True, nullable=False)
    mrp = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    customer_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    distributor_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    wholesaler_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved_stock = db.Column(db.Integer, nullable=False, default=0)
    min_stock_level = db.Column(db.Integer, nullable=False, default=10)
    reorder_level = db.Column(db.Integer, nullable=False, default=25)
    image = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

    @hybrid_property
    def weight_grams(self):
        w = float(self.weight or 0)
        return w * 1000 if (self.unit or "g").lower() == "kg" else w

    @weight_grams.expression
    def weight_grams(cls):
        from sqlalchemy import case
        return case((func.lower(cls.unit) == "kg", cls.weight * 1000), else_=cls.weight)

    @property
    def label(self):
        w = D(self.weight)
        txt = str(int(w)) if w == w.to_integral() else str(w.normalize())
        return f"{txt} {self.unit}"

    @property
    def available_stock(self):
        return max(0, (self.stock_quantity or 0) - (self.reserved_stock or 0))

    @property
    def is_low_stock(self):
        return self.available_stock <= (self.min_stock_level or 0)

    @property
    def display_image(self):
        return self.image or self.product.primary_image

    def __repr__(self):
        return f"<Variant {self.sku}>"


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (db.UniqueConstraint("product_id", "user_id", name="uq_review_user_product"),)
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text)
    verified_purchase = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(12), default="APPROVED", index=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User")


class Wishlist(db.Model):
    __tablename__ = "wishlists"
    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_wishlist"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    product = db.relationship("Product")
