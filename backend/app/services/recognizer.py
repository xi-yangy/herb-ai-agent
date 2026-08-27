"""可插拔识别服务。

定义 RecognitionService 抽象接口与 MockRecognizer 实现。
真实引擎接入时，只需新增 BaiduRecognizer / LocalModelRecognizer 实现
并在此切换返回的实例，路由与前端契约不变。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.herb import Herb
from app.schemas.herb import HerbResponse
from app.schemas.recognize import RecognizeResult


class RecognitionService(ABC):
    """识别服务抽象接口。

    所有实现需返回一个 RecognizeResult（含名称、置信度、安全等级与药材详情）。
    """

    # 服务通道标识，写历史时使用
    channel: str

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
            herb=HerbResponse.model_validate(herb) if herb else None,
        )


# 当前使用的识别服务实例（真实引擎接入时在此切换）
recognizer: RecognitionService = MockRecognizer()
