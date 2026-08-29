"""多模态问答路由（F12）。

接收识别结果上下文 + 用户问题，调用 Qwen 问答服务生成回答；
Qwen 不可用时降级为知识库结构化展示，不阻断主流程。
"""

import logging

from fastapi import APIRouter

from app.schemas.qa import QARequest, QAResponse
from app.services.qa import qa_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["qa"])


@router.post("/api/qa", response_model=QAResponse)
def ask(req: QARequest) -> QAResponse:
    """多模态问答：结合识别结果上下文回答问题。"""
    answer, fallback = qa_service.ask(
        req.question,
        req.herb_name,
        req.herb_context,
        req.image_base64,
    )
    logger.info(
        "问答完成：药材 %s，通道 %s",
        req.herb_name,
        "fallback" if fallback else "qwen",
    )
    return QAResponse(answer=answer, fallback=fallback)
