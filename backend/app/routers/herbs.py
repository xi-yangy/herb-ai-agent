"""药材知识库路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.herb import Herb
from app.schemas.herb import HerbResponse
from app.services.herb_images import image_url_for

router = APIRouter(tags=["herbs"])


def _with_image(herb: HerbResponse) -> HerbResponse:
    """按药材名填充示例图 URL（无图返回空串，前端降级为纯文字卡片）。"""
    herb.image_url = image_url_for(herb.name)
    return herb


@router.get("/api/herbs", response_model=list[HerbResponse])
def list_herbs(db: Session = Depends(get_db)) -> list[Herb]:
    """列出全部药材（空库时返回空列表）。"""
    herbs = list(db.scalars(select(Herb)).all())
    return [_with_image(HerbResponse.model_validate(h)) for h in herbs]


@router.get("/api/herbs/{herb_id}", response_model=HerbResponse)
def get_herb(herb_id: int, db: Session = Depends(get_db)) -> Herb:
    """按 ID 查询药材详情。"""
    herb = db.get(Herb, herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药材不存在")
    return _with_image(HerbResponse.model_validate(herb))
