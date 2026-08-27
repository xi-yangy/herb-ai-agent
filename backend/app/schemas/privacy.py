"""隐私授权接口模型。"""

from pydantic import BaseModel, Field

# 支持的授权类型
CONSENT_TYPES = {"camera", "album", "microphone"}


class ConsentUpdate(BaseModel):
    """更新某一项授权状态。"""

    consent_type: str = Field(..., description="授权类型：camera/album/microphone")
    granted: bool = Field(..., description="是否已授权")


class ConsentResponse(BaseModel):
    """单项授权状态响应。"""

    consent_type: str
    granted: bool
