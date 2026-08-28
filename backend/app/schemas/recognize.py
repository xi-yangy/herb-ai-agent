"""识别接口模型。

识别接口契约与真实引擎保持一致：
前端上传 base64 图片 → 后端调用 RecognitionService → 返回药材结果。
本阶段由 MockRecognizer 返回写死示例药材。
"""

from pydantic import BaseModel, Field

from app.schemas.herb import HerbResponse, SimilarHerb


class RecognizeRequest(BaseModel):
    """识别请求：前端上传的图片（base64，可含 data:image 前缀）。"""

    image_base64: str = Field(..., description="图片 base64 编码")
    # 触发通道：camera / album
    channel: str = Field(default="camera", description="触发通道：camera 或 album")


class WarningInfo(BaseModel):
    """鉴别防雷警报信息（由知识库药材的防雷字段组装，非空即触发前端警报卡）。"""

    label: str = ""          # 需防雷标签，如"易与断肠草混淆"
    message: str = ""        # 辨析警示文案
    herb_name: str = ""      # 命中的本药材名称


class RecognizeResult(BaseModel):
    """单条识别结果（含完整药材知识）。

    channel 为实际命中通道（local/baidu/mock）；similar 为低置信度降级用的
    相似品种候选列表；low_confidence 标记是否触发"改判相似品种"。
    """

    name: str
    confidence: float
    safety_level: str
    channel: str = "mock"
    similar: list[SimilarHerb] = []
    low_confidence: bool = False
    herb: HerbResponse | None = None
    # 鉴别防雷警报（由命中药材组装，无防雷信息时为空对象）
    warning: WarningInfo = Field(default_factory=WarningInfo)


class RecognizeResponse(BaseModel):
    """识别响应。"""

    name: str
    confidence: float
    channel: str
    safety_level: str
    similar: list[SimilarHerb] = []
    low_confidence: bool = False
    herb: HerbResponse | None = None
    # 鉴别防雷警报（由命中药材组装，无防雷信息时为空对象）
    warning: WarningInfo = Field(default_factory=WarningInfo)
