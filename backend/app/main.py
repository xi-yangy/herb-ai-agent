"""FastAPI 应用工厂。

负责注册路由、CORS、异常处理，并在启动时自动建表。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.routers import auth, favorites, health, herbs, history, privacy, qa, recognize
from app.services.herb_images import HERB_IMG_DIR


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    setup_logging()

    app = FastAPI(
        title="herb-ai-agent",
        description="Multimodal Chinese herbal medicine recognition, safety warning and professional info service",
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
    app.include_router(auth.router)
    app.include_router(privacy.router)
    app.include_router(qa.router)

    # 药材示例图静态目录（/api/static/herb_imgs/<药名>.jpg）
    # 挂在 /api/static 前缀：前端 axios baseURL 为 /api 且 Vite 代理只转发 /api，前端零配置
    app.mount("/api/static", StaticFiles(directory=HERB_IMG_DIR.parent), name="static")

    return app


app = create_app()

# 首次运行自动建表（SQLite 起步）。
# 注意：显式在模块加载时建表，而非依赖 startup 事件，
# 以兼容 TestClient 直连与测试场景。
Base.metadata.create_all(bind=engine)
