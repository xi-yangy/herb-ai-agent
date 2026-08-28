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


def test_recognize_returns_anti_deception_warning(client: TestClient) -> None:
    """识别命中配置了防雷字段的药材（附子）时，响应携带鉴别防雷警报。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    # 附子已配置防雷字段，warning 应为非空
    assert data["herb"] is not None
    assert data["warning"]["label"]
    assert data["warning"]["message"]
    assert data["warning"]["herb_name"] == "附子"


def test_recognize_falls_back_to_mock_when_baidu_disabled(client: TestClient) -> None:
    """百度识别未启用时，识别接口回退 Mock 仍返回结果（不中断链路）。"""
    # conftest 已设置 BAIDU_ENABLED=false
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"]  # 有识别名称
    assert data["safety_level"] in {"普通", "慎用", "毒性"}


def test_herb_category_and_similar_fields(client: TestClient) -> None:
    """知识库药材返回新增字段 category 与 similar_herbs。"""
    herbs = client.get("/api/herbs").json()
    assert herbs  # 知识库非空
    sample = herbs[0]
    assert "category" in sample
    assert "similar_herbs" in sample


def test_history_migrate_anonymous_to_user(client: TestClient) -> None:
    """登录后匿名历史合并到用户维度，且以 user_id 读取。"""
    dev = "migrate-dev-001"
    headers = {"X-Device-Id": dev}

    # 匿名写入一条历史
    client.post(
        "/api/history",
        json={"result_name": "黄芪", "confidence": 0.9, "channel": "mock", "herb_id": None},
        headers=headers,
    )
    assert len(client.get("/api/history", headers=headers).json()) == 1

    # 注册并登录
    reg = client.post(
        "/api/auth/register", json={"username": "mig", "password": "secret123"}
    ).json()
    auth = {"Authorization": f"Bearer {reg['token']}", "X-Device-Id": dev}

    # 登录后（未迁移）用户维度应为空
    assert client.get("/api/history", headers=auth).json() == []

    # 迁移
    migrate = client.post("/api/history/migrate", headers=auth)
    assert migrate.status_code == 200
    assert migrate.json()["migrated"] == 1

    # 迁移后用户维度可见，匿名维度不再可见
    assert len(client.get("/api/history", headers=auth).json()) == 1
    assert client.get("/api/history", headers=headers).json() == []


def test_favorite_migrate_anonymous_to_user(client: TestClient) -> None:
    """登录后匿名收藏合并到用户维度（含 herb_id 去重）。"""
    dev = "migrate-dev-002"
    headers = {"X-Device-Id": dev}

    # 匿名收藏一株药材
    herb_id = client.get("/api/herbs").json()[0]["id"]
    client.post("/api/favorites", json={"herb_id": herb_id}, headers=headers)
    assert len(client.get("/api/favorites", headers=headers).json()) == 1

    # 注册登录
    reg = client.post(
        "/api/auth/register", json={"username": "mig2", "password": "secret123"}
    ).json()
    auth = {"Authorization": f"Bearer {reg['token']}", "X-Device-Id": dev}

    migrate = client.post("/api/favorites/migrate", headers=auth)
    assert migrate.status_code == 200
    assert migrate.json()["migrated"] == 1

    # 迁移后用户维度可见，匿名维度清空
    assert len(client.get("/api/favorites", headers=auth).json()) == 1
    assert client.get("/api/favorites", headers=headers).json() == []


def test_migrate_requires_login(client: TestClient) -> None:
    """未登录时调用迁移接口返回 401。"""
    resp = client.post("/api/history/migrate", headers={"X-Device-Id": "some-dev"})
    assert resp.status_code == 401
