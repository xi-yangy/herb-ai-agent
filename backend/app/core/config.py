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

    # ==== 本地自建模型（主通道）配置 ====
    # 是否启用本地模型主通道（默认关闭；未配置模型文件时自动回退百度/Mock）
    model_enabled: bool = False
    # 模型文件路径（onnx 或 pytorch .pt/.pth）
    model_path: str = ""
    # 类别清单文件路径（json/txt，一行一类或 JSON 数组，顺序需与模型输出对齐）
    model_labels: str = ""
    # 本地模型置信度阈值：低于该值视为低置信度，触发百度兜底/相似品种降级
    model_confidence_threshold: float = 0.6
    # 相似品种 top-k 数量（本地与百度共用，供"低置信度降级列表"展示）
    model_top_k: int = 5

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
