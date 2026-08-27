"""识别历史模型。"""

from datetime import datetime

from pydantic import BaseModel


class HistoryCreate(BaseModel):
    """新增识别历史请求。

    识别成功后由前端/后端写入一条记录。
    """

    result_name: str
    confidence: float
    channel: str
    herb_id: int | None = None
    device_id: str = ""


class HistoryResponse(BaseModel):
    """识别历史响应。"""

    id: int
    result_name: str
    confidence: float
    channel: str
    herb_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
