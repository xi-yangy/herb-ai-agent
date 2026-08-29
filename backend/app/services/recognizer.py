"""可插拔识别服务（百度 + Mock 单通道）。

- BaiduRecognizer：百度植物识别（top-k + 名称匹配知识库 + 低置信降级）；
- MockRecognizer：开发/降级保底（写死示例药材）。

统一返回 RecognizeResult（含实际命中 channel 与相似品种 similar）。百度未启用/
失败/无结果时回退 Mock，保证演示链路不中断。路由与前端契约不变。
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.herb import Herb
from app.schemas.herb import HerbResponse, SimilarHerb
from app.schemas.recognize import RecognizeResult

logger = logging.getLogger(__name__)

# 百度植物识别接口与 OAuth token 地址
_BAIDU_PLANT_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v1/plant"
_BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

# 知识库名称去后缀匹配用的常见形态后缀
_SUFFIXES = ("片", "根", "皮", "子", "花", "叶", "茎", "果")


class RecognitionService(ABC):
    """识别服务抽象接口。

    所有实现需返回一个 RecognizeResult（含名称、置信度、安全等级、药材详情、
    相似品种列表与实际命中通道）。
    """

    channel: str = "mock"

    @abstractmethod
    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        """识别图片并返回结果。

        Args:
            image_base64: 图片 base64 编码。
            db: 数据库会话（用于匹配知识库药材）。

        Returns:
            识别结果；若匹配不到知识库药材，herb 为 None。
        """
        raise NotImplementedError


class MockRecognizer(RecognitionService):
    """Mock 识别实现。

    不真正分析图片，返回写死的示例药材（默认为「附子」，覆盖高危警示展示），
    供前端打通「上传 → 识别 → 结果 → 安全警示 → 历史收藏」全链路。
    百度未配置凭证/不可用时作为兜底。
    """

    channel = "mock"

    # 默认命中的示例药材名（需存在于知识库，否则 herb 为 None）
    DEFAULT_HERB_NAME = "附子"

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        # 忽略图片内容，恒定返回示例药材；置信度写死以模拟识别结果。
        herb = db.scalar(select(Herb).where(Herb.name == self.DEFAULT_HERB_NAME))
        return RecognizeResult(
            name=herb.name if herb else self.DEFAULT_HERB_NAME,
            confidence=0.97,
            safety_level=herb.safety_level if herb else "普通",
            channel=self.channel,
            similar=_build_similar_from_names(db, [(self.DEFAULT_HERB_NAME, 0.97)]),
            herb=HerbResponse.model_validate(herb) if herb else None,
        )


class BaiduRecognizer(RecognitionService):
    """百度植物识别实现。

    调用百度「植物识别」接口识别图片，取 top-k 返回结果并匹配本地知识库；
    识别失败/超时/未配置凭证时回退到 MockRecognizer，保证演示链路不中断。
    """

    channel = "baidu"

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expire_at: float = 0.0
        # 降级兜底
        self._fallback = MockRecognizer()

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        """识别图片；百度未启用/不可用时回退 Mock。"""
        if not (settings.baidu_enabled and settings.baidu_api_key and settings.baidu_secret_key):
            return self._fallback.recognize(image_base64, db)
        try:
            topk = self._call_baidu(image_base64)
        except Exception as exc:  # noqa: BLE001  网络/接口异常统一降级
            logger.warning("百度识别失败，回退 Mock：%s", exc)
            return self._fallback.recognize(image_base64, db)

        if not topk:
            logger.info("百度识别无结果，回退 Mock")
            return self._fallback.recognize(image_base64, db)

        name, score = topk[0]
        herb = _match_herb(db, name)
        similar = _build_similar_from_names(db, topk)

        # 低置信度不直接给结论：降级为相似品种（前端按 low_confidence 降级展示）
        low_conf = score < settings.baidu_confidence_threshold
        if low_conf:
            logger.info("百度置信度偏低（%.2f），按相似品种展示：%s", score, name)

        return RecognizeResult(
            name=name,
            confidence=round(float(score), 4),
            safety_level=herb.safety_level if herb else "普通",
            channel=self.channel,
            similar=similar,
            low_confidence=low_conf,
            herb=HerbResponse.model_validate(herb) if herb else None,
        )

    # ---- 内部实现 ----

    def _get_access_token(self) -> str:
        """获取百度 access_token（带缓存与过期刷新）。"""
        if self._access_token and time.time() < self._token_expire_at:
            return self._access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": settings.baidu_api_key,
            "client_secret": settings.baidu_secret_key,
        }
        url = f"{_BAIDU_TOKEN_URL}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310  固定 https 地址
            data = json.loads(resp.read().decode("utf-8"))

        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"获取百度 token 失败：{data.get('error_description', '未知错误')}")
        # 百度 token 有效期 30 天，提前 1 小时刷新
        self._access_token = token
        self._token_expire_at = time.time() + 29 * 24 * 3600
        return token

    def _call_baidu(self, image_base64: str) -> list[tuple[str, float]]:
        """调用百度植物识别，返回按置信度降序的 top-k (name, score) 列表。"""
        token = self._get_access_token()
        body = urllib.parse.urlencode(
            {
                "image": image_base64,
                "baike_num": 0,
            }
        ).encode("utf-8")
        url = f"{_BAIDU_PLANT_URL}?access_token={urllib.parse.quote(token)}"

        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))

        results = data.get("result") or []
        if not results:
            return []
        # result 按置信度降序，取前 k 条
        k = settings.baidu_top_k
        out: list[tuple[str, float]] = []
        for item in results[:k]:
            out.append((str(item.get("name", "")), float(item.get("score", 0.0))))
        return out


def _match_herb(db: Session, name: str) -> Herb | None:
    """按名称匹配本地知识库药材（双向归一化）。

    匹配顺序：
    1. 精确匹配（「枸杞子」→「枸杞子」）；
    2. 去常见后缀匹配（如「黄芪片」→「黄芪」）；
    3. 补常见后缀匹配（如「枸杞」→「枸杞子」，兼容识别返回简写而知识库存全称）；
    4. 别名兜底匹配（如百度返回植物学名「忍冬」→ 命中别名配置了「忍冬」的金银花）；
    5. 受限包含兜底匹配（如「蒙古黄芪」→「黄芪」，endswith + 修饰词 ≤2 字 + 最长优先）。

    仅做单层补全，不递归，避免过度归一化造成误匹配。别名匹配用整词匹配
    （alias 字段逗号分隔，避免「人参」误中「人参果」这类子串误判）；包含匹配
    仅允许前缀修饰（endswith）、限制修饰词长度并取最长名称优先，防误匹配。
    """
    if not name:
        return None

    herb = db.scalar(select(Herb).where(Herb.name == name))
    if herb is not None:
        return herb

    # 去常见后缀后匹配（如「黄芪片」→「黄芪」）
    for suffix in _SUFFIXES:
        stripped = name[:-1] if name.endswith(suffix) else name
        if stripped == name:
            continue
        herb = db.scalar(select(Herb).where(Herb.name == stripped))
        if herb is not None:
            return herb

    # 补常见后缀后匹配（如「枸杞」→「枸杞子」；识别返回简写、知识库存全称）
    for suffix in _SUFFIXES:
        expanded = f"{name}{suffix}"
        if expanded == name:
            continue
        herb = db.scalar(select(Herb).where(Herb.name == expanded))
        if herb is not None:
            return herb

    # 别名兜底匹配：alias 为逗号分隔列表，识别返回名恰好是某药材别名即命中
    herb = _match_by_alias(db, name)
    if herb is not None:
        return herb

    # 受限包含兜底：知识库名是识别名的后缀且修饰词不超 2 字（如「蒙古黄芪」→「黄芪」）
    herb = _match_by_containment(db, name)
    if herb is not None:
        return herb
    return None


def _match_by_containment(db: Session, name: str) -> Herb | None:
    """受限包含兜底匹配：识别名以知识库名为后缀，且前置修饰词不超 2 字。

    覆盖百度返回「产地/性状前缀 + 标准名」的模式（如「蒙古黄芪」「膜荚黄芪」→「黄芪」）。

    防误匹配设计：
    - 仅允许前缀修饰（endswith），不用 startswith，避免「人参果」误中「人参」这类后缀延伸；
    - 长度差 ≤ 2（修饰词不超 2 字），排除「内蒙古黄芪」（差 3）等过度匹配；
    - 多个候选命中时取名称最长者优先，避免短名误配（如返回名同时以「芪」「黄芪」结尾时取「黄芪」）。
    """
    if not name:
        return None
    # 知识库规模小（约百级），全量读取后内存过滤，代码清晰且开销可忽略
    candidates = [
        herb
        for herb in db.scalars(select(Herb)).all()
        if 0 < len(name) - len(herb.name) <= 2 and name.endswith(herb.name)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda h: len(h.name))


def _match_by_alias(db: Session, name: str) -> Herb | None:
    """按别名整词匹配：识别返回的名称 name 若正好是某药材的别名之一，则命中该药材。

    alias 存的是"该药材自己的别名"（逗号分隔，如金银花→"忍冬"）。语义是：
    百度/本地识别返回 name，若 name 是某药材的别名（如「忍冬」），即匹配到该药材。
    用 LIKE 粗筛 + 整词精筛，兼顾性能与避免子串误判（避免「人参」误中「人参果」）。
    """
    if not name:
        return None
    for herb in db.scalars(select(Herb).where(Herb.alias.like(f"%{name}%"))).all():
        # 别名可用中文顿号「、」、逗号「，」或英文逗号「,」分隔
        tokens = [a.strip() for a in herb.alias.replace("、", ",").replace("，", ",").split(",")]
        if name in tokens:
            return herb
    return None


def _build_similar_from_names(
    db: Session, topk: list[tuple[str, float]]
) -> list[SimilarHerb]:
    """将 top-k (名称, 置信度) 列表映射为相似品种条目（填充知识库安全等级与来源）。"""
    out: list[SimilarHerb] = []
    for name, confidence in topk:
        if not name:
            continue
        herb = _match_herb(db, name)
        out.append(
            SimilarHerb(
                name=name,
                confidence=round(float(confidence), 4),
                safety_level=herb.safety_level if herb else "普通",
                source=herb.source if herb else "",
            )
        )
    return out


# 当前使用的识别服务实例：本地优先 + 百度兜底 + Mock 保底。
# 延迟导入 HybridRecognizer，避免未安装 torch 时在模块导入阶段报错。
def _build_default_recognizer() -> RecognitionService:
    from app.services.hybrid_recognizer import HybridRecognizer

    return HybridRecognizer()


recognizer: RecognitionService = _build_default_recognizer()
