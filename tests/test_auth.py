async def test_register_creates_user(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "pwd12345"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert body["scheduler_enabled"] is False
    assert isinstance(body["user_id"], int)


async def test_register_duplicate_email_409(client):
    payload = {"email": "dup@example.com", "password": "pwd12345"}
    r1 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200
    r2 = await client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409


async def test_login_success(client):
    await client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "secret"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "login@example.com"


async def test_login_wrong_password_401(client):
    await client.post(
        "/api/auth/register",
        json={"email": "wp@example.com", "password": "right"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "wp@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_missing_user_401(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "any"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 401


async def test_me_returns_user_after_login(user_client):
    resp = await user_client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"


async def test_logout_clears_session(user_client):
    r1 = await user_client.post("/api/auth/logout")
    assert r1.status_code == 204
    r2 = await user_client.get("/api/me")
    assert r2.status_code == 401
