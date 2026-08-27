"""认证接口测试。

覆盖注册、登录、重复注册、错误密码、token 校验与鉴权依赖，
对应 PRD Q2 质量基线与 F10 注册登录验收。
"""

from fastapi.testclient import TestClient


def test_register_success(client: TestClient) -> None:
    """注册成功返回 token 与用户信息。"""
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "secret123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"]
    assert data["user"]["username"] == "alice"


def test_register_duplicate(client: TestClient) -> None:
    """重复注册同一用户名返回 409。"""
    payload = {"username": "bob", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    dup = client.post("/api/auth/register", json=payload)
    assert dup.status_code == 409


def test_login_success(client: TestClient) -> None:
    """正确密码登录返回 token。"""
    client.post("/api/auth/register", json={"username": "carol", "password": "secret123"})
    resp = client.post("/api/auth/login", json={"username": "carol", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_login_wrong_password(client: TestClient) -> None:
    """错误密码登录返回 401。"""
    client.post("/api/auth/register", json={"username": "dave", "password": "secret123"})
    resp = client.post("/api/auth/login", json={"username": "dave", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_nonexistent_user(client: TestClient) -> None:
    """不存在的用户名登录返回 401。"""
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "secret123"})
    assert resp.status_code == 401


def test_me_with_valid_token(client: TestClient) -> None:
    """携带合法 token 访问 /me 返回用户信息。"""
    reg = client.post(
        "/api/auth/register", json={"username": "erin", "password": "secret123"}
    ).json()
    token = reg["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "erin"


def test_me_without_token(client: TestClient) -> None:
    """未携带 token 访问 /me 返回 401。"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token(client: TestClient) -> None:
    """携带伪造 token 访问 /me 返回 401。"""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token"})
    assert resp.status_code == 401
