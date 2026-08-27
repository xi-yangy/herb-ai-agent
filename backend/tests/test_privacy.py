"""隐私授权接口测试。

覆盖授权状态读写、非法类型校验，对应 PRD F11 首次授权与隐私说明。
"""

from fastapi.testclient import TestClient

DEVICE = "privacy-device-001"


def test_consents_empty_without_device(client: TestClient) -> None:
    """无设备标识时返回空列表。"""
    resp = client.get("/api/privacy/consents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_update_and_list_consent(client: TestClient) -> None:
    """更新授权后可查询到对应状态。"""
    headers = {"X-Device-Id": DEVICE}
    put = client.put(
        "/api/privacy/consents", json={"consent_type": "camera", "granted": True}, headers=headers
    )
    assert put.status_code == 200
    assert put.json()["granted"] is True

    items = client.get("/api/privacy/consents", headers=headers)
    assert items.status_code == 200
    assert any(c["consent_type"] == "camera" and c["granted"] for c in items.json())


def test_update_consent_idempotent(client: TestClient) -> None:
    """重复更新同一授权不产生重复记录。"""
    headers = {"X-Device-Id": DEVICE}
    for _ in range(2):
        client.put(
            "/api/privacy/consents",
            json={"consent_type": "album", "granted": True},
            headers=headers,
        )
    items = client.get("/api/privacy/consents", headers=headers).json()
    albums = [c for c in items if c["consent_type"] == "album"]
    assert len(albums) == 1


def test_update_invalid_type(client: TestClient) -> None:
    """不支持的授权类型返回 422。"""
    resp = client.put(
        "/api/privacy/consents",
        json={"consent_type": "location", "granted": True},
        headers={"X-Device-Id": DEVICE},
    )
    assert resp.status_code == 422


def test_update_requires_device(client: TestClient) -> None:
    """缺少设备标识时更新返回 400。"""
    resp = client.put("/api/privacy/consents", json={"consent_type": "camera", "granted": True})
    assert resp.status_code == 400
