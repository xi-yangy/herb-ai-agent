"""药材知识库响应模型。"""

from pydantic import BaseModel


class HerbResponse(BaseModel):
    """药材条目响应（含 P0 知识字段）。"""

    id: int
    name: str
    safety_level: str
    source: str
    nature_flavor: str
    effects: str
    usage: str
    contraindications: str
    toxicity: str
    description: str | None = None

    model_config = {"from_attributes": True}
