import csv
import io
from datetime import timedelta

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template,
                   request, send_file, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..forms import (B2BReviewForm, BannerForm, CategoryForm, CouponForm, OrderStatusForm,
                     ProductForm, VariantForm)
from ..models import (ApplicationStatus, AuditLog, Banner, BulkOrderRequest, Category, ContactMessage,
                      Coupon, DistributorApplication, D, InventoryTransaction, Notification, Order,
                      OrderItem, OrderStatus, Payment, Product, ProductImage, ProductVariant, Review,
                      Role, Setting, SupportTicket, User, WholesalerApplication, q2, utcnow)
from ..services import inventory_service, order_service
from ..services.audit_service import log_action
from ..services.invoice_service import generate_invoice_pdf
from ..services.notification_service import notify
from ..utils.helpers import allowed_image, save_upload, unique_slug

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def _guard():
    if not current_user.is_authenticated or current_user.role != Role.ADMIN or not current_user.is_active:
        abort(403)


# ---------------------------------------------------------------- dashboard
@admin_bp.route("/dashboard")
def dashboard():
    today = utcnow().date()
    month_start = today.replace(day=1)

    paid_orders = Order.query.filter(Order.order_status != OrderStatus.CANCELLED)
    total_sales = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.order_status != OrderStatus.CANCELLED).scalar()
    today_sales = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.order_status != OrderStatus.CANCELLED, func.date(Order.created_at) == today).scalar()
    monthly_sales = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.order_status != OrderStatus.CANCELLED, Order.created_at >= month_start).scalar()

    total_orders = Order.query.count()
    pending_orders = Order.query.filter(Order.order_status.in_((OrderStatus.PENDING, OrderStatus.CONFIRMED))).count()
    customers_count = User.query.filter_by(role=Role.CUSTOMER).count()
    wholesalers_count = User.query.filter_by(role=Role.WHOLESALER).count()
    distributors_count = User.query.filter_by(role=Role.DISTRIBUTOR).count()

    low_stock = ProductVariant.query.filter(ProductVariant.active == True).all()  # noqa: E712
    low_stock = [v for v in low_stock if v.is_low_stock][:10]

    months, monthly_sales_series, monthly_orders_series = [], [], []
    for i in range(5, -1, -1):
        m_start = (month_start.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        m_end = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append(m_start.strftime("%b"))
        s = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.order_status != OrderStatus.CANCELLED, Order.created_at >= m_start, Order.created_at < m_end).scalar()
        c = Order.query.filter(Order.created_at >= m_start, Order.created_at < m_end).count()
        monthly_sales_series.append(float(s or 0))
        monthly_orders_series.append(c)

    tier_sales = {}
    for tier in ("CUSTOMER", "WHOLESALER", "DISTRIBUTOR"):
        s = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.price_tier == tier, Order.order_status != OrderStatus.CANCELLED).scalar()
        tier_sales[tier] = float(s or 0)

    status_counts = {}
    for status in OrderStatus.ALL:
        status_counts[status] = Order.query.filter_by(order_status=status).count()

    top_products_rows = db.session.query(Product.name, func.coalesce(func.sum(OrderItem.subtotal), 0).label("rev")).join(
        OrderItem, OrderItem.product_id == Product.id).join(Order, Order.id == OrderItem.order_id).filter(
        Order.order_status != OrderStatus.CANCELLED).group_by(Product.id).order_by(func.sum(OrderItem.subtotal).desc()).limit(6).all()
    top_products = [{"name": r[0], "revenue": float(r[1])} for r in top_products_rows]

    return render_template(
        "admin/dashboard.html", total_sales=total_sales, today_sales=today_sales, monthly_sales=monthly_sales,
        total_orders=total_orders, pending_orders=pending_orders, customers_count=customers_count,
        wholesalers_count=wholesalers_count, distributors_count=distributors_count, low_stock=low_stock,
        months=months, monthly_sales_series=monthly_sales_series, monthly_orders_series=monthly_orders_series,
        tier_sales=tier_sales, status_counts=status_counts, top_products=top_products,
    )


