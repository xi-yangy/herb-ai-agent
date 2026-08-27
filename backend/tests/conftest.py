"""pytest 夹具。

提供 TestClient 直连应用实例，用于冒烟测试。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """返回 FastAPI 应用的 TestClient。"""
    return TestClient(app)
