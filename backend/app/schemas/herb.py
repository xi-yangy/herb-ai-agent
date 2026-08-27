"""药材知识库响应模型。"""

from pydantic import BaseModel


class HerbResponse(BaseModel):
    """药材条目响应。"""

    id: int
    name: str
    safety_level: str
    source: str

    model_config = {"from_attributes": True}