# ---------------------------------------------------------------- categories
@admin_bp.route("/categories", methods=["GET", "POST"])
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data, description=form.description.data,
                       sort_order=form.sort_order.data or 0, active=form.active.data)
        cat.slug = unique_slug(Category, form.name.data, db.session)
        if form.image.data:
            cat.image = save_upload(form.image.data, "categories")
        db.session.add(cat)
        db.session.commit()
        log_action("CATEGORY_CREATED", "Category", cat.id, cat.name)
        flash("Category created.", "success")
        return redirect(url_for("admin.categories"))
    items = Category.query.order_by(Category.sort_order).all()
    return render_template("admin/categories.html", form=form, categories=items)


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
def edit_category(cat_id):
    cat = db.session.get(Category, cat_id) or abort(404)
    cat.name = request.form.get("name", cat.name)
    cat.description = request.form.get("description", cat.description)
    cat.sort_order = request.form.get("sort_order", cat.sort_order, type=int)
    cat.active = bool(request.form.get("active"))
    db.session.commit()
    log_action("CATEGORY_UPDATED", "Category", cat.id)
    flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def delete_category(cat_id):
    cat = db.session.get(Category, cat_id) or abort(404)
    if cat.products.count() > 0:
        flash("Cannot delete a category that still has products. Deactivate it instead.", "warning")
    else:
        db.session.delete(cat)
        db.session.commit()
        log_action("CATEGORY_DELETED", "Category", cat_id)
        flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------- products
@admin_bp.route("/products")
def products():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Product.name.ilike(like), Product.sku.ilike(like)))
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/products.html", pagination=pagination, products=pagination.items, q=q)


def _product_form_context(product=None):
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    return form


@admin_bp.route("/products/new", methods=["GET", "POST"])
def new_product():
    form = _product_form_context()
    if form.validate_on_submit():
        product = Product(name=form.name.data, category_id=form.category_id.data,
                          short_description=form.short_description.data, description=form.description.data,
                          ingredients=form.ingredients.data, nutritional_information=form.nutritional_information.data,
                          shelf_life=form.shelf_life.data, storage_instructions=form.storage_instructions.data,
                          manufacturer=form.manufacturer.data or "Prashanth Home Industries", sku=form.sku.data,
                          hsn_code=form.hsn_code.data or "2001", gst_percentage=form.gst_percentage.data,
                          minimum_order_quantity=form.minimum_order_quantity.data, featured=form.featured.data,
                          active=form.active.data)
        product.slug = unique_slug(Product, form.name.data, db.session)
        db.session.add(product)
        db.session.flush()
        if form.image.data:
            path = save_upload(form.image.data, "products")
            db.session.add(ProductImage(product_id=product.id, path=path, sort_order=0))
        db.session.commit()
        log_action("PRODUCT_CREATED", "Product", product.id, product.name)
        flash("Product created. Now add pack-size variants.", "success")
        return redirect(url_for("admin.edit_product", product_id=product.id))
    return render_template("admin/product_form.html", form=form, product=None, variant_form=VariantForm())


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = _product_form_context(product)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(product)
        if form.image.data:
            path = save_upload(form.image.data, "products")
            if product.images:
                product.images[0].path = path
            else:
                db.session.add(ProductImage(product_id=product.id, path=path, sort_order=0))
        db.session.commit()
        log_action("PRODUCT_UPDATED", "Product", product.id, product.name)
        flash("Product updated.", "success")
        return redirect(url_for("admin.edit_product", product_id=product.id))
    return render_template("admin/product_form.html", form=form, product=product, variant_form=VariantForm())


