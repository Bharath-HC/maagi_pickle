from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import SupportTicketForm
from ..models import Order, OrderStatus, PartnerCustomer, Role, SupportTicket
from ..services.invoice_service import generate_invoice_pdf

b2b_bp = Blueprint("b2b", __name__, url_prefix="")

CONTEXT = {
    Role.DISTRIBUTOR: {"prefix": "distributor", "title": "Distributor Portal", "role": Role.DISTRIBUTOR},
    Role.WHOLESALER: {"prefix": "wholesaler", "title": "Wholesaler Portal", "role": Role.WHOLESALER},
}


def _guard(role):
    if not current_user.is_authenticated:
        abort(401)
    if current_user.role != role:
        abort(403)
    if not current_user.is_active:
        abort(403)


def _dashboard(role):
    _guard(role)
    ctx = CONTEXT[role]
    orders_q = current_user.orders
    stats = {
        "total_orders": orders_q.count(),
        "pending_orders": orders_q.filter(Order.order_status.in_(OrderStatus.ACTIVE)).count(),
        "delivered_orders": orders_q.filter_by(order_status=OrderStatus.DELIVERED).count(),
        "monthly_purchase": sum((o.total_amount for o in orders_q.filter(
            Order.order_status != OrderStatus.CANCELLED).all()), start=0),
        "outstanding": sum((o.outstanding for o in orders_q.all()), start=0),
    }
    recent = orders_q.order_by(Order.created_at.desc()).limit(5).all()
    return render_template("b2b/dashboard.html", ctx=ctx, stats=stats, recent=recent)


def _orders(role):
    _guard(role)
    ctx = CONTEXT[role]
    page = request.args.get("page", 1, type=int)
    pagination = current_user.orders.order_by(Order.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("b2b/orders.html", ctx=ctx, pagination=pagination, orders=pagination.items)


def _order_detail(role, order_number):
    _guard(role)
    ctx = CONTEXT[role]
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template("b2b/order_detail.html", ctx=ctx, order=order, timeline=order.timeline())


def _invoice(role, order_number):
    _guard(role)
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    if not order.has_invoice:
        abort(404)
    pdf = generate_invoice_pdf(order)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{order.invoice_number or order.order_number}.pdf")


def _payments(role):
    _guard(role)
    ctx = CONTEXT[role]
    orders = current_user.orders.order_by(Order.created_at.desc()).all()
    return render_template("b2b/payments.html", ctx=ctx, orders=orders)


def _customers(role):
    _guard(role)
    ctx = CONTEXT[role]
    customers = PartnerCustomer.query.filter_by(owner_id=current_user.id).order_by(PartnerCustomer.created_at.desc()).all()
    return render_template("b2b/customers.html", ctx=ctx, customers=customers)


def _add_customer(role):
    _guard(role)
    ctx = CONTEXT[role]
    name = request.form.get("name", "").strip()
    if name:
        db.session.add(PartnerCustomer(owner_id=current_user.id, name=name, phone=request.form.get("phone"),
                                       city=request.form.get("city"), notes=request.form.get("notes")))
        db.session.commit()
        flash("Customer added.", "success")
    return redirect(url_for(f"b2b.{ctx['prefix']}_customers"))


def _support(role):
    _guard(role)
    ctx = CONTEXT[role]
    form = SupportTicketForm()
    if form.validate_on_submit():
        db.session.add(SupportTicket(user_id=current_user.id, category=form.category.data,
                                     subject=form.subject.data, message=form.message.data))
        db.session.commit()
        flash("Support ticket submitted. Our team will respond shortly.", "success")
        return redirect(url_for(f"b2b.{ctx['prefix']}_support"))
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    return render_template("b2b/support.html", ctx=ctx, form=form, tickets=tickets)


# Distributor routes
b2b_bp.add_url_rule("/distributor/dashboard", "distributor_dashboard", lambda: _dashboard(Role.DISTRIBUTOR))
b2b_bp.add_url_rule("/distributor/orders", "distributor_orders", lambda: _orders(Role.DISTRIBUTOR))
b2b_bp.add_url_rule("/distributor/orders/<order_number>", "distributor_order_detail",
                   lambda order_number: _order_detail(Role.DISTRIBUTOR, order_number))
b2b_bp.add_url_rule("/distributor/orders/<order_number>/invoice", "distributor_invoice",
                   lambda order_number: _invoice(Role.DISTRIBUTOR, order_number))
b2b_bp.add_url_rule("/distributor/payments", "distributor_payments", lambda: _payments(Role.DISTRIBUTOR))
b2b_bp.add_url_rule("/distributor/customers", "distributor_customers", lambda: _customers(Role.DISTRIBUTOR))
b2b_bp.add_url_rule("/distributor/customers/add", "distributor_add_customer",
                   lambda: _add_customer(Role.DISTRIBUTOR), methods=["POST"])
b2b_bp.add_url_rule("/distributor/support", "distributor_support", lambda: _support(Role.DISTRIBUTOR),
                   methods=["GET", "POST"])

# Wholesaler routes
b2b_bp.add_url_rule("/wholesaler/dashboard", "wholesaler_dashboard", lambda: _dashboard(Role.WHOLESALER))
b2b_bp.add_url_rule("/wholesaler/orders", "wholesaler_orders", lambda: _orders(Role.WHOLESALER))
b2b_bp.add_url_rule("/wholesaler/orders/<order_number>", "wholesaler_order_detail",
                   lambda order_number: _order_detail(Role.WHOLESALER, order_number))
b2b_bp.add_url_rule("/wholesaler/orders/<order_number>/invoice", "wholesaler_invoice",
                   lambda order_number: _invoice(Role.WHOLESALER, order_number))
b2b_bp.add_url_rule("/wholesaler/payments", "wholesaler_payments", lambda: _payments(Role.WHOLESALER))
b2b_bp.add_url_rule("/wholesaler/customers", "wholesaler_customers", lambda: _customers(Role.WHOLESALER))
b2b_bp.add_url_rule("/wholesaler/customers/add", "wholesaler_add_customer",
                   lambda: _add_customer(Role.WHOLESALER), methods=["POST"])
b2b_bp.add_url_rule("/wholesaler/support", "wholesaler_support", lambda: _support(Role.WHOLESALER),
                   methods=["GET", "POST"])
