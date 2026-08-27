"""识别路由。

调用可插拔识别服务（当前为 MockRecognizer），返回药材结果。
真实引擎接入后，仅需替换 services/recognizer.py 中的实现实例。
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
    """图片识别：调用 RecognitionService 返回药材结果。"""
    result = recognizer.recognize(req.image_base64, db)
    logger.info("识别完成：%s (置信度 %.2f)", result.name, result.confidence)
    return RecognizeResponse(
        name=result.name,
        confidence=result.confidence,
        channel=recognizer.channel,
        safety_level=result.safety_level,
        herb=result.herb,
    )
