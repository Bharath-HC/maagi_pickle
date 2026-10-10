from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template,
                   request, send_file, url_for)
from flask_login import current_user, login_required

from ..extensions import csrf, db
from ..forms import AddressForm
from ..models import Address, Order, PaymentMethod, Role
from ..services import cart_service, order_service, payment_service
from ..services.order_service import CheckoutError
from ..services.payment_service import PaymentError

checkout_bp = Blueprint("checkout", __name__, url_prefix="/checkout")


@checkout_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    cart = cart_service.get_or_create_cart(current_user)
    if not cart.items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("products.catalog"))

    address_form = AddressForm()
    if request.method == "POST" and address_form.validate_on_submit():
        addr = Address(user_id=current_user.id, label=address_form.label.data or "Home",
                       name=address_form.name.data, phone=address_form.phone.data,
                       line1=address_form.line1.data, line2=address_form.line2.data,
                       city=address_form.city.data, state=address_form.state.data,
                       pincode=address_form.pincode.data, is_default=address_form.is_default.data)
        if addr.is_default:
            Address.query.filter_by(user_id=current_user.id).update({"is_default": False})
        db.session.add(addr)
        db.session.commit()
        flash("Address saved.", "success")
        return redirect(url_for("checkout.index"))

    addresses = current_user.addresses.order_by(Address.is_default.desc()).all()
    coupon_code = request.args.get("coupon") or cart.coupon_code
    preview = order_service.build_order_preview(cart, current_user, coupon_code)
    allow_cod = current_user.role not in Role.B2B
    return render_template("customer/checkout.html", addresses=addresses, address_form=address_form,
                          preview=preview, allow_cod=allow_cod)


@checkout_bp.route("/place", methods=["POST"])
@login_required
def place():
    cart = cart_service.get_or_create_cart(current_user)
    address_id = request.form.get("address_id", type=int)
    payment_method = request.form.get("payment_method", PaymentMethod.RAZORPAY)
    coupon_code = request.form.get("coupon_code") or cart.coupon_code
    notes = request.form.get("notes")

    address = db.session.get(Address, address_id) if address_id else None
    if not address or address.user_id != current_user.id:
        flash("Please choose a valid delivery address.", "danger")
        return redirect(url_for("checkout.index"))

    try:
        order = order_service.place_order(current_user, address, payment_method, coupon_code, notes, cart=cart)
    except CheckoutError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("checkout.index"))

    if payment_method in (PaymentMethod.COD, PaymentMethod.CREDIT):
        return redirect(url_for("checkout.success", order_number=order.order_number))
    return redirect(url_for("checkout.pay", order_number=order.order_number))


@checkout_bp.route("/pay/<order_number>")
@login_required
def pay(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    if order.is_paid:
        return redirect(url_for("checkout.success", order_number=order.order_number))
    try:
        payment_info = payment_service.create_payment_order(order)
    except PaymentError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("customer.orders"))
    return render_template("customer/pay.html", order=order, payment_info=payment_info)


@checkout_bp.route("/pay/<order_number>/verify", methods=["POST"])
@login_required
@csrf.exempt
def verify(order_number):
    # Exempted from CSRF: Razorpay Checkout.js submits this callback via its own
    # dynamically-built client-side form/XHR without a Flask-generated CSRF token.
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or request.form
    try:
        payment_service.verify_and_confirm(order, data.get("razorpay_order_id"), data.get("razorpay_payment_id"),
                                           data.get("razorpay_signature"))
        if request.is_json:
            return jsonify({"ok": True, "redirect": url_for("checkout.success", order_number=order.order_number)})
        flash("Payment successful! Your order is confirmed.", "success")
        return redirect(url_for("checkout.success", order_number=order.order_number))
    except PaymentError as exc:
        payment_service.mark_payment_failed(order, data.get("razorpay_order_id"), str(exc))
        if request.is_json:
            return jsonify({"ok": False, "error": str(exc)}), 400
        flash(str(exc), "danger")
        return redirect(url_for("checkout.pay", order_number=order.order_number))


@checkout_bp.route("/pay/<order_number>/simulate", methods=["POST"])
@login_required
def simulate(order_number):
    if not current_app.config.get("ALLOW_PAYMENT_SIMULATION") or current_app.config.get("RAZORPAY_KEY_ID"):
        return ("", 404)
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    from ..models import Payment
    payment = Payment.query.filter_by(order_id=order.id).order_by(Payment.created_at.desc()).first()
    if not payment:
        flash("No pending payment found for this order.", "danger")
        return redirect(url_for("checkout.pay", order_number=order_number))
    fake_payment_id = payment_service.simulate_successful_payment_id()
    try:
        payment_service.verify_and_confirm(order, payment.razorpay_order_id, fake_payment_id, None)
        flash("Simulated payment successful (development mode). Your order is confirmed.", "success")
    except PaymentError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("checkout.pay", order_number=order_number))
    return redirect(url_for("checkout.success", order_number=order.order_number))


@checkout_bp.route("/success/<order_number>")
@login_required
def success(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template("customer/order_success.html", order=order)
