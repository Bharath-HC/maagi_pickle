from .conftest import login


def test_customer_cannot_access_admin_dashboard(client):
    login(client, "customer@maagi.local", "CUSTOMER")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_customer_cannot_access_distributor_dashboard(client):
    login(client, "customer@maagi.local", "CUSTOMER")
    resp = client.get("/distributor/dashboard")
    assert resp.status_code == 403


def test_wholesaler_cannot_access_distributor_dashboard(client):
    login(client, "wholesaler@maagi.local", "WHOLESALER")
    resp = client.get("/distributor/dashboard")
    assert resp.status_code == 403


def test_admin_dashboard_requires_login(client):
    resp = client.get("/admin/dashboard")
    assert resp.status_code in (302, 401)


def test_admin_can_access_own_dashboard(client):
    login(client, "admin@maagi.local", "ADMIN")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
