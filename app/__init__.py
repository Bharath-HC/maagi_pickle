import os

from flask import Flask, render_template, request

from .config import CONFIGS
from .extensions import csrf, db, login_manager, migrate


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS.get(config_name, CONFIGS["development"]))
    if hasattr(CONFIGS.get(config_name), "validate"):
        CONFIGS[config_name].validate()

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"
    csrf.init_app(app)

    from . import models  # noqa: F401 register models with SQLAlchemy metadata

    register_blueprints(app)
    register_error_handlers(app)
    register_template_helpers(app)
    register_cli(app)

    return app


def register_blueprints(app):
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.b2b import b2b_bp
    from .routes.cart import cart_bp
    from .routes.checkout import checkout_bp
    from .routes.customer import customer_bp
    from .routes.main import main_bp
    from .routes.products import products_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(b2b_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)


def register_error_handlers(app):
    from .extensions import db

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/403.html", message="Please log in to access this page."), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", message=None), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/403.html", message="The file you uploaded is too large."), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def register_template_helpers(app):
    from .models import Category, Role
    from .services.pricing_service import variant_price
    from .utils.helpers import rupees

    app.jinja_env.filters["rupees"] = rupees
    app.jinja_env.globals["variant_price"] = variant_price

    @app.template_filter("dict_minus_page")
    def dict_minus_page(d):
        return {k: v for k, v in d.items() if k != "page"}

    @app.context_processor
    def url_for_page_helper():
        from flask import url_for as _url_for

        def url_for_page(page):
            args = dict(request.view_args or {})
            args.update(request.args.to_dict())
            args["page"] = page
            return _url_for(request.endpoint, **args)

        return {"url_for_page": url_for_page}

    @app.context_processor
    def inject_globals():
        from flask_login import current_user as cu
        cart_count = 0
        if cu.is_authenticated:
            from .services.cart_service import get_or_create_cart
            cart = get_or_create_cart(cu)
            cart_count = sum(i.quantity for i in cart.items)
        return {
            "nav_categories": Category.query.filter_by(active=True).order_by(Category.sort_order).all(),
            "cart_count": cart_count,
            "current_year": __import__("datetime").datetime.utcnow().year,
            "company_name": app.config["COMPANY_NAME"],
            "company_email": app.config["COMPANY_EMAIL"],
            "company_phone": app.config["COMPANY_PHONE"],
            "Role": Role,
            "role": cu.role if cu.is_authenticated else Role.CUSTOMER,
        }


def register_cli(app):
    @app.cli.command("seed")
    def seed_command():
        """Seed the database with demo accounts, products, and sample data."""
        from seed import run_seed
        run_seed(app)
