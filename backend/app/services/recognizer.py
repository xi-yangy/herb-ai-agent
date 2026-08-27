"""可插拔识别服务（混合双通道）。

通道编排（主通道优先）：
- LocalModelRecognizer：本地自建模型主通道（onnx/pytorch，本轮为占位桩 Stub）；
- BaiduRecognizer：百度植物识别兜底通道（top-k + 名称匹配知识库）；
- MockRecognizer：开发/降级保底（写死示例药材）。

三者统一返回 RecognizeResult（含实际命中 channel 与相似品种 similar），
由 HybridRecognizer 按「主通道 → 兜底 → Mock」链式调度。路由与前端契约不变。
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Any

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


def _parse_image(image_base64: str) -> bytes:
    """剥离 data:image 前缀，返回原始图片字节。"""
    if "," in image_base64 and image_base64.strip().lower().startswith("data:image"):
        return base64.b64decode(image_base64.split(",", 1)[1])
    return base64.b64decode(image_base64)


class MockRecognizer(RecognitionService):
    """Mock 识别实现。

    不真正分析图片，返回写死的示例药材（默认为「附子」，覆盖高危警示展示），
    供前端打通「上传 → 识别 → 结果 → 安全警示 → 历史收藏」全链路。
    真实引擎接入后替换本类。
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


