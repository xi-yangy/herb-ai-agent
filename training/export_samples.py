"""从训练集为每类药材抽取 1 张代表图，压缩导出到后端静态目录（一次性、可复跑）。

背景：百科页卡片需要示例缩略图。训练集为 ImageFolder 结构（类别名=文件夹名），
本脚本只读遍历训练集，每类按固定随机种子选 1 张代表图，Pillow 中心裁剪为正方形、
缩放到 ``size`` 后以 JPG(quality=85) 输出到 ``backend/static/herb_imgs/<类别名>.jpg``，
文件名与类别名严格一致，供后端静态服务与前端百科页缩略图使用。

特点：
- 幂等覆盖：重复运行会覆盖同名输出；
- 可复现：每类使用 ``Random(f"{seed}:{类别名}")`` 选图，同类结果固定；
- 只读访问项目外训练集，输出全部落在项目内 ``backend/static/herb_imgs/``。

用法::

    python training/export_samples.py
    python training/export_samples.py --data-dir D:/Code/data --size 320 --seed 42
"""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

from PIL import Image, ImageOps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("export_samples")

# 支持的图片扩展名（训练集以 jpg/png 为主）
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def pick_and_export(class_dir: Path, out_path: Path, size: int, seed: int) -> tuple[str, int] | None:
    """从类别目录随机选 1 张图，压缩导出到 out_path。

    返回 (源文件名, 输出字节数)；目录无有效图片时返回 None。
    """
    images = sorted(p for p in class_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)
    if not images:
        logger.warning("类别目录无图片：%s", class_dir)
        return None

    # 每类独立的随机源，保证同类选择可复现、且不受其他类影响
    rng = random.Random(f"{seed}:{class_dir.name}")
    chosen = images[rng.randrange(len(images))]

    try:
        with Image.open(chosen) as img:
            img = ImageOps.exif_transpose(img)  # 修正相机方向
            img = img.convert("RGB")
            # 中心裁剪正方形后缩放，避免拉伸变形
            w, h = img.size
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            img.save(out_path, format="JPEG", quality=85)
    except Exception as exc:  # noqa: BLE001  单图损坏不阻塞整类
        logger.warning("处理失败 %s（跳过）：%s", chosen, exc)
        return None

    return chosen.name, out_path.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description="从训练集每类抽取 1 张代表图导出为百科缩略图")
    parser.add_argument("--data-dir", type=str, default="D:/Code/data", help="训练集根目录（含 train/）")
    parser.add_argument("--out", type=str, default="", help="输出目录（默认 backend/static/herb_imgs）")
    parser.add_argument("--size", type=int, default=320, help="输出边长（正方形）")
    parser.add_argument("--seed", type=int, default=42, help="选图随机种子")
    parser.add_argument("--only", nargs="*", default=None, help="仅处理指定类别名（其余跳过；用于局部换图）")
    args = parser.parse_args()

    train_dir = Path(args.data_dir) / "train"
    if not train_dir.is_dir():
        logger.error("找不到训练目录：%s", train_dir)
        return 1

    # 输出目录固定位于项目内：training/export_samples.py -> 项目根/backend/static/herb_imgs
    out_dir = Path(args.out) if args.out else (Path(__file__).resolve().parent.parent / "backend" / "static" / "herb_imgs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 只统计真正的类别目录（ImageFolder 约定），跳过隐藏项与杂项文件
    classes = [d for d in sorted(train_dir.iterdir()) if d.is_dir() and not d.name.startswith(".")]
    if args.only is not None:
        classes = [d for d in classes if d.name in args.only]
        logger.info("按 --only 过滤后类别数：%d（%s）", len(classes), "、".join(args.only))
    else:
        logger.info("训练集类别数：%d（目录：%s）", len(classes), train_dir)

    ok, failed, total_bytes = 0, 0, 0
    for class_dir in classes:
        out_path = out_dir / f"{class_dir.name}.jpg"
        result = pick_and_export(class_dir, out_path, args.size, args.seed)
        if result is None:
            failed += 1
            continue
        src_name, size_bytes = result
        ok += 1
        total_bytes += size_bytes
        logger.info("  %-8s <- %s（%.1f KB）", class_dir.name, src_name, size_bytes / 1024)

    logger.info("完成：成功 %d 张，失败 %d 张，总大小 %.2f MB -> %s", ok, failed, total_bytes / 1024 / 1024, out_dir)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
