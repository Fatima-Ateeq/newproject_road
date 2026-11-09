from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def test_login_returns_a_bearer_token(admin_headers):
    assert admin_headers["Authorization"].startswith("Bearer ")


def test_wrong_password_is_rejected(client, admin_headers):
    response = client.post("/api/admin/login", json={"username": ADMIN_USERNAME, "password": "wrong-password"})
    assert response.status_code == 401


def test_unknown_user_is_rejected_with_the_same_message(client, admin_headers):
    wrong_password = client.post("/api/admin/login", json={"username": ADMIN_USERNAME, "password": "nope"})
    unknown_user = client.post("/api/admin/login", json={"username": "ghost", "password": ADMIN_PASSWORD})
    assert unknown_user.status_code == 401
    assert unknown_user.json() == wrong_password.json()


def test_admin_endpoints_require_a_token(client):
    assert client.get("/api/admin/complaints").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/admin/complaints", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
