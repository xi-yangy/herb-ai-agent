"""多模态问答接口模型（F12）。

问答请求携带问题与识别结果上下文（药材名 + 知识库字段），
后端结合上下文调用 Qwen 生成回答；Qwen 不可用时降级为知识库结构化展示。
"""

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """问答请求：用户问题 + 识别结果上下文。

    herb_context 由前端从识别结果（result.herb）透传，含功效/用法/禁忌/毒性等字段；
    为空时后端仅凭 herb_name 回答或直接降级。
    """

    question: str = Field(..., min_length=1, description="用户问题")
    herb_name: str = Field(..., description="识别结果药材名称")
    herb_context: dict | None = Field(default=None, description="药材知识库上下文字段")


class QAResponse(BaseModel):
    """问答响应。

    fallback 标记是否触发知识库降级展示（前端据此标注「已切换至本地知识库展示」）。
    disclaimer 为每条回答强制附带的免责声明。
    """

    answer: str
    fallback: bool = False
    disclaimer: str = "以上内容仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师。"
