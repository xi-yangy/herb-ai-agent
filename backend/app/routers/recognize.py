"""识别路由。

调用混合双通道识别服务（本地模型 → 百度 → Mock），返回药材结果与相似品种降级信息。
实际命中通道由识别器结果回传（local/baidu/mock）。
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recognize import RecognizeRequest, RecognizeResponse
from app.services.recognizer import recognizer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recognize"])


@router.post("/api/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest, db: Session = Depends(get_db)) -> RecognizeResponse:
    """图片识别：调用混合调度器返回药材结果。"""
    result = recognizer.recognize(req.image_base64, db)
    logger.info(
        "识别完成：%s (置信度 %.2f, 通道 %s, 低置信 %s)",
        result.name,
        result.confidence,
        result.channel,
        result.low_confidence,
    )
    return RecognizeResponse(
        name=result.name,
        confidence=result.confidence,
        channel=result.channel,
        safety_level=result.safety_level,
        similar=result.similar,
        low_confidence=result.low_confidence,
        herb=result.herb,
    )