class LocalModelRecognizer(RecognitionService):
    """本地自建模型主通道。

    本轮为「完整接口 + 占位桩(Stub)」实现：加载、图像预处理、top-k 输出的代码骨架
    均已写好，但推理内核为明确标注的占位逻辑。当未配置模型文件/类别清单时，
    本类如实判定为「不可用」（返回 is_available=False），由 HybridRecognizer 回退
    到百度/Mock，绝不虚标识别结果。

    待用户后续提供 onnx/pytorch 模型与类别清单后，仅需替换 `_infer_topk` 的
    推理实现（用真实引擎加载模型并输出 top-k），其余调度/映射逻辑无需改动。
    """

    channel = "local"

    # 占位桩默认输出（仅用于本地模型被强制启用但无真实模型时，验证通道链路）
    _STUB_LABELS = ["黄芪", "附子", "金银花"]

    def __init__(self) -> None:
        self._session: Any | None = None  # onnxruntime InferenceSession（惰性加载）
        self._labels: list[str] = []
        self._labels_loaded = False

    # ---- 配置/可用性 ----

    @property
    def is_available(self) -> bool:
        """本地模型主通道是否可用（需启用 + 配置模型文件与类别清单）。"""
        if not settings.model_enabled:
            return False
        if not settings.model_path or not settings.model_labels:
            logger.info("本地模型未配置完整（缺模型文件/类别清单），主通道不可用")
            return False
        return True

    def _load_labels(self) -> list[str]:
        """惰性加载类别清单（支持 txt 一行一类 或 JSON 数组）。"""
        if self._labels_loaded:
            return self._labels
        self._labels_loaded = True
        if not settings.model_labels:
            return []
        try:
            text = Path(settings.model_labels).read_text(encoding="utf-8").strip()
            if text.startswith("["):
                self._labels = [str(x) for x in json.loads(text)]
            else:
                self._labels = [line.strip() for line in text.splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("类别清单加载失败：%s", exc)
            self._labels = []
        return self._labels

    # ---- 图像预处理（真实模型接入时按模型输入协议调整） ----

    @staticmethod
    def _preprocess(image_bytes: bytes) -> Any:
        """将图片字节转为模型输入张量（占位实现：仅返回原始字节）。

        接入真实模型时，应使用 Pillow/numpy 完成 resize + 归一化 + HWC→CHW，
        并返回与 onnxruntime 输入协议一致的 numpy 数组。
        """
        return image_bytes

    # ---- 推理内核（占位桩，替换点） ----

    def _infer_topk(
        self, image_bytes: bytes, k: int, labels: list[str]
    ) -> list[tuple[str, float]]:
        """返回 top-k 的 (类别名, 置信度) 列表，按置信度降序。

        【占位桩说明】本实现不真正分析图片，恒定返回 _STUB_LABELS 的模拟置信度，
        仅用于验证「本地通道 → 降级/回退」链路。真实模型到位后，改为：
        1. onnxruntime: self._session.run(...) 取 softmax 概率，取前 k 个索引映射 labels；
        2. pytorch: 同理。labels 由 _load_labels() 提供，顺序与模型输出对齐。
        """
        # 占位桩：忽略 labels，返回内置示例类别（真实模型接入后按 labels 映射索引）
        names = labels or self._STUB_LABELS
        n = len(names)
        probs = [(1.0 - i * 0.08) for i in range(n)]  # 模拟：首类 1.0，依次递减
        ranked = sorted(zip(names, probs), key=lambda x: x[1], reverse=True)
        return ranked[:k]

    # ---- 识别主入口 ----

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        # 未配置/未启用：如实返回"主通道不可用"，由调度器回退（不虚标）
        if not self.is_available:
            logger.info("本地模型主通道不可用，交由调度器回退")
            herb = db.scalar(select(Herb).where(Herb.name == self._STUB_LABELS[0]))
            return RecognizeResult(
                name="",
                confidence=0.0,
                safety_level=herb.safety_level if herb else "普通",
                channel=self.channel,
                similar=[],
                low_confidence=True,
            )
        try:
            image_bytes = _parse_image(image_base64)
        except (ValueError, base64.binascii.Error) as exc:
            logger.warning("本地模型图片解析失败：%s", exc)
            herb = db.scalar(select(Herb).where(Herb.name == self._STUB_LABELS[0]))
            return RecognizeResult(
                name="",
                confidence=0.0,
                safety_level=herb.safety_level if herb else "普通",
                channel=self.channel,
                similar=[],
                low_confidence=True,
            )

        labels = self._load_labels()
        topk = self._infer_topk(image_bytes, settings.model_top_k, labels)
        if not topk:
            logger.info("本地模型无输出，交由调度器回退")
            herb = db.scalar(select(Herb).where(Herb.name == self._STUB_LABELS[0]))
            return RecognizeResult(
                name="",
                confidence=0.0,
                safety_level=herb.safety_level if herb else "普通",
                channel=self.channel,
                similar=[],
                low_confidence=True,
            )

        name, score = topk[0]
        herb = _match_herb(db, name)
        similar = _build_similar_from_names(db, topk)

        # 低置信度：标记 low_confidence，交由前端展示"相似品种 + 引导重拍"
        low_conf = score < settings.model_confidence_threshold or herb is None
        return RecognizeResult(
            name=name if herb else (name or ""),
            confidence=round(float(score), 4),
            safety_level=herb.safety_level if herb else "普通",
            channel=self.channel,
            similar=similar,
            low_confidence=low_conf,
            herb=HerbResponse.model_validate(herb) if herb else None,
        )


class BaiduRecognizer(RecognitionService):
    """百度植物识别兜底实现。

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
        k = settings.model_top_k
        out: list[tuple[str, float]] = []
        for item in results[:k]:
            out.append((str(item.get("name", "")), float(item.get("score", 0.0))))
        return out


class HybridRecognizer(RecognitionService):
    """混合双通道调度器（主通道优先）。

    链路：本地模型(主) → 百度(兜底) → Mock(保底)。本地模型不可用/低置信度/
    未命中知识库时，自动回退百度；百度不可用时回退 Mock。
    """

    channel = "hybrid"

    def __init__(self) -> None:
        self._local = LocalModelRecognizer()
        self._baidu = BaiduRecognizer()

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        # 1) 主通道：本地模型
        if self._local.is_available:
            local_result = self._local.recognize(image_base64, db)
            # 命中条件：有名称、置信度达标、且命中本地知识库（未命中则视为不靠谱，交给兜底）
            if (
                local_result.name
                and not local_result.low_confidence
                and local_result.herb is not None
            ):
                logger.info("本地模型命中：%s (%.2f)", local_result.name, local_result.confidence)
                return local_result
            # 低置信度：仍优先展示本地模型的相似品种降级（不直接回退百度，给用户更贴近的候选）
            if local_result.name and local_result.low_confidence and local_result.similar:
                logger.info(
                    "本地模型低置信度（%.2f），按相似品种降级展示：%s",
                    local_result.confidence,
                    local_result.name,
                )
                return local_result
            logger.info("本地模型未命中知识库，回退百度兜底")

        # 2) 兜底通道：百度
        baidu_result = self._baidu.recognize(image_base64, db)
        return baidu_result


def _match_herb(db: Session, name: str) -> Herb | None:
    """按名称匹配本地知识库药材。

    优先精确匹配；失败时去除常见形态后缀（片/根/皮/子 等）再匹配，
    以兼容百度返回的植物别名与本地药材命名差异。
    """
    if not name:
        return None

    herb = db.scalar(select(Herb).where(Herb.name == name))
    if herb is not None:
        return herb

    # 尝试去常见后缀后匹配（如「黄芪片」→「黄芪」）
    for suffix in _SUFFIXES:
        stripped = name[:-1] if name.endswith(suffix) else name
        if stripped == name:
            continue
        herb = db.scalar(select(Herb).where(Herb.name == stripped))
        if herb is not None:
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


# 当前使用的识别服务实例：混合双通道调度器（本地模型 → 百度 → Mock）
recognizer: RecognitionService = HybridRecognizer()
