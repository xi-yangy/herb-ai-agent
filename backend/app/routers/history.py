"""识别历史路由（P0 持久化实现）。

支持匿名（device_id）与登录（user_id）双维度：
- 未登录：以 X-Device-Id 关联；
- 已登录（携带 Bearer token）：优先以 user_id 关联，未携带 token 时回退 device_id。
登录后调用 POST /api/history/migrate 将匿名记录合并到当前用户。
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recognition_history import RecognitionHistory
from app.models.user import User
from app.schemas.history import HistoryCreate, HistoryResponse
from app.services.auth import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["history"])


@router.get("/api/history", response_model=list[HistoryResponse])
def list_history(
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> list[RecognitionHistory]:
    """查询识别历史（时间倒序）。已登录按用户维度，否则按设备维度。"""
    # 未登录时：需提供非空设备标识才返回对应匿名记录，避免命中用户维度的空 device 记录
    if user is None and not device_id:
        return []
    query = select(RecognitionHistory).order_by(RecognitionHistory.created_at.desc())
    if user is not None:
        query = query.where(RecognitionHistory.user_id == user.id)
    else:
        query = query.where(RecognitionHistory.device_id == device_id)
    return list(db.scalars(query).all())


@router.post("/api/history", response_model=HistoryResponse)
def create_history(
    payload: HistoryCreate,
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> RecognitionHistory:
    """新增识别历史。已登录写入 user_id，否则写入 device_id。"""
    record = RecognitionHistory(
        device_id="" if user is not None else (payload.device_id or device_id),
        user_id=user.id if user is not None else None,
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
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """清除识别历史（仅当前维度）。"""
    if user is not None:
        db.execute(delete(RecognitionHistory).where(RecognitionHistory.user_id == user.id))
    else:
        db.execute(delete(RecognitionHistory).where(RecognitionHistory.device_id == device_id))
    db.commit()
    return {"detail": "历史已清除"}


@router.post("/api/history/migrate", response_model=dict)
def migrate_history(
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """将当前设备的匿名历史合并到登录用户，并清除匿名副本。

    已登录必需，否则 401；防止重复迁移（已属于该用户的历史不动）。
    """
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    if not device_id:
        return {"migrated": 0}

    anonymous = list(
        db.scalars(
            select(RecognitionHistory).where(
                RecognitionHistory.device_id == device_id,
                RecognitionHistory.user_id.is_(None),
            )
        ).all()
    )

    migrated = 0
    for record in anonymous:
        # 避免与用户已存在的同 herb 记录重复（按 herb_id 去重）
        if record.herb_id is not None:
            dup = db.scalar(
                select(RecognitionHistory).where(
                    RecognitionHistory.user_id == user.id,
                    RecognitionHistory.herb_id == record.herb_id,
                )
            )
            if dup is not None:
                # 用户已有记录，直接移除匿名副本
                db.delete(record)
                continue
        # 转移到用户维度（user_id 归属 + 清空 device_id），并移除匿名副本，
        # 确保匿名设备维度不再能查到该记录
        new_record = RecognitionHistory(
            device_id="",
            user_id=user.id,
            herb_id=record.herb_id,
            result_name=record.result_name,
            confidence=record.confidence,
            channel=record.channel,
        )
        db.add(new_record)
        db.delete(record)
        migrated += 1

    db.commit()
    logger.info("历史迁移完成：user=%s, migrated=%s", user.username, migrated)
    return {"migrated": migrated}
