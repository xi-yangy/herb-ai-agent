"""混合识别调度器（本地优先 + 百度兜底 + Mock 保底）。

调度策略（严格保证演示链路不中断）：

1. 本地模型启用且推理成功、置信度 >= 阈值 → 返回 local 结果；
2. 本地未启用 / 加载失败 / 推理异常 / 无结果 / 置信度低于阈值 → 回退百度；
3. 百度未启用 / 失败 / 无结果 → 百度内部再回退 Mock。

返回结果的 channel 如实标记 local / baidu / mock，路由与前端契约不变。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.recognize import RecognizeResult
from app.services.recognizer import BaiduRecognizer, RecognitionService

logger = logging.getLogger(__name__)


class HybridRecognizer(RecognitionService):
    """本地主通道 + 百度兜底的混合识别器。"""

    # 对外默认 channel 标记为 local（实际由识别结果如实标记）
    channel = "local"

    def __init__(self) -> None:
        # 延迟导入 LocalRecognizer，避免后端未装 torch 时导入即报错
        from app.services.local_recognizer import LocalRecognizer

        self._local = LocalRecognizer()
        self._baidu = BaiduRecognizer()  # 百度内部已兜 Mock

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        """按 本地 → 百度 → Mock 的顺序识别。"""
        # 本地未启用时直接跳过本地，回退百度
        if not settings.local_enabled:
            logger.info("本地模型未启用，直接回退百度")
            return self._baidu.recognize(image_base64, db)

        try:
            result = self._local.recognize(image_base64, db)
        except Exception as exc:  # noqa: BLE001  本地模型任何异常均回退百度
            logger.warning("本地模型识别失败，回退百度：%s", exc)
            return self._baidu.recognize(image_base64, db)

        # 本地置信度低于阈值：按用户约定回退百度兜底
        if result.low_confidence:
            logger.info(
                "本地模型置信度偏低（%.2f < %.2f），回退百度兜底",
                result.confidence,
                settings.local_confidence_threshold,
            )
            return self._baidu.recognize(image_base64, db)

        return result
