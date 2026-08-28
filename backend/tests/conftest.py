"""pytest 夹具。

为测试提供隔离的临时 SQLite 数据库（避免污染/依赖开发库 herb_ai.db），
并注入示例药材数据，返回 FastAPI 应用的 TestClient。
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# 必须在导入 app.main（及其 engine）之前设置环境变量：
# - 独立临时数据库，避免污染开发库；
# - 测试环境禁用百度识别（走 Mock），保证用例稳定且不依赖网络。
_tmp_dir = tempfile.mkdtemp(prefix="herb-ai-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp_dir, 'test.db')}"
os.environ["BAIDU_ENABLED"] = "false"

from app.main import app  # noqa: E402  （导入顺序依赖上面的环境变量）
from app.services.seed import seed_herbs  # noqa: E402

# 测试库建表后注入示例药材（黄芪/附子），供识别/知识库用例使用。
seed_herbs()


@pytest.fixture
def client() -> TestClient:
    """返回 FastAPI 应用的 TestClient。"""
    return TestClient(app)
