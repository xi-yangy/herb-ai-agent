"""识别接口模型。

注意：本阶段识别接口为占位实现（返回 501），此处仅预留响应结构，
供后续接入百度 API / 自建模型时使用。
"""

from pydantic import BaseModel


class RecognizeResponse(BaseModel):
    """识别结果响应（预留结构，P0 阶段实现）。"""

    name: str
    confidence: float
    channel: str
    safety_level: str
