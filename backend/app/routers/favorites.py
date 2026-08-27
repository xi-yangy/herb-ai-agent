"""收藏路由（匿名 device_id 维度）。

本批无登录，以 X-Device-Id 请求头关联收藏；第二批登录后迁移到 user_id。
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.herb import Herb
from app.schemas.favorite import FavoriteCreate, FavoriteResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["favorites"])


@router.get("/api/favorites", response_model=list[FavoriteResponse])
def list_favorites(
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> list[Favorite]:
    """查询某设备的收藏列表。"""
    if not device_id:
        return []
    return list(
        db.scalars(
            select(Favorite)
            .where(Favorite.device_id == device_id)
            .order_by(Favorite.created_at.desc())
        ).all()
    )


@router.post("/api/favorites", response_model=FavoriteResponse)
def add_favorite(
    payload: FavoriteCreate,
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> Favorite:
    """新增收藏（幂等：已收藏则直接返回）。"""
    if not device_id:
        raise HTTPException(status_code=400, detail="缺少设备标识 X-Device-Id")
    herb = db.get(Herb, payload.herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药材不存在")
    existing = db.scalar(
        select(Favorite).where(Favorite.device_id == device_id, Favorite.herb_id == payload.herb_id)
    )
    if existing:
        return existing
    favorite = Favorite(device_id=device_id, herb_id=payload.herb_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/api/favorites/{herb_id}")
def remove_favorite(
    herb_id: int,
    device_id: str = Header(default="", alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> dict:
    """取消收藏。"""
    db.execute(delete(Favorite).where(Favorite.device_id == device_id, Favorite.herb_id == herb_id))
    db.commit()
    return {"detail": "已取消收藏"}
