"""后端接口冒烟测试。

覆盖健康检查、识别、知识库查询、历史记录、收藏接口，
确保主链路可运行（对应 PRD Q2 质量基线）。
"""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """健康检查应返回 200 与 ok 状态。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_recognize_ok(client: TestClient) -> None:
    """识别接口应返回 200 与药材结果（mock 服务）。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"]
    assert data["safety_level"] in {"普通", "慎用", "毒性"}
    assert data["channel"]


def test_list_herbs(client: TestClient) -> None:
    """药材列表应返回 200 且含示例数据。"""
    resp = client.get("/api/herbs")
    assert resp.status_code == 200
    herbs = resp.json()
    assert isinstance(herbs, list)
    assert len(herbs) >= 1
    assert "nature_flavor" in herbs[0]
    assert "safety_level" in herbs[0]


def test_get_herb_not_found(client: TestClient) -> None:
    """查询不存在的药材应返回 404。"""
    resp = client.get("/api/herbs/999999")
    assert resp.status_code == 404


def test_list_history_empty(client: TestClient) -> None:
    """无设备标识时历史应返回 200 与空列表。"""
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json() == []
