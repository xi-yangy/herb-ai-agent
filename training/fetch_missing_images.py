"""为训练集缺失的药材抓取示例图（一次性、可复跑）。

背景：百科页卡片需要示例缩略图。训练集只有 93 类，数据库 172 味药材中有 79 味
没有训练图。本脚本以数据库 herbs 表为准，减去 ``backend/static/herb_imgs/`` 已有
文件（含训练集导出的 93 张），得到缺图名单，多源搜索每味取第一张有效图下载，
压缩为 320x320 JPG 存入 ``backend/static/herb_imgs/<药名>.jpg``。

数据源（按优先级）：
1. **360 图片 API**（主源，稳定 JSON）：``https://image.so.com/j?q=<kw>``，取 ``list[].img``；
2. **必应图片**（备源，时好时坏）：``https://cn.bing.com/images/search`` 的 ``a.iusc`` m 属性 JSON 里 ``murl``；
3. **百度图片**（备源，风控严重，仅重试碰运气）：``/search/index`` 的 ``"objurl":"..."``。

选图策略（用户要求：不要水印明显的图、挑好的）：
- 过滤 URL 含 watermark/logo/shuiyin/wm 等水印标识的候选；
- 下载后校验：能解析、宽高 >=128px、字节数 >5KB，通过才入库；
- 失败自动换下一候选；全部失败记录失败名单，前端将降级为纯文字卡片。

合规：图片来自网络公开搜索结果，仅作教学演示展示，版权归原作者所有。

用法::

    # 1) 探针：只取候选不下载，确认各源能拿到图（约 30s）
    python training/fetch_missing_images.py --probe

    # 2) 实际抓取（约 3~6 分钟）
    python training/fetch_missing_images.py
"""

from __future__ import annotations

import argparse
import html as _html
import json
import logging
import random
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fetch_missing_images")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "herb_ai.db"
OUT_DIR = BASE_DIR / "backend" / "static" / "herb_imgs"
SIZE = 320
MIN_SIDE = 128
MIN_BYTES = 5 * 1024

