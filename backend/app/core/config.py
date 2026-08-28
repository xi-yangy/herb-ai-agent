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

    # 本地自训练模型（PyTorch）识别配置（经 .env 提供，未启用时回退百度）
    # 是否启用本地模型（需配置模型与类别文件路径后开启）
    local_enabled: bool = False
    # 训练产物 .pth 模型权重路径
    local_model_path: str = ""
    # 训练产物 classes.txt 类别清单路径（每行一个类别名，行号=索引）
    local_classes_path: str = ""
    # 本地模型置信度阈值：低于该值回退百度兜底
    local_confidence_threshold: float = 0.6
    # 本地模型 top-k 数量（供"相似品种列表"展示）
    local_top_k: int = 5
    # 本地模型推理设备：空=自动（cuda 优先，否则 cpu）；可显式指定 cuda/cpu
    local_device: str = ""

    # 通义千问（Qwen）多模态问答凭证（经 .env 提供，不硬编码）
    qwen_api_key: str = ""
    # 是否启用 Qwen 问答（未配置凭证时自动降级为知识库结构化展示）
    qwen_enabled: bool = False
    # Qwen 模型（OpenAI 兼容协议模型名；默认用更快的 qwen-turbo 以降低回答耗时）
    qwen_model: str = "qwen-turbo"
    # Qwen OpenAI 兼容接口 base_url（默认标准 DashScope；专属云/自定义域名可覆盖）
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # Qwen 调用超时（秒）：超时即降级，避免阻塞结果页（专属云首调需较长）
    qwen_timeout: float = 30.0

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
