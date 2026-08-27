"""后端接口冒烟测试。

覆盖健康检查、识别占位、知识库查询、历史记录接口，
确保骨架可运行（对应 PRD Q2 质量基线）。
"""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """健康检查应返回 200 与 ok 状态。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_recognize_placeholder(client: TestClient) -> None:
    """识别接口当前为占位实现，应返回 501。"""
    resp = client.post("/api/recognize")
    assert resp.status_code == 501


def test_list_herbs_empty(client: TestClient) -> None:
    """空库时药材列表应返回 200 与空列表。"""
    resp = client.get("/api/herbs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_herb_not_found(client: TestClient) -> None:
    """查询不存在的药材应返回 404。"""
    resp = client.get("/api/herbs/999999")
    assert resp.status_code == 404


def test_list_history_empty(client: TestClient) -> None:
    """历史记录接口当前返回空列表。"""
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json() == []
