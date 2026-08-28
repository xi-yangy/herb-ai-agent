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

    # token 签名密钥（生产环境务必通过环境变量覆盖）
    token_secret: str = "herb-ai-dev-secret-change-me"

    # 调试开关
    debug: bool = True

    # 百度植物识别 API 凭证（经 .env 提供，不硬编码）
    baidu_api_key: str = ""
    baidu_secret_key: str = ""
    # 是否启用百度识别（未配置凭证时自动回退 Mock）
    baidu_enabled: bool = False
    # 百度识别置信度阈值：低于该值不直接给结论，降级为相似品种
    baidu_confidence_threshold: float = 0.6
    # 百度相似品种 top-k 数量（供"低置信度降级列表"展示）
    baidu_top_k: int = 5

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
