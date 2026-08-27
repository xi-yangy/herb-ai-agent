"""FastAPI 应用工厂。

负责注册路由、CORS、异常处理，并在启动时自动建表。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.routers import favorites, health, herbs, history, recognize


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    setup_logging()

    app = FastAPI(
        title="多模态中草药图像识别智能体",
        description="图像识别 + 用药安全 + 专业信息的一体化服务（骨架阶段）",
        version="0.1.0",
    )

    # CORS：允许前端开发服务器跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(health.router)
    app.include_router(recognize.router)
    app.include_router(herbs.router)
    app.include_router(history.router)
    app.include_router(favorites.router)

    return app


app = create_app()

# 首次运行自动建表（SQLite 起步）。
# 注意：显式在模块加载时建表，而非依赖 startup 事件，
# 以兼容 TestClient 直连与测试场景。
Base.metadata.create_all(bind=engine)
