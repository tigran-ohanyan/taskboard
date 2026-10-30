def test_register_login_me(client):
    r = client.post(
        "/api/auth/register", json={"email": "Ann@Example.com", "password": "secret123"}
    )
    assert r.status_code == 201
    assert r.json()["email"] == "ann@example.com"

    r = client.post("/api/auth/login", json={"email": "ann@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "ann@example.com"


def test_duplicate_email_and_wrong_password(client):
    client.post("/api/auth/register", json={"email": "a@b.co", "password": "secret123"})
    assert (
        client.post("/api/auth/register", json={"email": "a@b.co", "password": "x" * 8}).status_code
        == 409
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "a@b.co", "password": "nope-nope"}
        ).status_code
        == 401
    )


def test_short_password_rejected(client):
    assert (
        client.post("/api/auth/register", json={"email": "a@b.co", "password": "short"}).status_code
        == 422
    )


def test_protected_routes_need_token(client):
    assert client.get("/api/boards").status_code == 401
    bad = {"Authorization": "Bearer garbage"}
    assert client.get("/api/boards", headers=bad).status_code == 401
