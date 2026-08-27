"""基础日志配置。

复用标准 logging，仅设置 INFO 级别与统一格式。
注意：不打印请求体、图片等敏感数据。
"""

import logging


def setup_logging() -> None:
    """配置应用日志格式与级别。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
