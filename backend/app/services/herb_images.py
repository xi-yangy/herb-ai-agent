"""药材示例图片 URL 映射服务。

百科页需要为每味药材展示一张示例缩略图。图片文件由外部脚本（训练集选图 /
网络抓取）生成在 ``backend/static/herb_imgs/<药名>.jpg``，本模块在进程启动时
扫描一次目录建立「药名 → 文件名」缓存，并提供 ``image_url_for(name)`` 按药名
返回可访问的静态图 URL（未命中返回空串，前端据此降级为纯文字卡片）。
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

# backend/static/herb_imgs/（基于本文件绝对路径推导，不依赖启动工作目录）
HERB_IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "herb_imgs"
# 静态服务前缀：与 main.py 中 app.mount("/api/static", ...) 保持一致
STATIC_PREFIX = "/api/static/herb_imgs"

# 启动时扫描一次的缓存：文件名 stem（药名）→ 完整文件名
_IMAGE_FILES: dict[str, str] = {}


def _rebuild_cache() -> None:
    """全量重建图片缓存（幂等，目录不存在时为空缓存）。"""
    global _IMAGE_FILES
    _IMAGE_FILES = {}
    if HERB_IMG_DIR.is_dir():
        for path in HERB_IMG_DIR.glob("*.jpg"):
            _IMAGE_FILES[path.stem] = path.name
    logger.info("药材示例图缓存：%d 张（%s）", len(_IMAGE_FILES), HERB_IMG_DIR)


def image_url_for(name: str) -> str:
    """按药材名返回示例图 URL；未命中返回空串。

    精确匹配文件名 stem（如「人参」→ ``/api/static/herb_imgs/人参.jpg``），
    中文文件名经 URL 编码，保证浏览器可访问。
    """
    if not _IMAGE_FILES:
        _rebuild_cache()
    fname = _IMAGE_FILES.get(name or "")
    if not fname:
        return ""
    return f"{STATIC_PREFIX}/{quote(fname)}"


# 模块加载即建立缓存（幂等；目录后续新增图片可手动调用 _rebuild_cache 刷新）
_rebuild_cache()
