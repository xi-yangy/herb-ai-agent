"""药材知识库响应模型。"""

from pydantic import BaseModel


class SimilarHerb(BaseModel):
    """相似/候选品种条目（低置信度降级列表用）。

    由识别引擎（本地模型/百度）返回的 top-k 候选映射而来，与知识库的
    HerbResponse.similar_herbs（静态字符串）语义不同，故独立建模。
    """

    name: str
    confidence: float
    safety_level: str = "普通"
    source: str = ""


class HerbResponse(BaseModel):
    """药材条目响应（含 P0 知识字段）。"""

    id: int
    name: str
    safety_level: str
    source: str
    category: str
    similar_herbs: str
    nature_flavor: str
    effects: str
    usage: str
    contraindications: str
    toxicity: str
    description: str | None = None

    model_config = {"from_attributes": True}
