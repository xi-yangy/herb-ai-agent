"""收藏表。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Favorite(Base):
    """用户收藏的药材。

    本批（P0 主链路）暂不实现用户体系，故以 device_id 标识匿名收藏；
    user_id 留空以保持向后兼容，第二批登录接入后再收紧为必填。
    """

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("device_id", "herb_id", name="uq_device_herb"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 匿名设备标识（未登录时使用）；登录后置空，以 user_id 维度为准。
    # device_id 可空：SQLite 中 UNIQUE 允许多个 NULL，故不同用户的收藏不会冲突。
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    herb_id: Mapped[int] = mapped_column(ForeignKey("herbs.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
