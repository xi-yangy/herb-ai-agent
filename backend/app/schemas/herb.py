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
    # 鉴别防雷警报字段（知识库数据驱动，非空即触发前端防雷警报卡）
    warning_label: str = ""
    warning_message: str = ""
    # 别名/俗名/植物学名（逗号分隔），识别匹配别名兜底用
    alias: str = ""
    nature_flavor: str
    effects: str
    usage: str
    contraindications: str
    toxicity: str
    description: str | None = None
    # 示例缩略图 URL（由路由层按药材名填充；无图返回空串，前端降级为纯文字卡片）
    image_url: str = ""

    model_config = {"from_attributes": True}