# 图片 URL / 来源含以下关键词即视为水印风险候选，直接跳过
_WATERMARK_KEYS = (
    "watermark", "water_mark", "shuiyin", "add_watermark",
    "/wm", "wm=", "_logo", "logo.", "qiantucdn",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

DEFAULT_MAX_CANDIDATES = 12


# --------------------------------------------------------------------------- #
# 缺图名单
# --------------------------------------------------------------------------- #

def load_missing_names() -> list[str]:
    """读取数据库全部药材名，减去已有图片文件，返回缺图名单（保持数据库顺序）。"""
    conn = sqlite3.connect(DB_PATH)
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM herbs ORDER BY id")]
    finally:
        conn.close()
    existing = {p.stem for p in OUT_DIR.glob("*.jpg")} if OUT_DIR.is_dir() else set()
    missing = [n for n in names if n not in existing]
    logger.info("数据库药材 %d 味，已有图 %d 张，缺图 %d 味", len(names), len(existing), len(missing))
    return missing


# --------------------------------------------------------------------------- #
# 通用 HTTP 与 URL 工具
# --------------------------------------------------------------------------- #

def http_get(url: str, referer: str, timeout: float = 12.0) -> bytes | None:
    """带 UA/Referer/Accept-Language 发起 GET，成功返回 bytes，失败/超时返回 None。"""
    req = urllib.request.Request(url, headers={**_HEADERS, "Referer": referer})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:  # noqa: BLE001  网络异常统一降级
        logger.debug("GET 失败 %s：%s", url[:120], exc)
        return None


def _clean(url: str | None) -> str | None:
    """URL 清洗：仅保留 http(s) 且不含水印关键词的链接。"""
    if not url:
        return None
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    low = u.lower()
    if any(k in low for k in _WATERMARK_KEYS):
        return None
    return u


def _dedup_keep_order(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


# --------------------------------------------------------------------------- #
# 360 图片（主源，JSON API）
# --------------------------------------------------------------------------- #

def so360_candidates(kw: str) -> list[str]:
    """360 图片搜索候选（主源）。解析 JSON list[].img，并用宽高过滤小图。"""
    q = urllib.parse.quote(kw)
    url = f"https://image.so.com/j?q={q}&sn=0&pn=40"
    data = http_get(url, "https://image.so.com/")
    if not data:
        return []
    try:
        payload = json.loads(data.decode("utf-8", errors="ignore"))
    except ValueError:
        return []
    cands: list[str] = []
    for item in payload.get("list") or []:
        if not isinstance(item, dict):
            continue
        try:
            w, h = int(item.get("width") or 0), int(item.get("height") or 0)
        except (TypeError, ValueError):
            w, h = 0, 0
        if min(w, h) < MIN_SIDE:
            continue
        c = _clean(item.get("img"))
        if c:
            cands.append(c)
    return _dedup_keep_order(cands)


# --------------------------------------------------------------------------- #
# 必应图片（备源，HTML a.iusc 的 murl）
# --------------------------------------------------------------------------- #

def bing_candidates(kw: str) -> list[str]:
    """必应图片搜索候选（备源）。从搜索页 HTML 解析 a.iusc 的 m 属性 JSON 取 murl。"""
    q = urllib.parse.quote(kw)
    url = f"https://cn.bing.com/images/search?q={q}&form=HDRSC2"
    data = http_get(url, "https://cn.bing.com/")
    if not data:
        return []
    html = data.decode("utf-8", errors="ignore")
    attrs = re.findall(r'<a[^>]*class="iusc"[^>]*\sm="([^"]+)"', html)
    cands: list[str] = []
    for raw in attrs:
        m = _html.unescape(raw)
        try:
            obj = json.loads(m)
        except (ValueError, TypeError):
            continue
        c = _clean(obj.get("murl"))
        if c:
            cands.append(c)
    return _dedup_keep_order(cands)


# --------------------------------------------------------------------------- #
# 百度图片（备源，HTML 内嵌 JSON 的 objurl）
# --------------------------------------------------------------------------- #

def baidu_candidates(kw: str) -> list[str]:
    """百度图片搜索候选（备源）。解析搜索页 HTML 中 "objurl":"..." 的原图地址。"""
    q = urllib.parse.quote(kw)
    url = f"https://image.baidu.com/search/index?tn=baiduimage&word={q}"
    data = http_get(url, "https://image.baidu.com/")
    if not data:
        return []
    html = data.decode("utf-8", errors="ignore")
    # 风控时百度会返回极短页面，长度不足视为失败
    if len(html) < 50000:
        return []
    cands: list[str] = []
    for raw in re.findall(r'"objurl"\s*:\s*"([^"]+)"', html):
        u = _html.unescape(raw).replace("\\/", "/")
        u = urllib.parse.unquote(u)
        c = _clean(u)
        if c:
            cands.append(c)
    return _dedup_keep_order(cands)


# --------------------------------------------------------------------------- #
# 下载与入库
# --------------------------------------------------------------------------- #

def fetch_image(url: str, referer: str) -> bytes | None:
    """下载图片字节并做最小体积校验（<5KB 视为错误页/占位图）。"""
    data = http_get(url, referer)
    if data is None or len(data) < MIN_BYTES:
        return None
    return data


def save_valid_image(data: bytes, out_path: Path) -> bool:
    """校验并压缩图片，成功落盘返回 True。"""
    try:
        with Image.open(BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            w, h = img.size
            if min(w, h) < MIN_SIDE:
                logger.debug("图片过小 %dx%d，跳过", w, h)
                return False
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            img = img.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)
            img.save(out_path, format="JPEG", quality=85)
        return True
    except Exception as exc:  # noqa: BLE001  单图损坏不影响整体
        logger.debug("图片校验/压缩失败：%s", exc)
        return False


def process_one(name: str, max_candidates: int, probe: bool = False, skip_first: int = 0) -> tuple[bool, str, list[str]]:
    """为单个药材抓图。返回 (成功?, 说明, 候选 URL 列表)。

    skip_first > 0 时跳过前 N 个候选，用于局部换图（避开水印明显的旧图）。
    """
    sources = (
        ("so360", so360_candidates, "https://image.so.com/"),
        ("bing", bing_candidates, "https://cn.bing.com/"),
        ("baidu", baidu_candidates, "https://image.baidu.com/"),
    )
    cands: list[str] = []
    src_used: list[str] = []
    for src_name, fn, referer in sources:
        got = fn(name)
        if got:
            src_used.append(src_name)
        cands.extend(c for c in got if c not in cands)
        if len(cands) >= max_candidates + skip_first:
            break
        time.sleep(0.3)
    cands = cands[skip_first : skip_first + max_candidates]

    if not cands:
        return False, "三源均未取到候选", []
    if probe:
        return True, f"探针：{'+'.join(src_used)} 共 {len(cands)} 个候选", cands

    for url in cands:
        data = fetch_image(url, "https://image.so.com/")
        if data is None:
            continue
        if save_valid_image(data, OUT_DIR / f"{name}.jpg"):
            return True, url[:100], cands
        time.sleep(0.3)
    return False, f"尝试 {len(cands)} 个候选均无效", cands


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description="为训练集缺失药材抓取示例图")
    parser.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES, help="每味最多尝试的候选数")
    parser.add_argument("--sleep", type=float, default=0.8, help="每味处理间隔秒数（礼貌抓取）")
    parser.add_argument("--probe", action="store_true", help="探针模式：只取候选不下载，输出每味候选数与样例 URL")
    parser.add_argument("--limit", type=int, default=0, help="仅处理前 N 味（0=全部；仅对缺图名单生效）")
    parser.add_argument("--skip-first", type=int, default=0, help="跳过前 N 个候选（局部换图避开水印旧图）")
    args = parser.parse_args()

    missing = load_missing_names()
    if not missing:
        logger.info("没有缺图药材，无需抓取。")
        return 0

    if args.limit:
        missing = missing[: args.limit]

    # 探针模式：随机抽样最多 8 味，快速验证各源能否取到候选
    if args.probe:
        sample = random.sample(missing, min(8, len(missing)))
        logger.info("探针模式：随机抽样 %d 味验证", len(sample))
        for n in sample:
            ok, note, cands = process_one(n, args.max_candidates, probe=True)
            sample_urls = " | ".join(c[:90] for c in cands[:2])
            logger.info("  %s -> %s\n      样例：%s", n, note, sample_urls or "(空)")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    order = missing[:]
    rng.shuffle(order)

    ok, failed, total_bytes = 0, 0, 0
    failed_names: list[str] = []
    for idx, name in enumerate(order, 1):
        time.sleep(args.sleep)
        success, note, _ = process_one(name, args.max_candidates, probe=False, skip_first=args.skip_first)
        if success:
            ok += 1
            size = (OUT_DIR / f"{name}.jpg").stat().st_size
            total_bytes += size
            logger.info("[%d/%d] %s OK（%.1f KB）", idx, len(order), name, size / 1024)
        else:
            failed += 1
            failed_names.append(name)
            logger.warning("[%d/%d] %s 失败：%s", idx, len(order), name, note)

    logger.info("抓取完成：成功 %d 味，失败 %d 味，总大小 %.2f MB", ok, failed, total_bytes / 1024 / 1024)
    if failed_names:
        logger.warning("失败名单（可删除错误图后重跑补齐）：%s", "、".join(failed_names))
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