@admin_bp.route("/products/<int:product_id>/toggle", methods=["POST"])
def toggle_product(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    product.active = not product.active
    db.session.commit()
    log_action("PRODUCT_TOGGLED", "Product", product.id, str(product.active))
    flash(f"{product.name} is now {'active' if product.active else 'inactive'}.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if OrderItem.query.filter_by(product_id=product.id).first():
        product.active = False
        db.session.commit()
        flash("Product has existing orders, so it was deactivated instead of deleted.", "warning")
    else:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted.", "info")
    log_action("PRODUCT_DELETED_OR_DEACTIVATED", "Product", product_id)
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/variants/add", methods=["POST"])
def add_variant(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = VariantForm()
    if form.validate_on_submit():
        variant = ProductVariant(product_id=product.id, weight=form.weight.data, unit=form.unit.data,
                                 sku=form.sku.data, mrp=form.mrp.data, customer_price=form.customer_price.data,
                                 wholesaler_price=form.wholesaler_price.data, distributor_price=form.distributor_price.data,
                                 stock_quantity=form.stock_quantity.data, min_stock_level=form.min_stock_level.data or 10,
                                 reorder_level=form.reorder_level.data or 25, active=form.active.data)
        if form.image.data:
            variant.image = save_upload(form.image.data, "products")
        db.session.add(variant)
        product.sync_stock()
        db.session.commit()
        log_action("VARIANT_CREATED", "ProductVariant", variant.id, variant.sku)
        flash("Pack size added.", "success")
    else:
        flash("Please correct the errors in the variant form: " + "; ".join(
            f"{k}: {', '.join(v)}" for k, v in form.errors.items()), "danger")
    return redirect(url_for("admin.edit_product", product_id=product.id))


@admin_bp.route("/variants/<int:variant_id>/edit", methods=["POST"])
def edit_variant(variant_id):
    variant = db.session.get(ProductVariant, variant_id) or abort(404)
    form = VariantForm()
    if form.validate_on_submit():
        form.populate_obj(variant)
        if form.image.data:
            variant.image = save_upload(form.image.data, "products")
        variant.product.sync_stock()
        db.session.commit()
        log_action("VARIANT_UPDATED", "ProductVariant", variant.id)
        flash("Pack size updated.", "success")
    else:
        flash("Please correct the errors in the variant form.", "danger")
    return redirect(url_for("admin.edit_product", product_id=variant.product_id))


@admin_bp.route("/variants/<int:variant_id>/restock", methods=["POST"])
def restock_variant(variant_id):
    variant = db.session.get(ProductVariant, variant_id) or abort(404)
    qty = request.form.get("quantity", type=int)
    if qty and qty > 0:
        inventory_service.restock(variant, qty, user_id=current_user.id)
        log_action("VARIANT_RESTOCKED", "ProductVariant", variant.id, f"+{qty}")
        flash(f"Added {qty} units to {variant.product.name} ({variant.label}).", "success")
    return redirect(request.referrer or url_for("admin.inventory"))


@admin_bp.route("/variants/<int:variant_id>/delete", methods=["POST"])
def delete_variant(variant_id):
    variant = db.session.get(ProductVariant, variant_id) or abort(404)
    product_id = variant.product_id
    if OrderItem.query.filter_by(variant_id=variant.id).first():
        variant.active = False
        db.session.commit()
        flash("Pack size has existing orders, so it was deactivated instead of deleted.", "warning")
    else:
        db.session.delete(variant)
        db.session.commit()
        flash("Pack size deleted.", "info")
    log_action("VARIANT_DELETED_OR_DEACTIVATED", "ProductVariant", variant_id)
    return redirect(url_for("admin.edit_product", product_id=product_id))


# ---------------------------------------------------------------- inventory
@admin_bp.route("/inventory")
def inventory():
    variants = ProductVariant.query.join(Product).filter(Product.active == True).order_by(Product.name).all()  # noqa: E712
    return render_template("admin/inventory.html", variants=variants)


# ---------------------------------------------------------------- orders
@admin_bp.route("/orders")
def orders():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter_by(order_status=status)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/orders.html", pagination=pagination, orders=pagination.items,
                          status=status, statuses=OrderStatus.ALL)


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    form = OrderStatusForm(order_status=order.order_status)
    form.order_status.choices = [(s, OrderStatus.label(s)) for s in OrderStatus.ALL]
    if form.validate_on_submit():
        order_service.update_order_status(order, form.order_status.data, form.note.data, by_user=current_user)
        flash("Order status updated.", "success")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    return render_template("admin/order_detail.html", order=order, form=form, timeline=order.timeline())


@admin_bp.route("/orders/<int:order_id>/invoice")
def order_invoice(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    if not order.has_invoice:
        abort(404)
    pdf = generate_invoice_pdf(order)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{order.invoice_number or order.order_number}.pdf")


# ---------------------------------------------------------------- customers / b2b users
@admin_bp.route("/customers")
def customers():
    page = request.args.get("page", 1, type=int)
    pagination = User.query.filter_by(role=Role.CUSTOMER).order_by(User.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/customers.html", pagination=pagination, customers=pagination.items)


def _b2b_page(role, applications_model):
    users = User.query.filter_by(role=role).order_by(User.created_at.desc()).all()
    pending = applications_model.query.filter_by(status=ApplicationStatus.PENDING).order_by(
        applications_model.created_at.desc()).all()
    history = applications_model.query.filter(applications_model.status != ApplicationStatus.PENDING).order_by(
        applications_model.created_at.desc()).limit(20).all()
    return render_template("admin/b2b_users.html", role=role, users=users, pending=pending, history=history,
                          form=B2BReviewForm())


@admin_bp.route("/distributors")
def distributors():
    return _b2b_page(Role.DISTRIBUTOR, DistributorApplication)


@admin_bp.route("/wholesalers")
def wholesalers():
    return _b2b_page(Role.WHOLESALER, WholesalerApplication)


@admin_bp.route("/applications/<role>/<int:app_id>/review", methods=["POST"])
def review_application(role, app_id):
    model = DistributorApplication if role == Role.DISTRIBUTOR else WholesalerApplication
    app_row = db.session.get(model, app_id) or abort(404)
    action = request.form.get("action")
    app_row.reviewed_at = utcnow()
    app_row.reviewed_by = current_user.id
    app_row.admin_notes = request.form.get("admin_notes")
    if action == "approve":
        app_row.status = ApplicationStatus.APPROVED
        user = db.session.get(User, app_row.user_id)
        user.role = role
        user.company_name = app_row.company_name
        user.gst_number = app_row.gst_number
        notify(user.id, "Application approved!",
              f"Your {role.title()} application has been approved. Enjoy partner pricing on Maagi products.",
              "APPLICATION", url_for(user.dashboard_endpoint))
        flash(f"{app_row.name} approved as {role.title()}.", "success")
    elif action == "reject":
        app_row.status = ApplicationStatus.REJECTED
        notify(app_row.user_id, "Application update",
              f"Your {role.title()} application was not approved at this time.", "APPLICATION")
        flash("Application rejected.", "info")
    db.session.commit()
    log_action(f"{role}_APPLICATION_{action.upper()}", "User", app_row.user_id)
    return redirect(url_for(f"admin.{'distributors' if role == Role.DISTRIBUTOR else 'wholesalers'}"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def toggle_user_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.role == Role.ADMIN:
        flash("Admin accounts cannot be deactivated here.", "warning")
        return redirect(request.referrer or url_for("admin.customers"))
    user.is_active = not user.is_active
    db.session.commit()
    log_action("USER_TOGGLED_ACTIVE", "User", user.id, str(user.is_active))
    flash(f"{user.name} is now {'active' if user.is_active else 'deactivated'}.", "info")
    return redirect(request.referrer or url_for("admin.customers"))


@admin_bp.route("/users/<int:user_id>/suspend-b2b", methods=["POST"])
def suspend_b2b(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.role not in Role.B2B:
        abort(400)
    user.is_active = False
    db.session.commit()
    log_action("B2B_SUSPENDED", "User", user.id)
    flash(f"{user.name}'s business account has been suspended.", "warning")
    return redirect(request.referrer or url_for(f"admin.{'distributors' if user.role == Role.DISTRIBUTOR else 'wholesalers'}"))


# ---------------------------------------------------------------- coupons
@admin_bp.route("/coupons", methods=["GET", "POST"])
def coupons():
    form = CouponForm()
    if form.validate_on_submit():
        coupon = Coupon(code=form.code.data.strip().upper(), description=form.description.data,
                        discount_type=form.discount_type.data, discount_value=form.discount_value.data,
                        min_order=form.min_order.data or 0, max_discount=form.max_discount.data,
                        start_date=form.start_date.data, expiry_date=form.expiry_date.data,
                        usage_limit=form.usage_limit.data, per_user_limit=form.per_user_limit.data or 1,
                        active=form.active.data)
        db.session.add(coupon)
        db.session.commit()
        log_action("COUPON_CREATED", "Coupon", coupon.id, coupon.code)
        flash("Coupon created.", "success")
        return redirect(url_for("admin.coupons"))
    items = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template("admin/coupons.html", form=form, coupons=items)


@admin_bp.route("/coupons/<int:coupon_id>/toggle", methods=["POST"])
def toggle_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id) or abort(404)
    coupon.active = not coupon.active
    db.session.commit()
    flash(f"Coupon {coupon.code} is now {'active' if coupon.active else 'inactive'}.", "info")
    return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/<int:coupon_id>/delete", methods=["POST"])
def delete_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id) or abort(404)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted.", "info")
    return redirect(url_for("admin.coupons"))


# ---------------------------------------------------------------- reviews
@admin_bp.route("/reviews")
def reviews():
    items = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=items)


@admin_bp.route("/reviews/<int:review_id>/toggle", methods=["POST"])
def toggle_review(review_id):
    review = db.session.get(Review, review_id) or abort(404)
    review.status = "REJECTED" if review.status == "APPROVED" else "APPROVED"
    db.session.commit()
    flash("Review moderation updated.", "info")
    return redirect(url_for("admin.reviews"))


# ---------------------------------------------------------------- bulk requests / support / enquiries
@admin_bp.route("/bulk-requests", methods=["GET", "POST"])
def bulk_requests():
    if request.method == "POST":
        req = db.session.get(BulkOrderRequest, request.form.get("request_id", type=int))
        if req:
            req.status = request.form.get("status", req.status)
            req.admin_note = request.form.get("admin_note")
            db.session.commit()
            flash("Bulk request updated.", "success")
        return redirect(url_for("admin.bulk_requests"))
    items = BulkOrderRequest.query.order_by(BulkOrderRequest.created_at.desc()).all()
    return render_template("admin/bulk_requests.html", requests=items)


@admin_bp.route("/support-tickets", methods=["GET", "POST"])
def support_tickets():
    if request.method == "POST":
        ticket = db.session.get(SupportTicket, request.form.get("ticket_id", type=int))
        if ticket:
            ticket.admin_reply = request.form.get("admin_reply")
            ticket.status = "RESOLVED" if request.form.get("resolve") else "OPEN"
            db.session.commit()
            notify(ticket.user_id, "Support reply", "Our team has responded to your support ticket.", "SUPPORT")
            flash("Reply sent.", "success")
        return redirect(url_for("admin.support_tickets"))
    items = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template("admin/support_tickets.html", tickets=items)


@admin_bp.route("/enquiries")
def enquiries():
    items = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    ContactMessage.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("admin/enquiries.html", messages=items)


# ---------------------------------------------------------------- banners
@admin_bp.route("/banners", methods=["GET", "POST"])
def banners():
    form = BannerForm()
    if form.validate_on_submit():
        if not form.image.data:
            flash("Please upload a banner image.", "danger")
        else:
            banner = Banner(title=form.title.data, subtitle=form.subtitle.data, link=form.link.data,
                            cta_label=form.cta_label.data, sort_order=form.sort_order.data or 0,
                            active=form.active.data, image=save_upload(form.image.data, "banners"))
            db.session.add(banner)
            db.session.commit()
            flash("Banner added.", "success")
            return redirect(url_for("admin.banners"))
    items = Banner.query.order_by(Banner.sort_order).all()
    return render_template("admin/banners.html", form=form, banners=items)


@admin_bp.route("/banners/<int:banner_id>/toggle", methods=["POST"])
def toggle_banner(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    banner.active = not banner.active
    db.session.commit()
    flash("Banner visibility updated.", "info")
    return redirect(url_for("admin.banners"))


@admin_bp.route("/banners/<int:banner_id>/delete", methods=["POST"])
def delete_banner(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    db.session.delete(banner)
    db.session.commit()
    flash("Banner deleted.", "info")
    return redirect(url_for("admin.banners"))


# ---------------------------------------------------------------- notifications / audit / reports / settings
@admin_bp.route("/notifications")
def notifications():
    items = current_user.notifications.order_by(Notification.created_at.desc()).limit(100).all()
    return render_template("admin/notifications.html", items=items)


@admin_bp.route("/audit-logs")
def audit_logs():
    page = request.args.get("page", 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template("admin/audit_logs.html", pagination=pagination, logs=pagination.items)


@admin_bp.route("/reports")
def reports():
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    query = Order.query.filter(Order.order_status != OrderStatus.CANCELLED)
    if from_date:
        query = query.filter(Order.created_at >= from_date)
    if to_date:
        query = query.filter(Order.created_at <= to_date + " 23:59:59")
    orders = query.order_by(Order.created_at.desc()).all()
    total = sum((D(o.total_amount) for o in orders), start=D(0))
    return render_template("admin/reports.html", orders=orders, total=total, from_date=from_date, to_date=to_date)


@admin_bp.route("/reports/export")
def reports_export():
    orders = Order.query.filter(Order.order_status != OrderStatus.CANCELLED).order_by(Order.created_at.desc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Order Number", "Date", "Customer", "Tier", "Status", "Payment Status", "Total"])
    for o in orders:
        writer.writerow([o.order_number, o.created_at.strftime("%Y-%m-%d"), o.customer_name, o.price_tier,
                         o.order_status, o.payment_status, str(o.total_amount)])
    log_action("REPORT_EXPORTED", "Order")
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=maagi-sales-report.csv"})


@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        for key, value in request.form.items():
            setting = db.session.get(Setting, key)
            if setting:
                setting.value = value
            else:
                db.session.add(Setting(key=key, value=value))
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    items = {s.key: s.value for s in Setting.query.all()}
    return render_template("admin/settings.html", settings=items)
