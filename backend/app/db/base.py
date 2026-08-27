"""SQLAlchemy 声明式基类。

所有 ORM 模型均继承自 Base，用于建表与元数据管理。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
