from app.models import Role, User

from .conftest import login


def test_register_creates_customer(client, app):
    resp = client.post("/register", data={
        "name": "New User", "email": "newuser@maagi.local", "phone": "9123456789",
        "password": "StrongPass1", "confirm_password": "StrongPass1", "agree": "y",
    }, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        u = User.query.filter_by(email="newuser@maagi.local").first()
        assert u is not None
        assert u.role == Role.CUSTOMER


def test_login_wrong_role_rejected(client):
    resp = client.post("/login", data={
        "identifier": "customer@maagi.local", "password": "Maagi@12345", "login_as": "ADMIN",
    }, follow_redirects=True)
    assert b"not registered as a Admin" in resp.data or b"not registered as a" in resp.data


def test_login_each_role_redirects_to_own_dashboard(client):
    cases = [
        ("admin@maagi.local", Role.ADMIN, "/admin/dashboard"),
        ("distributor@maagi.local", Role.DISTRIBUTOR, "/distributor/dashboard"),
        ("wholesaler@maagi.local", Role.WHOLESALER, "/wholesaler/dashboard"),
        ("customer@maagi.local", Role.CUSTOMER, "/customer/dashboard"),
    ]
    for email, role, expected_path in cases:
        resp = login(client, email, role)
        assert resp.status_code == 302
        assert resp.headers["Location"] == expected_path
        dash = client.get(expected_path)
        assert dash.status_code == 200
        client.get("/logout")


def test_logout_requires_login(client):
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code in (302, 401)
