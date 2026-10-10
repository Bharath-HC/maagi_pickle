from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import AddressForm, ProfileForm
from ..models import Address, Notification, Order, OrderStatus, Product, Wishlist
from ..services import cart_service, order_service
from ..services.audit_service import log_action
from ..services.invoice_service import generate_invoice_pdf
from ..services.order_service import CheckoutError

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


@customer_bp.before_request
@login_required
def _guard():
    pass


@customer_bp.route("/dashboard")
def dashboard():
    orders = current_user.orders.order_by(Order.created_at.desc()).limit(5).all()
    stats = {
        "total_orders": current_user.orders.count(),
        "pending_orders": current_user.orders.filter(Order.order_status.in_(OrderStatus.ACTIVE)).count(),
        "delivered_orders": current_user.orders.filter_by(order_status=OrderStatus.DELIVERED).count(),
        "wishlist_count": Wishlist.query.filter_by(user_id=current_user.id).count(),
    }
    return render_template("customer/dashboard.html", orders=orders, stats=stats)


@customer_bp.route("/orders")
def orders():
    page = request.args.get("page", 1, type=int)
    pagination = current_user.orders.order_by(Order.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("customer/orders.html", pagination=pagination, orders=pagination.items)


@customer_bp.route("/orders/<order_number>")
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template("customer/order_detail.html", order=order, timeline=order.timeline())


@customer_bp.route("/orders/<order_number>/cancel", methods=["POST"])
def cancel_order(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    try:
        order_service.cancel_order(order, by_user=current_user, reason=request.form.get("reason"))
        flash("Your order has been cancelled.", "info")
    except CheckoutError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("customer.order_detail", order_number=order_number))


@customer_bp.route("/orders/<order_number>/invoice")
def order_invoice(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    if not order.has_invoice:
        abort(404)
    pdf = generate_invoice_pdf(order)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{order.invoice_number or order.order_number}.pdf")


@customer_bp.route("/orders/<order_number>/reorder", methods=["POST"])
def reorder(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    added, skipped = 0, 0
    from ..services.cart_service import CartError, add_item
    for item in order.items:
        try:
            add_item(current_user, item.variant_id, item.quantity)
            added += 1
        except CartError:
            skipped += 1
    flash(f"{added} item(s) added to your cart." + (f" {skipped} item(s) could not be added." if skipped else ""),
         "success" if added else "warning")
    return redirect(url_for("cart.view"))


@customer_bp.route("/wishlist")
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).order_by(Wishlist.created_at.desc()).all()
    return render_template("customer/wishlist.html", items=items)


@customer_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
def wishlist_toggle(product_id):
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        db.session.delete(existing)
        flash("Removed from wishlist.", "info")
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        flash("Added to wishlist.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("customer.wishlist"))


@customer_bp.route("/addresses", methods=["GET", "POST"])
def addresses():
    form = AddressForm()
    if form.validate_on_submit():
        if form.is_default.data:
            Address.query.filter_by(user_id=current_user.id).update({"is_default": False})
        db.session.add(Address(user_id=current_user.id, label=form.label.data or "Home", name=form.name.data,
                               phone=form.phone.data, line1=form.line1.data, line2=form.line2.data,
                               city=form.city.data, state=form.state.data, pincode=form.pincode.data,
                               is_default=form.is_default.data))
        db.session.commit()
        flash("Address added.", "success")
        return redirect(url_for("customer.addresses"))
    all_addresses = current_user.addresses.order_by(Address.is_default.desc()).all()
    return render_template("customer/addresses.html", form=form, addresses=all_addresses)


@customer_bp.route("/addresses/<int:address_id>/delete", methods=["POST"])
def delete_address(address_id):
    addr = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    db.session.delete(addr)
    db.session.commit()
    flash("Address removed.", "info")
    return redirect(url_for("customer.addresses"))


@customer_bp.route("/profile", methods=["GET", "POST"])
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone = form.phone.data
        current_user.company_name = form.company_name.data
        current_user.gst_number = form.gst_number.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.pincode = form.pincode.data
        db.session.commit()
        log_action("PROFILE_UPDATED", "User", current_user.id)
        flash("Profile updated successfully.", "success")
        return redirect(url_for("customer.profile"))
    return render_template("customer/profile.html", form=form)


@customer_bp.route("/notifications")
def notifications():
    items = current_user.notifications.order_by(Notification.created_at.desc()).limit(50).all()
    current_user.notifications.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("customer/notifications.html", items=items)
