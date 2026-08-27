"""收藏路由（匿名 device_id / 登录 user_id 双维度）。

未登录以 X-Device-Id 关联；已登录（携带 Bearer token）以 user_id 关联。
登录后调用 POST /api/favorites/migrate 将匿名收藏合并到当前用户。
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.herb import Herb
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.services.auth import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["favorites"])


def _scope(device_id: str, user: User | None) -> tuple[str | None, int | None]:
    """返回 (device_id, user_id) 作用域；登录时以 user 为准。"""
    if user is not None:
        return None, user.id
    return device_id, None


@router.get("/api/favorites", response_model=list[FavoriteResponse])
def list_favorites(
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> list[Favorite]:
    """查询收藏列表。已登录按用户维度，否则按设备维度。"""
    if user is not None:
        query = select(Favorite).where(Favorite.user_id == user.id)
    else:
        if not device_id:
            return []
        query = select(Favorite).where(Favorite.device_id == device_id)
    return list(db.scalars(query.order_by(Favorite.created_at.desc())).all())


@router.post("/api/favorites", response_model=FavoriteResponse)
def add_favorite(
    payload: FavoriteCreate,
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Favorite:
    """新增收藏（幂等：已收藏则直接返回）。"""
    scope_device, scope_user = _scope(device_id, user)
    if scope_user is None and not scope_device:
        raise HTTPException(status_code=400, detail="缺少设备标识 X-Device-Id")

    herb = db.get(Herb, payload.herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药材不存在")

    query = select(Favorite).where(Favorite.herb_id == payload.herb_id)
    query = query.where(Favorite.user_id == scope_user) if scope_user else query.where(
        Favorite.device_id == scope_device
    )
    existing = db.scalar(query)
    if existing:
        return existing

    favorite = Favorite(device_id=scope_device, user_id=scope_user, herb_id=payload.herb_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/api/favorites/{herb_id}")
def remove_favorite(
    herb_id: int,
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """取消收藏。"""
    scope_device, scope_user = _scope(device_id, user)
    query = delete(Favorite).where(Favorite.herb_id == herb_id)
    query = query.where(Favorite.user_id == scope_user) if scope_user else query.where(
        Favorite.device_id == scope_device
    )
    db.execute(query)
    db.commit()
    return {"detail": "已取消收藏"}


@router.post("/api/favorites/migrate", response_model=dict)
def migrate_favorites(
    device_id: str = Header(default="", alias="X-Device-Id"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """将当前设备的匿名收藏合并到登录用户，并清除匿名副本。

    已登录必需；按 herb_id 去重，避免重复收藏。
    """
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    if not device_id:
        return {"migrated": 0}

    anonymous = list(
        db.scalars(
            select(Favorite).where(
                Favorite.device_id == device_id, Favorite.user_id.is_(None)
            )
        ).all()
    )

    migrated = 0
    for favorite in anonymous:
        dup = db.scalar(
            select(Favorite).where(
                Favorite.user_id == user.id, Favorite.herb_id == favorite.herb_id
            )
        )
        if dup is not None:
            # 用户已有收藏，仅移除匿名副本
            db.delete(favorite)
            continue
        # 改归属到用户并清空 device_id（NULL），匿名设备维度不再可见
        favorite.user_id = user.id
        favorite.device_id = None
        migrated += 1

    db.commit()
    logger.info("收藏迁移完成：user=%s, migrated=%s", user.username, migrated)
    return {"migrated": migrated}
