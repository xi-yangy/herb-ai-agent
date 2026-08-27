"""识别历史表。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecognitionHistory(Base):
    """识别记录（PRD：名称、置信度、触发通道、时间戳、关联药材 ID）。"""

    __tablename__ = "recognition_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    herb_id: Mapped[int | None] = mapped_column(
        ForeignKey("herbs.id", ondelete="SET NULL"), nullable=True
    )
    # 识别结果名称（可能尚未收录到知识库，故冗余存名）
    result_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # 触发通道：自建模型 / 百度兜底
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
