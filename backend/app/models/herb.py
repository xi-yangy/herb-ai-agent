"""药材知识库表。"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Herb(Base):
    """药材条目。

    safety_level 为 PRD 红线字段（普通/慎用/毒性），必填。
    以下为 P0 主链路补充的 PRD 知识字段：
    性味归经、功效主治、用法用量、禁忌、毒性说明等。
    """

    __tablename__ = "herbs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    # 安全等级：普通 / 慎用 / 毒性
    safety_level: Mapped[str] = mapped_column(
        Enum("普通", "慎用", "毒性", name="safety_level"), nullable=False
    )
    # 数据来源标注（如《中国药典》2020 年版 / 示例(编撰)）
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # 药材分类（如：根茎类 / 花类 / 果实类 / 全草类 / 动物类 等）
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # 相似/易混淆品种（逗号分隔，用于 F4 易混淆辨析提示）
    similar_herbs: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # 鉴别防雷警报：需防雷标签（如"易与断肠草混淆"，非空即触发前端防雷警报卡）
    warning_label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # 鉴别防雷警报：辨析警示文案（外观/毒性差异要点，高危字段需专家复核后上线）
    warning_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 别名/俗名/植物学名（逗号分隔，如金银花→忍冬），识别匹配别名兜底用
    alias: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # ==== P0 新增知识字段 ====
    # 性味归经，如“甘、微苦；温。归脾、肺经”
    nature_flavor: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # 功效主治
    effects: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 用法用量
    usage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 禁忌（含人群禁忌、食物相克等）
    contraindications: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 毒性说明（普通药材可留空/写“无毒”）
    toxicity: Mapped[str] = mapped_column(Text, nullable=False, default="")

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
