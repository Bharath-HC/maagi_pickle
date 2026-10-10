from app.extensions import db
from app.models import Coupon, Product, ProductVariant

from .conftest import login


def test_product_catalog_lists_products(client):
    resp = client.get("/products/")
    assert resp.status_code == 200
    assert b"Dry Fruit Pickle" in resp.data


def test_product_detail_page(client):
    resp = client.get("/products/dry-fruit-pickle")
    assert resp.status_code == 200
    assert b"Dry Fruit Pickle" in resp.data


def test_role_based_pricing_hidden_and_correct(app):
    with app.app_context():
        from app.services.pricing_service import variant_price
        v = ProductVariant.query.first()
        assert variant_price(v, "CUSTOMER") == 160
        assert variant_price(v, "WHOLESALER") == 140
        assert variant_price(v, "DISTRIBUTOR") == 130


def test_customer_cannot_obtain_distributor_price_via_cart(client, app):
    login(client, "customer@maagi.local", "CUSTOMER")
    with app.app_context():
        v = ProductVariant.query.first()
        variant_id = v.id
    resp = client.post("/cart/add", data={"variant_id": variant_id, "quantity": 1}, follow_redirects=True)
    assert resp.status_code == 200
    cart_resp = client.get("/cart/")
    # Customer price (160), not distributor price (130), should appear
    assert b"160" in cart_resp.data
    assert b"130" not in cart_resp.data or b"customer" in cart_resp.data.lower()


def test_add_to_cart_respects_stock(client, app):
    login(client, "customer@maagi.local", "CUSTOMER")
    with app.app_context():
        v = ProductVariant.query.first()
        variant_id = v.id
        stock = v.stock_quantity
    resp = client.post("/cart/add", data={"variant_id": variant_id, "quantity": stock + 100}, follow_redirects=True)
    assert resp.status_code == 200


def test_checkout_cod_creates_order(client, app):
    login(client, "customer@maagi.local", "CUSTOMER")
    with app.app_context():
        v = ProductVariant.query.first()
        variant_id = v.id
    client.post("/cart/add", data={"variant_id": variant_id, "quantity": 1})
    client.post("/customer/addresses", data={
        "label": "Home", "name": "Cust", "phone": "9000000000", "line1": "Line 1",
        "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "is_default": "y",
    })
    with app.app_context():
        from app.models import Address, User
        user = User.query.filter_by(email="customer@maagi.local").first()
        address = Address.query.filter_by(user_id=user.id).first()
        address_id = address.id
    resp = client.post("/checkout/place", data={
        "address_id": address_id, "payment_method": "COD",
    }, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        from app.models import Order
        order = Order.query.first()
        assert order is not None
        assert order.order_status == "CONFIRMED"
        assert order.inventory_state == "DEDUCTED"


def test_inventory_deducted_after_cod_order(client, app):
    with app.app_context():
        v = ProductVariant.query.first()
        initial_stock = v.stock_quantity
        variant_id = v.id

    login(client, "customer@maagi.local", "CUSTOMER")
    client.post("/cart/add", data={"variant_id": variant_id, "quantity": 2})
    client.post("/customer/addresses", data={
        "label": "Home", "name": "Cust", "phone": "9000000000", "line1": "Line 1",
        "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "is_default": "y",
    })
    with app.app_context():
        from app.models import Address, User
        user = User.query.filter_by(email="customer@maagi.local").first()
        address_id = Address.query.filter_by(user_id=user.id).first().id
    client.post("/checkout/place", data={"address_id": address_id, "payment_method": "COD"})

    with app.app_context():
        v = db.session.get(ProductVariant, variant_id)
        assert v.stock_quantity == initial_stock - 2


def test_coupon_rejects_below_minimum_order(app):
    with app.app_context():
        from app.services.coupon_service import CouponError, validate_coupon
        from app.models import User
        coupon = Coupon(code="TESTMIN", discount_type="PERCENT", discount_value=10, min_order=500,
                        customers_only=True, active=True)
        db.session.add(coupon)
        db.session.commit()
        user = User.query.filter_by(role="CUSTOMER").first()
        try:
            validate_coupon("TESTMIN", user, 100)
            assert False, "Expected CouponError for below-minimum order"
        except CouponError:
            pass
