"""识别历史路由（占位）。

本阶段不实现用户体系，接口返回空列表，供前端联调。
后续 P0 阶段接入用户身份与历史记录持久化。
"""

from fastapi import APIRouter

router = APIRouter(tags=["history"])


@router.get("/api/history")
def list_history() -> list[dict]:
    """识别历史列表（占位，返回空列表）。"""
    return []


@router.post("/api/history")
def create_history() -> dict:
    """新增识别历史（占位）。"""
    return {"detail": "历史记录写入将在后续阶段实现"}


@router.delete("/api/history")
def clear_history() -> dict:
    """清除历史（占位）。"""
    return {"detail": "历史清除将在后续阶段实现"}
