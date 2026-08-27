"""应用配置。

使用 pydantic-settings 从环境变量 / .env 文件加载配置。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置。"""

    # 数据库连接串（SQLite 起步）
    database_url: str = "sqlite:///./herb_ai.db"

    # CORS 允许来源（逗号分隔字符串）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 调试开关
    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """将逗号分隔的 CORS 来源解析为列表。"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取缓存的配置单例。"""
    return Settings()


settings = get_settings()
