"""药材知识库表。"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Herb(Base):
    """药材条目。

    safety_level 为 PRD 红线字段（普通/慎用/毒性），必填。
    """

    __tablename__ = "herbs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    # 安全等级：普通 / 慎用 / 毒性
    safety_level: Mapped[str] = mapped_column(
        Enum("普通", "慎用", "毒性", name="safety_level"), nullable=False
    )
    # 数据来源标注（如《中国药典》2020 年版）
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # 预留：性味归经 / 功效主治等字段在 P0 阶段逐步补齐
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
