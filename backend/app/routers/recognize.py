"""识别路由（占位）。

本阶段不实现真实识别逻辑，返回 501 提示未实现。
后续 P0 阶段接入百度 API / 自建模型后替换。
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["recognize"])


@router.post("/api/recognize")
async def recognize() -> JSONResponse:
    """图片识别（占位，待接入识别引擎）。"""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "识别功能尚未实现，将在后续阶段接入识别引擎"},
    )
