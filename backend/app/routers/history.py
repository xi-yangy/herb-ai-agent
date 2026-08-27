"""识别历史路由（P0 持久化实现）。

本批以 device_id 标识匿名用户；第二批接入登录后切换到 user_id。
"""

import logging

from fastapi import APIRouter, Depends, Header
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recognition_history import RecognitionHistory
from app.schemas.history import HistoryCreate, HistoryResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["history"])


@router.get("/api/history", response_model=list[HistoryResponse])
def list_history(
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> list[RecognitionHistory]:
    """查询识别历史（时间倒序）。"""
    return list(
        db.scalars(
            select(RecognitionHistory)
            .where(RecognitionHistory.device_id == device_id)
            .order_by(RecognitionHistory.created_at.desc())
        ).all()
    )


@router.post("/api/history", response_model=HistoryResponse)
def create_history(
    payload: HistoryCreate,
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> RecognitionHistory:
    """新增识别历史。"""
    record = RecognitionHistory(
        device_id=payload.device_id or device_id,
        herb_id=payload.herb_id,
        result_name=payload.result_name,
        confidence=payload.confidence,
        channel=payload.channel,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/api/history")
def clear_history(
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> dict:
    """清除识别历史。"""
    db.execute(delete(RecognitionHistory).where(RecognitionHistory.device_id == device_id))
    db.commit()
    return {"detail": "历史已清除"}
