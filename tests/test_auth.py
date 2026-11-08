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


def test_b2b_portals_hidden_when_disabled(app, client):
    """With B2B_ENABLED off, distributor/wholesaler logins and application pages are closed."""
    app.config["B2B_ENABLED"] = False
    for email, role in (("distributor@maagi.local", Role.DISTRIBUTOR), ("wholesaler@maagi.local", Role.WHOLESALER)):
        resp = client.post("/login", data={"identifier": email, "password": "Maagi@12345", "login_as": role},
                           follow_redirects=True)
        assert b"not available right now" in resp.data
        assert client.get("/distributor/dashboard").status_code in (404, 401, 403)
    assert client.get("/become-a-distributor").status_code in (404, 302, 401)
    page = client.get("/login").data
    assert b"Wholesaler" not in page and b"Distributor" not in page
    # customer + admin still work
    assert login(client, "customer@maagi.local", "CUSTOMER").status_code == 302
    client.get("/logout")
    assert login(client, "admin@maagi.local", "ADMIN").status_code == 302
