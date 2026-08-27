"""隐私授权表。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PrivacyConsent(Base):
    """用户隐私授权记录（相机 / 相册 / 麦克风等）。

    以 device_id（匿名设备维度）为主关联，登录后也可用 user_id 关联；
    两者可空其一，保持向后兼容。
    """

    __tablename__ = "privacy_consents"
    __table_args__ = (
        UniqueConstraint("device_id", "consent_type", name="uq_consent_device_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 匿名设备标识（本阶段主维度）
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    # 授权类型：camera / album / microphone
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
