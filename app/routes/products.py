from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import ReviewForm
from ..models import Category, Order, OrderItem, OrderStatus, Product, Review
from ..services.audit_service import log_action

products_bp = Blueprint("products", __name__, url_prefix="/products")


@products_bp.route("/")
def catalog():
    category_id = request.args.get("category", type=int)
    sort = request.args.get("sort", "featured")
    page = request.args.get("page", 1, type=int)
    query = Product.query.filter_by(active=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if sort == "name":
        query = query.order_by(Product.name)
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.featured.desc(), Product.name)
    pagination = query.paginate(page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
    categories = Category.query.filter_by(active=True).order_by(Category.sort_order).all()
    return render_template("products/catalog.html", pagination=pagination, products=pagination.items,
                          categories=categories, category_id=category_id, sort=sort)


@products_bp.route("/<slug>")
def detail(slug):
    product = Product.query.filter_by(slug=slug, active=True).first_or_404()
    role = current_user.role if current_user.is_authenticated else "CUSTOMER"
    can_review = False
    if current_user.is_authenticated:
        purchased = db.session.query(OrderItem).join(Order).filter(
            Order.user_id == current_user.id, OrderItem.product_id == product.id,
            Order.order_status == OrderStatus.DELIVERED).first()
        already_reviewed = Review.query.filter_by(product_id=product.id, user_id=current_user.id).first()
        can_review = bool(purchased) and not already_reviewed
    related = Product.query.filter(Product.category_id == product.category_id, Product.id != product.id,
                                   Product.active == True).limit(4).all()  # noqa: E712
    reviews = product.approved_reviews().order_by(Review.created_at.desc()).all()
    review_form = ReviewForm()
    return render_template("products/detail.html", product=product, role=role, can_review=can_review,
                          related=related, reviews=reviews, review_form=review_form)


@products_bp.route("/<slug>/review", methods=["POST"])
@login_required
def submit_review(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    purchased = db.session.query(OrderItem).join(Order).filter(
        Order.user_id == current_user.id, OrderItem.product_id == product.id,
        Order.order_status == OrderStatus.DELIVERED).first()
    if not purchased:
        flash("You can review a product only after it has been delivered to you.", "warning")
        return redirect(url_for("products.detail", slug=slug))
    if Review.query.filter_by(product_id=product.id, user_id=current_user.id).first():
        flash("You have already reviewed this product.", "info")
        return redirect(url_for("products.detail", slug=slug))
    form = ReviewForm()
    if form.validate_on_submit():
        db.session.add(Review(product_id=product.id, user_id=current_user.id, rating=int(form.rating.data),
                              title=form.title.data, body=form.body.data, verified_purchase=True))
        db.session.commit()
        log_action("REVIEW_SUBMITTED", "Product", product.id)
        flash("Thanks for your review!", "success")
    else:
        flash("Please fill in the review form correctly.", "danger")
    return redirect(url_for("products.detail", slug=slug))
