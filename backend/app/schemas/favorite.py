"""收藏模型。"""

from datetime import datetime

from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    """新增收藏请求。"""

    herb_id: int


class FavoriteResponse(BaseModel):
    """收藏响应。"""

    id: int
    herb_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
