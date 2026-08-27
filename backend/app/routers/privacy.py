"""隐私授权路由：读写授权状态。

以 X-Device-Id（匿名设备维度）关联授权记录，未登录也可管理。
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.privacy_consent import PrivacyConsent
from app.schemas.privacy import CONSENT_TYPES, ConsentResponse, ConsentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/consents", response_model=list[ConsentResponse])
def list_consents(
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> list[PrivacyConsent]:
    """查询某设备的授权状态列表。"""
    if not device_id:
        return []
    return list(
        db.scalars(
            select(PrivacyConsent).where(PrivacyConsent.device_id == device_id)
        ).all()
    )


@router.put("/consents", response_model=ConsentResponse)
def update_consent(
    payload: ConsentUpdate,
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> PrivacyConsent:
    """更新某一项授权状态（幂等，不存在则创建）。"""
    if not device_id:
        raise HTTPException(status_code=400, detail="缺少设备标识 X-Device-Id")
    if payload.consent_type not in CONSENT_TYPES:
        raise HTTPException(
            status_code=422, detail=f"不支持的授权类型：{payload.consent_type}"
        )

    record = db.scalar(
        select(PrivacyConsent).where(
            PrivacyConsent.device_id == device_id,
            PrivacyConsent.consent_type == payload.consent_type,
        )
    )
    if record is None:
        record = PrivacyConsent(
            device_id=device_id, consent_type=payload.consent_type, granted=payload.granted
        )
        db.add(record)
    else:
        record.granted = payload.granted

    db.commit()
    db.refresh(record)
    return record
