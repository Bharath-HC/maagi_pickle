import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Category, Product, ProductVariant, Role, User


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        _seed_minimal()
        yield app
        _db.session.remove()
        _db.drop_all()


def _seed_minimal():
    cat = Category(name="Specialty Pickles", slug="specialty-pickles", active=True)
    _db.session.add(cat)
    _db.session.flush()

    product = Product(name="Dry Fruit Pickle", slug="dry-fruit-pickle", category_id=cat.id,
                      sku="MAAGI-DFP", gst_percentage=12, minimum_order_quantity=10,
                      featured=True, active=True)
    _db.session.add(product)
    _db.session.flush()
    _db.session.add(ProductVariant(product_id=product.id, weight=200, unit="g", sku="MAAGI-DFP-200G",
                                   mrp=180, customer_price=160, wholesaler_price=140, distributor_price=130,
                                   stock_quantity=50, min_stock_level=5, active=True))
    product.sync_stock()

    for email, role, name in [
        ("admin@maagi.local", Role.ADMIN, "Admin"),
        ("distributor@maagi.local", Role.DISTRIBUTOR, "Distro"),
        ("wholesaler@maagi.local", Role.WHOLESALER, "Whole"),
        ("customer@maagi.local", Role.CUSTOMER, "Cust"),
    ]:
        u = User(email=email, name=name, phone=f"90000000{role[0]}", role=role, is_active=True)
        u.set_password("Maagi@12345")
        _db.session.add(u)
    _db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, role):
    return client.post("/login", data={"identifier": email, "password": "Maagi@12345", "login_as": role},
                       follow_redirects=False)
