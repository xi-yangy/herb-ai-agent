"""双通道识别调度与低置信降级测试。

覆盖：
- 默认配置（本地模型禁用 + 百度禁用）下，识别回退 Mock，channel 语义正确；
- 本地模型主通道可用性判定；
- HybridRecognizer 主通道优先调度：本地命中 / 本地低置信降级 / 本地不可用回退百度；
- 相似品种列表（similar）构建与 low_confidence 标记。

本地模型为占位桩，故通过直接实例化并替换内部方法的方式隔离验证调度逻辑，
不依赖真实模型文件或外网。对应 PRD Q2「高危判定/调度逻辑单测」要求。
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.herb import HerbResponse, SimilarHerb
from app.schemas.recognize import RecognizeResult
from app.services.recognizer import (
    HybridRecognizer,
    LocalModelRecognizer,
    _build_similar_from_names,
)

# 保证测试环境配置（独立覆盖，避免污染其他用例）
settings.model_enabled = False
settings.model_path = ""
settings.model_labels = ""
settings.baidu_enabled = False
settings.baidu_api_key = ""
settings.baidu_secret_key = ""


def _herb_response(name: str, safety_level: str, hid: int) -> HerbResponse:
    return HerbResponse(
        id=hid,
        name=name,
        safety_level=safety_level,
        source="示例(编撰)",
        category="",
        similar_herbs="",
        nature_flavor="",
        effects="",
        usage="",
        contraindications="",
        toxicity="",
    )


def test_default_falls_back_to_mock(client: TestClient) -> None:
    """本地模型与百度均禁用时，识别接口回退 Mock，channel 为 mock。"""
    resp = client.post("/api/recognize", json={"image_base64": "fake", "channel": "camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "mock"
    assert data["name"]  # Mock 恒定返回附子
    assert data["low_confidence"] is False
    # 响应契约包含相似品种字段
    assert "similar" in data
    assert isinstance(data["similar"], list)


def test_local_model_availability() -> None:
    """未配置模型文件/类别清单时，本地主通道不可用（如实判定，不虚标）。"""
    rec = LocalModelRecognizer()
    assert rec.is_available is False

    settings.model_enabled = True
    settings.model_path = "models/dummy.onnx"
    settings.model_labels = ""
    assert rec.is_available is False  # 缺类别清单仍不可用

    settings.model_labels = "models/labels.txt"
    assert rec.is_available is True  # 配置完整后可用

    # 还原，避免影响后续用例
    settings.model_enabled = False
    settings.model_path = ""
    settings.model_labels = ""


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


def test_hybrid_prefers_local_when_available() -> None:
    """本地模型可用且命中知识库时，调度器应返回 local 结果。"""
    hybrid = HybridRecognizer()
    settings.model_enabled = True
    settings.model_path = "dummy.onnx"
    settings.model_labels = "dummy.txt"

    # 打桩本地识别器：返回"黄芪"高置信命中结果
    hybrid._local.recognize = lambda image_base64, db: RecognizeResult(  # type: ignore[method-assign]
        name="黄芪",
        confidence=0.95,
        safety_level="普通",
        channel="local",
        similar=[],
        low_confidence=False,
        herb=_herb_response("黄芪", "普通", 1),
    )

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "local"
    assert result.name == "黄芪"
    assert result.low_confidence is False

    settings.model_enabled = False
    settings.model_path = ""
    settings.model_labels = ""


def test_hybrid_returns_local_low_confidence() -> None:
    """本地模型低置信度但有相似候选时，保留本地降级展示（low_confidence=true）。"""
    hybrid = HybridRecognizer()
    settings.model_enabled = True
    settings.model_path = "dummy.onnx"
    settings.model_labels = "dummy.txt"

    def fake_local_low(image_base64, db):
        return RecognizeResult(
            name="黄芪",
            confidence=0.4,  # 低于阈值 0.6
            safety_level="普通",
            channel="local",
            similar=[SimilarHerb(name="黄芪", confidence=0.4, safety_level="普通")],
            low_confidence=True,
        )

    hybrid._local.recognize = fake_local_low  # type: ignore[method-assign]

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    # 本地低置信且有相似候选 → 保留本地结果降级展示
    assert result.channel == "local"
    assert result.low_confidence is True
    assert result.similar

    settings.model_enabled = False
    settings.model_path = ""
    settings.model_labels = ""


def test_hybrid_falls_back_to_mock_when_disabled() -> None:
    """本地与百度均禁用时，调度器回退 Mock，channel 为 mock。"""
    hybrid = HybridRecognizer()
    settings.model_enabled = False
    settings.model_path = ""
    settings.model_labels = ""
    settings.baidu_enabled = False

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "mock"
