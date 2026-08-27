"""P0 核心主链路冒烟测试。

覆盖「识别 → 知识库详情 → 识别历史 → 收藏增删查」全链路，
对应 PRD Q2 质量基线与 F 系列功能验收的工程可运行性验证。
"""

from fastapi.testclient import TestClient

# 独立的匿名设备标识，避免污染其他演示数据
DEVICE = "test-device-001"


def test_recognize_and_fetch_detail(client: TestClient) -> None:
    """识别返回药材，随后可查询其完整知识详情。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["herb"] is not None
    herb_id = data["herb"]["id"]
    # 安全等级与红线字段必须存在
    assert data["safety_level"] in {"普通", "慎用", "毒性"}
    detail = client.get(f"/api/herbs/{herb_id}")
    assert detail.status_code == 200
    d = detail.json()
    for field in ("nature_flavor", "effects", "usage", "contraindications", "toxicity"):
        assert field in d


def test_history_write_and_list(client: TestClient) -> None:
    """识别历史可写入并可查询。"""
    create = client.post(
        "/api/history",
        json={
            "result_name": "附子",
            "confidence": 0.97,
            "channel": "mock",
            "device_id": DEVICE,
        },
        headers={"X-Device-Id": DEVICE},
    )
    assert create.status_code == 200
    created = create.json()
    assert created["result_name"] == "附子"

    items = client.get("/api/history", headers={"X-Device-Id": DEVICE})
    assert items.status_code == 200
    names = [h["result_name"] for h in items.json()]
    assert "附子" in names


def test_favorite_add_list_remove(client: TestClient) -> None:
    """收藏可新增、查询并可取消。"""
    # 找到示例药材 id
    herbs = client.get("/api/herbs").json()
    herb_id = herbs[0]["id"]

    add = client.post("/api/favorites", json={"herb_id": herb_id}, headers={"X-Device-Id": DEVICE})
    assert add.status_code == 200

    favs = client.get("/api/favorites", headers={"X-Device-Id": DEVICE})
    assert favs.status_code == 200
    assert any(f["herb_id"] == herb_id for f in favs.json())

    rm = client.delete(f"/api/favorites/{herb_id}", headers={"X-Device-Id": DEVICE})
    assert rm.status_code == 200

    after = client.get("/api/favorites", headers={"X-Device-Id": DEVICE})
    assert not any(f["herb_id"] == herb_id for f in after.json())


def test_recognize_safety_level(client: TestClient) -> None:
    """mock 识别默认命中示例毒性药材附子，应返回毒性警示。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "album"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "附子"
    assert data["safety_level"] == "毒性"
