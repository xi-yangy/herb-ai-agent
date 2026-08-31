"""识别路由。

调用混合双通道识别服务（本地模型 → 百度 → Mock），返回药材结果与相似品种降级信息。
实际命中通道由识别器结果回传（local/baidu/mock）。
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.herb import HerbResponse
from app.schemas.recognize import RecognizeRequest, RecognizeResponse, WarningInfo
from app.services.recognizer import recognizer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recognize"])


def _build_warning(herb: HerbResponse | None, result_name: str) -> WarningInfo:
    """由命中的知识库药材组装鉴别防雷警报信息。

    仅当药材配置了需防雷标记（warning_label 非空）时才返回非空 warning；
    未收录知识库或无防雷字段的药材返回空对象，避免前端误触发警报卡。
    """
    if not herb or not herb.warning_label:
        return WarningInfo()
    return WarningInfo(
        label=herb.warning_label,
        message=herb.warning_message,
        herb_name=result_name,
    )


@router.post("/api/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest, db: Session = Depends(get_db)) -> RecognizeResponse:
    """图片识别：调用混合调度器返回药材结果。"""
    result = recognizer.recognize(req.image_base64, db)
    logger.info(
        "识别完成：%s (置信度 %.2f, 通道 %s, 低置信 %s, 未识别 %s)",
        result.name,
        result.confidence,
        result.channel,
        result.low_confidence,
        result.unrecognized,
    )
    return RecognizeResponse(
        name=result.name,
        confidence=result.confidence,
        channel=result.channel,
        safety_level=result.safety_level,
        similar=result.similar,
        low_confidence=result.low_confidence,
        unrecognized=result.unrecognized,
        herb=result.herb,
        warning=_build_warning(result.herb, result.name),
    )
