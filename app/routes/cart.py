from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..services import cart_service, coupon_service, pricing_service
from ..services.cart_service import CartError
from ..services.coupon_service import CouponError

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


def _wants_json():
    return request.is_json or request.accept_mimetypes.best == "application/json" or \
        request.headers.get("X-Requested-With") == "XMLHttpRequest"


@cart_bp.route("/")
@login_required
def view():
    cart = cart_service.get_or_create_cart(current_user)
    lines = cart_service.cart_lines(cart, current_user.role)
    subtotal = sum((l["line_total"] for l in lines), start=pricing_service.D(0))
    return render_template("customer/cart.html", lines=lines, subtotal=subtotal, cart=cart)


@cart_bp.route("/add", methods=["POST"])
@login_required
def add():
    variant_id = request.form.get("variant_id", type=int)
    quantity = request.form.get("quantity", 1, type=int)
    try:
        cart_service.add_item(current_user, variant_id, quantity)
        if _wants_json():
            cart = cart_service.get_or_create_cart(current_user)
            return jsonify({"ok": True, "cart_count": len(cart.items)})
        flash("Added to your cart.", "success")
    except CartError as exc:
        if _wants_json():
            return jsonify({"ok": False, "error": str(exc)}), 400
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("cart.view"))


@cart_bp.route("/update/<int:item_id>", methods=["POST"])
@login_required
def update(item_id):
    quantity = request.form.get("quantity", 1, type=int)
    try:
        cart_service.update_item(current_user, item_id, quantity)
    except CartError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("cart.view"))


@cart_bp.route("/remove/<int:item_id>", methods=["POST"])
@login_required
def remove(item_id):
    cart_service.remove_item(current_user, item_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view"))


@cart_bp.route("/apply-coupon", methods=["POST"])
@login_required
def apply_coupon():
    code = request.form.get("code", "").strip()
    cart = cart_service.get_or_create_cart(current_user)
    subtotal = cart_service.cart_subtotal(cart, current_user.role)
    try:
        coupon = coupon_service.validate_coupon(code, current_user, subtotal)
        cart.coupon_code = coupon.code
        db.session.commit()
        flash(f"Coupon '{coupon.code}' applied!", "success")
    except CouponError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("cart.view"))


@cart_bp.route("/remove-coupon", methods=["POST"])
@login_required
def remove_coupon():
    cart = cart_service.get_or_create_cart(current_user)
    cart.coupon_code = None
    db.session.commit()
    flash("Coupon removed.", "info")
    return redirect(url_for("cart.view"))
