"""Integration tests for the passwordless OTP auth flow."""
BASE = "/api/v1/auth"
EMAIL = "alice@example.com"
NAME = "Alice Tester"


async def _register(client, email=EMAIL, full_name=NAME):
    return await client.post(
        f"{BASE}/register", json={"email": email, "full_name": full_name}
    )


async def _signup_and_get_tokens(client, otp_box, email=EMAIL):
    await _register(client, email=email)
    code = otp_box[email]
    r = await client.post(f"{BASE}/verify", json={"email": email, "code": code})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- register ----------
async def test_register_sends_otp(client, otp_box):
    r = await _register(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == EMAIL
    assert body["expires_in"] > 0
    assert EMAIL in otp_box  # an OTP was issued


async def test_register_invalid_email(client, otp_box):
    r = await _register(client, email="not-an-email")
    assert r.status_code == 422


async def test_register_existing_verified_conflict(client, otp_box):
    await _signup_and_get_tokens(client, otp_box)
    r = await _register(client)
    assert r.status_code == 409


# ---------- verify ----------
async def test_verify_success_returns_tokens(client, otp_box):
    body = await _signup_and_get_tokens(client, otp_box)
    assert body["user"]["email"] == EMAIL
    assert body["user"]["is_verified"] is True
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]


async def test_verify_wrong_code(client, otp_box):
    await _register(client)
    r = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": "000000"})
    assert r.status_code == 400


async def test_verify_consumes_code(client, otp_box):
    await _register(client)
    code = otp_box[EMAIL]
    r1 = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": code})
    assert r1.status_code == 200
    # Same code cannot be reused.
    r2 = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": code})
    assert r2.status_code == 400


async def test_verify_no_request(client, otp_box):
    r = await client.post(
        f"{BASE}/verify", json={"email": "nobody@example.com", "code": "123456"}
    )
    assert r.status_code == 400


# ---------- login ----------
async def test_login_existing_user_sends_otp(client, otp_box):
    await _signup_and_get_tokens(client, otp_box)
    r = await client.post(f"{BASE}/login", json={"email": EMAIL})
    assert r.status_code == 200
    # New login code issued.
    code = otp_box[EMAIL]
    v = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": code})
    assert v.status_code == 200
    assert v.json()["tokens"]["access_token"]


async def test_login_unknown_user(client, otp_box):
    r = await client.post(f"{BASE}/login", json={"email": "ghost@example.com"})
    assert r.status_code == 404


# ---------- resend ----------
async def test_resend_issues_new_code(client, otp_box):
    await _register(client)
    first = otp_box[EMAIL]
    r = await client.post(f"{BASE}/resend", json={"email": EMAIL})
    assert r.status_code == 200
    second = otp_box[EMAIL]
    assert second != first
    # Old code is now invalid; new one works.
    bad = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": first})
    assert bad.status_code == 400
    ok = await client.post(f"{BASE}/verify", json={"email": EMAIL, "code": second})
    assert ok.status_code == 200


# ---------- me ----------
async def test_me_with_token(client, otp_box):
    body = await _signup_and_get_tokens(client, otp_box)
    token = body["tokens"]["access_token"]
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


async def test_me_without_token(client, otp_box):
    r = await client.get(f"{BASE}/me")
    assert r.status_code in (401, 403)


# ---------- refresh / logout ----------
async def test_refresh_rotates(client, otp_box):
    body = await _signup_and_get_tokens(client, otp_box)
    old = body["tokens"]["refresh_token"]
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    again = await client.post(f"{BASE}/refresh", json={"refresh_token": old})
    assert again.status_code == 401


async def test_logout_revokes(client, otp_box):
    body = await _signup_and_get_tokens(client, otp_box)
    refresh = body["tokens"]["refresh_token"]
    out = await client.post(f"{BASE}/logout", json={"refresh_token": refresh})
    assert out.status_code == 200
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


# ---------- health ----------
async def test_health(client, otp_box):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
