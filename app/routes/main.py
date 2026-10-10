from datetime import datetime

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import BulkOrderForm, ContactForm, NewsletterForm, B2BApplicationForm
from ..models import (BulkOrderItem, BulkOrderRequest, Category, ContactMessage, DistributorApplication,
                      NewsletterSubscriber, Product, ProductVariant, Role, WholesalerApplication)
from ..services.audit_service import log_action
from ..services.notification_service import notify_admins
from ..utils.helpers import bulk_reference

main_bp = Blueprint("main", __name__, url_prefix="")


@main_bp.route("/")
def home():
    featured = Product.query.filter_by(active=True, featured=True).limit(8).all()
    categories = Category.query.filter_by(active=True).order_by(Category.sort_order).all()
    from ..models import Banner
    banners = Banner.query.filter_by(active=True).order_by(Banner.sort_order).all()
    return render_template("main/home.html", featured=featured, categories=categories, banners=banners)


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(name=form.name.data, email=form.email.data, phone=form.phone.data,
                             subject=form.subject.data, message=form.message.data)
        db.session.add(msg)
        db.session.commit()
        notify_admins("New contact enquiry", f"{form.name.data}: {form.subject.data}", "/admin/enquiries")
        flash("Thanks for reaching out — our team will get back to you shortly.", "success")
        return redirect(url_for("main.contact"))
    return render_template("main/contact.html", form=form)


@main_bp.route("/bulk-orders", methods=["GET", "POST"])
def bulk_orders():
    form = BulkOrderForm()
    products = Product.query.filter_by(active=True).all()
    if form.validate_on_submit():
        selected = []
        for key, value in request.form.items():
            if key.startswith("qty_") and value and int(value) > 0:
                variant_id = int(key.replace("qty_", ""))
                variant = db.session.get(ProductVariant, variant_id)
                if variant:
                    selected.append((variant, int(value)))
        if not selected:
            flash("Please select at least one product and quantity.", "warning")
            return render_template("main/bulk_orders.html", form=form, products=products)
        req = BulkOrderRequest(
            reference=bulk_reference(), user_id=current_user.id if current_user.is_authenticated else None,
            name=form.name.data, company_name=form.company_name.data, email=form.email.data,
            phone=form.phone.data, gst_number=form.gst_number.data, delivery_address=form.delivery_address.data,
            expected_delivery_date=form.expected_delivery_date.data, message=form.message.data,
        )
        db.session.add(req)
        db.session.flush()
        for variant, qty in selected:
            db.session.add(BulkOrderItem(request_id=req.id, variant_id=variant.id, quantity=qty))
        db.session.commit()
        notify_admins("New bulk quote request", f"{req.reference} from {req.name}", "/admin/bulk-requests")
        flash(f"Your bulk quote request ({req.reference}) has been submitted. Our team will contact you soon.", "success")
        return redirect(url_for("main.bulk_orders"))
    return render_template("main/bulk_orders.html", form=form, products=products)


@main_bp.route("/become-a-distributor", methods=["GET", "POST"], endpoint="become_distributor")
@main_bp.route("/become-a-wholesaler", methods=["GET", "POST"], endpoint="become_wholesaler")
@login_required
def become_partner():
    target_role = Role.DISTRIBUTOR if request.endpoint.endswith("distributor") else Role.WHOLESALER
    model = DistributorApplication if target_role == Role.DISTRIBUTOR else WholesalerApplication

    if current_user.role != Role.CUSTOMER:
        flash("Only retail customer accounts can submit a new business application.", "info")
        return redirect(url_for(current_user.dashboard_endpoint))

    existing = model.query.filter_by(user_id=current_user.id, status="PENDING").first()
    form = B2BApplicationForm(role=target_role)
    if existing:
        return render_template("main/become_partner.html", form=form, target_role=target_role, existing=existing)

    if form.validate_on_submit():
        app_row = model(
            user_id=current_user.id, name=form.name.data, company_name=form.company_name.data,
            phone=form.phone.data, email=form.email.data, address=form.address.data, city=form.city.data,
            state=form.state.data, pincode=form.pincode.data, gst_number=form.gst_number.data,
            business_type=form.business_type.data, expected_monthly_purchase=form.expected_monthly_purchase.data,
        )
        db.session.add(app_row)
        db.session.commit()
        notify_admins(f"New {target_role.title()} application", f"{form.name.data} ({form.company_name.data})",
                     f"/admin/{'distributors' if target_role == Role.DISTRIBUTOR else 'wholesalers'}")
        log_action(f"{target_role}_APPLICATION_SUBMITTED", "User", current_user.id)
        flash("Your application has been submitted. Our business team will review it shortly.", "success")
        return redirect(url_for(current_user.dashboard_endpoint))
    return render_template("main/become_partner.html", form=form, target_role=target_role, existing=None)


@main_bp.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    form = NewsletterForm()
    if form.validate_on_submit():
        if not NewsletterSubscriber.query.filter_by(email=form.email.data.lower()).first():
            db.session.add(NewsletterSubscriber(email=form.email.data.lower()))
            db.session.commit()
        flash("You're subscribed to Maagi updates!", "success")
    else:
        flash("Please enter a valid email address.", "danger")
    return redirect(request.referrer or url_for("main.home"))


@main_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    page = request.args.get("page", 1, type=int)
    query = Product.query.filter_by(active=True)
    if q:
        like = f"%{q}%"
        query = query.join(Category, isouter=True).filter(
            db.or_(Product.name.ilike(like), Product.sku.ilike(like), Product.short_description.ilike(like),
                  Category.name.ilike(like)))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    pagination = query.order_by(Product.featured.desc(), Product.name).paginate(
        page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
    categories = Category.query.filter_by(active=True).all()
    return render_template("main/search.html", q=q, pagination=pagination, products=pagination.items,
                          categories=categories, category_id=category_id)


@main_bp.route("/robots.txt")
def robots():
    lines = ["User-agent: *", "Allow: /", f"Sitemap: {current_app.config['SITE_URL']}/sitemap.xml"]
    return Response("\n".join(lines), mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap():
    base = current_app.config["SITE_URL"]
    urls = [base + "/", base + "/about", base + "/contact", base + "/bulk-orders"]
    for p in Product.query.filter_by(active=True).all():
        urls.append(f"{base}/products/{p.slug}")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("main/legal.html", section="privacy")


@main_bp.route("/terms-and-conditions")
def terms():
    return render_template("main/legal.html", section="terms")


@main_bp.route("/shipping-policy")
def shipping_policy():
    return render_template("main/legal.html", section="shipping")


@main_bp.route("/refund-policy")
def refund_policy():
    return render_template("main/legal.html", section="refund")
