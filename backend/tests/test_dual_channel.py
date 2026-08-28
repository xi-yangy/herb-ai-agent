"""识别兜底与低置信降级测试。

覆盖：
- 百度未启用时识别回退 Mock，channel 语义正确；
- BaiduRecognizer 在百度未配置/禁用时回退 Mock；
- 百度低置信度时返回 similar 相似品种列表并标记 low_confidence；
- 相似品种（similar）构建正确。

通过直接实例化并替换内部方法的方式隔离验证，不依赖真实外网。
对应 PRD Q2「高危判定/降级逻辑单测」要求。
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.recognize import RecognizeResult
from app.services.recognizer import BaiduRecognizer, _build_similar_from_names

# 保证测试环境配置（独立覆盖，避免污染其他用例）
settings.baidu_enabled = False
settings.baidu_api_key = ""
settings.baidu_secret_key = ""


def test_default_falls_back_to_mock(client: TestClient) -> None:
    """百度禁用时，识别接口回退 Mock，channel 为 mock。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "mock"
    assert data["name"]  # Mock 恒定返回附子
    assert data["low_confidence"] is False
    # 响应契约包含相似品种字段
    assert "similar" in data
    assert isinstance(data["similar"], list)


def test_baidu_falls_back_to_mock_when_disabled() -> None:
    """百度未配置凭证/禁用时，BaiduRecognizer 直接回退 Mock（channel=mock）。"""
    rec = BaiduRecognizer()
    settings.baidu_enabled = False
    with SessionLocal() as db:
        result = rec.recognize("fake", db)
    assert result.channel == "mock"
    assert result.name  # Mock 返回附子


def test_baidu_low_confidence_returns_similar() -> None:
    """百度置信度低于阈值时，标记 low_confidence 并返回相似品种列表。"""
    rec = BaiduRecognizer()
    settings.baidu_enabled = True
    settings.baidu_api_key = "dummy"
    settings.baidu_secret_key = "dummy"

    # 打桩内部网络调用：返回 top-k（置信度低于阈值 0.6）
    def fake_call(image_base64):
        return [("黄芪", 0.42), ("甘草", 0.30), ("附子", 0.12)]

    rec._call_baidu = fake_call  # type: ignore[method-assign]

    with SessionLocal() as db:
        result = rec.recognize("fake", db)
    assert result.channel == "baidu"
    assert result.name == "黄芪"
    assert result.low_confidence is True
    assert len(result.similar) == 3
    # 相似品种按置信度降序填充
    assert result.similar[0].name == "黄芪"
    assert result.similar[0].confidence == 0.42

    # 还原
    settings.baidu_enabled = False
    settings.baidu_api_key = ""
    settings.baidu_secret_key = ""


def test_baidu_high_confidence_not_low() -> None:
    """百度置信度高于阈值时，low_confidence 为 False。"""
    rec = BaiduRecognizer()
    settings.baidu_enabled = True
    settings.baidu_api_key = "dummy"
    settings.baidu_secret_key = "dummy"

    def fake_call_high(image_base64):
        return [("附子", 0.92), ("黄芪", 0.05)]

    rec._call_baidu = fake_call_high  # type: ignore[method-assign]

    with SessionLocal() as db:
        result = rec.recognize("fake", db)
    assert result.channel == "baidu"
    assert result.low_confidence is False
    assert result.name == "附子"

    settings.baidu_enabled = False
    settings.baidu_api_key = ""
    settings.baidu_secret_key = ""


def test_build_similar_from_names() -> None:
    """相似品种列表构建应填充知识库安全等级与来源。"""
    with SessionLocal() as db:
        similar = _build_similar_from_names(db, [("黄芪", 0.9), ("附子", 0.6), ("不存在品种", 0.5)])
    assert similar[0].name == "黄芪"
    assert similar[0].safety_level == "普通"  # 黄芪为普通
    assert similar[0].confidence == 0.9
    assert similar[1].name == "附子"
    assert similar[1].safety_level == "毒性"  # 附子为毒性
    # 知识库未收录的品种兜底为普通
    assert similar[2].name == "不存在品种"
    assert similar[2].safety_level == "普通"
