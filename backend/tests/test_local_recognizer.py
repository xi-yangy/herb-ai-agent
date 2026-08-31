"""本地模型识别与混合调度测试。

覆盖：
- 本地模型未启用时，HybridRecognizer 直接回退百度（百度禁用则回退 Mock）；
- 本地模型高置信度时返回 local 结果；
- 本地模型低置信度时回退百度兜底；
- LocalRecognizer 复用 _match_herb 匹配知识库。

通过打桩 LocalRecognizer._predict 隔离真实模型加载/推理，不依赖模型文件与外网。
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.hybrid_recognizer import HybridRecognizer
from app.services.local_recognizer import LocalRecognizer
from app.services.recognizer import MockRecognizer


def _make_local(preds):
    """构造一个已打桩 _predict 的 LocalRecognizer。"""
    rec = LocalRecognizer()
    rec._predict = lambda image_base64: preds  # type: ignore[method-assign]
    return rec


def test_local_disabled_falls_back_to_baidu() -> None:
    """本地未启用时，HybridRecognizer 跳过本地直接走百度（此处百度禁用→Mock）。"""
    settings.local_enabled = False
    settings.baidu_enabled = False
    hybrid = HybridRecognizer()
    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "mock"  # 百度禁用内部兜 Mock
    assert result.name  # Mock 返回附子


def test_local_high_confidence_returns_local() -> None:
    """本地高置信度时返回 local 通道结果。"""
    settings.local_enabled = True
    settings.local_confidence_threshold = 0.6
    hybrid = HybridRecognizer()
    hybrid._local = _make_local([("黄芪", 0.95), ("甘草", 0.03)])

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "local"
    assert result.name == "黄芪"
    assert result.low_confidence is False


def test_local_low_confidence_falls_back_to_baidu() -> None:
    """本地低置信度（< 阈值）时回退百度兜底。"""
    settings.local_enabled = True
    settings.local_confidence_threshold = 0.6
    settings.baidu_enabled = False  # 百度禁用，最终落 Mock
    hybrid = HybridRecognizer()
    hybrid._local = _make_local([("黄芪", 0.42), ("甘草", 0.30)])

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    # 低置信回退百度 → 百度禁用 → Mock
    assert result.channel == "mock"


def test_local_flat_distribution_rejects() -> None:
    """本地 softmax 分布平坦（top-1/top-2 边际小于阈值）时拒识，回退百度兜底。"""
    settings.local_enabled = True
    settings.local_confidence_threshold = 0.6
    settings.local_margin_threshold = 0.15
    settings.baidu_enabled = False  # 百度禁用，最终落 Mock
    hybrid = HybridRecognizer()
    # top-1 超过绝对阈值，但边际 0.60 - 0.50 = 0.10 < 0.15，判为不确定
    hybrid._local = _make_local([("黄芪", 0.60), ("甘草", 0.50), ("附子", 0.02)])

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    # 拒识回退百度 → 百度禁用 → Mock
    assert result.channel == "mock"


def test_local_sufficient_margin_passes() -> None:
    """top-1 达标且 top-1/top-2 边际充足时，本地结果放行。"""
    settings.local_enabled = True
    settings.local_confidence_threshold = 0.6
    settings.local_margin_threshold = 0.15
    hybrid = HybridRecognizer()
    hybrid._local = _make_local([("黄芪", 0.72), ("甘草", 0.20), ("附子", 0.02)])

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "local"
    assert result.low_confidence is False
    assert result.name == "黄芪"


def test_local_exception_falls_back_to_baidu() -> None:
    """本地推理抛异常时回退百度兜底。"""
    settings.local_enabled = True
    settings.baidu_enabled = False
    hybrid = HybridRecognizer()
    hybrid._local = _make_local([])  # 空结果
    # 空结果时 LocalRecognizer.recognize 抛 RuntimeError

    with SessionLocal() as db:
        result = hybrid.recognize("fake", db)
    assert result.channel == "mock"


def test_local_recognizer_matches_herb() -> None:
    """LocalRecognizer 复用 _match_herb，命中知识库返回完整 herb。"""
    settings.local_enabled = True
    settings.local_confidence_threshold = 0.6
    rec = _make_local([("附子", 0.97)])
    with SessionLocal() as db:
        result = rec.recognize("fake", db)
    assert result.channel == "local"
    assert result.name == "附子"
    assert result.safety_level == "毒性"  # 附子为毒性
    assert result.herb is not None


def test_mock_recognizer_still_works() -> None:
    """保底 MockRecognizer 语义不变（回归保护）。"""
    rec = MockRecognizer()
    with SessionLocal() as db:
        result = rec.recognize("fake", db)
    assert result.channel == "mock"
    assert result.name == "附子"
