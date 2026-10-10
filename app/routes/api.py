from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Category, Order, OrderStatus, Product, ProductVariant, Role
from ..services import cart_service, pricing_service
from ..services.cart_service import CartError
from ..utils.decorators import admin_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _role():
    return current_user.role if current_user.is_authenticated else Role.CUSTOMER


def _variant_json(v, role):
    return {
        "id": v.id, "sku": v.sku, "label": v.label, "mrp": float(v.mrp),
        "price": float(pricing_service.variant_price(v, role)), "stock": v.available_stock, "active": v.active,
    }


def _product_json(p, role):
    return {
        "id": p.id, "name": p.name, "slug": p.slug, "short_description": p.short_description,
        "category": p.category.name if p.category else None, "image": p.primary_image,
        "in_stock": p.in_stock, "rating": p.rating_summary,
        "variants": [_variant_json(v, role) for v in p.active_variants],
    }


@api_bp.route("/products")
def products():
    role = _role()
    items = Product.query.filter_by(active=True).all()
    return jsonify([_product_json(p, role) for p in items])


@api_bp.route("/products/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, active=True).first()
    if not product:
        return jsonify({"error": "not found"}), 404
    return jsonify(_product_json(product, _role()))


@api_bp.route("/categories")
def categories():
    items = Category.query.filter_by(active=True).order_by(Category.sort_order).all()
    return jsonify([{"id": c.id, "name": c.name, "slug": c.slug} for c in items])


@api_bp.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    data = request.get_json(force=True, silent=True) or {}
    try:
        cart = cart_service.add_item(current_user, data.get("variant_id"), data.get("quantity", 1))
        return jsonify({"ok": True, "item_count": len(cart.items)})
    except CartError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@api_bp.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    data = request.get_json(force=True, silent=True) or {}
    try:
        cart_service.update_item(current_user, data.get("item_id"), data.get("quantity"))
        return jsonify({"ok": True})
    except CartError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@api_bp.route("/cart/remove", methods=["POST"])
@login_required
def cart_remove():
    data = request.get_json(force=True, silent=True) or {}
    cart_service.remove_item(current_user, data.get("item_id"))
    return jsonify({"ok": True})


@api_bp.route("/orders")
@login_required
def orders():
    items = current_user.orders.order_by(Order.created_at.desc()).all()
    return jsonify([{"order_number": o.order_number, "status": o.order_status,
                    "total": float(o.total_amount), "created_at": o.created_at.isoformat()} for o in items])


@api_bp.route("/orders/<order_number>")
@login_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first()
    if not order:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "order_number": order.order_number, "status": order.order_status, "payment_status": order.payment_status,
        "total": float(order.total_amount),
        "items": [{"product": i.product_name, "variant": i.variant_label, "qty": i.quantity,
                  "unit_price": float(i.unit_price)} for i in order.items],
    })


@api_bp.route("/admin/sales")
@login_required
@admin_required
def admin_sales():
    from sqlalchemy import func
    orders = Order.query.filter(Order.order_status != OrderStatus.CANCELLED).all()
    return jsonify({"total_sales": sum(float(o.total_amount) for o in orders), "order_count": len(orders)})


@api_bp.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).limit(200).all()
    return jsonify([{"order_number": o.order_number, "status": o.order_status, "total": float(o.total_amount)}
                   for o in orders])


@api_bp.route("/admin/inventory")
@login_required
@admin_required
def admin_inventory():
    variants = ProductVariant.query.all()
    return jsonify([{"sku": v.sku, "product": v.product.name, "stock": v.stock_quantity,
                    "available": v.available_stock, "low_stock": v.is_low_stock} for v in variants])


@api_bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    from ..models import User
    users = User.query.all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "active": u.is_active}
                   for u in users])
