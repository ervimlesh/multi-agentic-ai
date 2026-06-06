"""Integration tests for the full auth flow."""
BASE = "/api/v1/auth"
REG = {
    "email": "alice@example.com",
    "password": "supersecret123",
    "full_name": "Alice Tester",
}


async def _register(client, **overrides):
    payload = {**REG, **overrides}
    return await client.post(f"{BASE}/register", json=payload)


# ---------- register ----------
async def test_register_success(client):
    r = await _register(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == REG["email"]
    assert body["user"]["full_name"] == REG["full_name"]
    assert "hashed_password" not in body["user"]
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["token_type"] == "bearer"


async def test_register_duplicate_email(client):
    await _register(client)
    r = await _register(client)
    assert r.status_code == 409


async def test_register_invalid_email(client):
    r = await _register(client, email="not-an-email")
    assert r.status_code == 422


async def test_register_short_password(client):
    r = await _register(client, password="short")
    assert r.status_code == 422


# ---------- login ----------
async def test_login_success(client):
    await _register(client)
    r = await client.post(
        f"{BASE}/login", json={"email": REG["email"], "password": REG["password"]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["tokens"]["access_token"]


async def test_login_wrong_password(client):
    await _register(client)
    r = await client.post(
        f"{BASE}/login", json={"email": REG["email"], "password": "wrongpass"}
    )
    assert r.status_code == 401


async def test_login_unknown_user(client):
    r = await client.post(
        f"{BASE}/login", json={"email": "ghost@example.com", "password": "whatever1"}
    )
    assert r.status_code == 401


# ---------- me ----------
async def test_me_with_token(client):
    reg = await _register(client)
    token = reg.json()["tokens"]["access_token"]
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == REG["email"]


async def test_me_without_token(client):
    r = await client.get(f"{BASE}/me")
    assert r.status_code in (401, 403)


async def test_me_bad_token(client):
    r = await client.get(
        f"{BASE}/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert r.status_code == 401


# ---------- refresh ----------
async def test_refresh_rotates_tokens(client):
    reg = await _register(client)
    old_refresh = reg.json()["tokens"]["refresh_token"]
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new_tokens = r.json()
    assert new_tokens["access_token"]
    # Old refresh token is now revoked (rotation).
    again = await client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
    assert again.status_code == 401


async def test_refresh_invalid_token(client):
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


# ---------- logout ----------
async def test_logout_revokes_refresh(client):
    reg = await _register(client)
    refresh = reg.json()["tokens"]["refresh_token"]
    out = await client.post(f"{BASE}/logout", json={"refresh_token": refresh})
    assert out.status_code == 200
    # The refresh token no longer works.
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


# ---------- health ----------
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
