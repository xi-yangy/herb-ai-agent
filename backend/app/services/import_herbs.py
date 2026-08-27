"""中草药知识库 CSV 导入脚本。

将 data/中草药知识库.csv 中的 100 味药材导入 herbs 表。

CSV 列与 Herb 模型字段映射：
- name            → name
- category        → category（药材分类）
- properties      → nature_flavor（性味归经）
- functions       → effects（功效主治）
- usage_dosage    → usage（用法用量）
- contraindications → contraindications（禁忌）
- safety_level    → safety_level（值映射：无毒→普通 / 小毒→慎用 / 有毒→毒性）
- similar_herbs   → similar_herbs（相似/易混淆品种，F4 用）

CSV 缺失的字段：source（来源）、toxicity（毒性说明）在此脚本补充/生成。

用法（在 backend/ 目录下）：
    python -m app.services.import_herbs
"""

import csv
import logging
import os

from sqlalchemy import select

import app.models  # noqa: F401  确保所有模型注册到 Base.metadata
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.herb import Herb

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

# CSV 相对 backend/ 目录的路径
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "中草药知识库.csv")

# safety_level 值映射：CSV 用词 → 模型枚举
SAFETY_LEVEL_MAP = {
    "无毒": "普通",
    "小毒": "慎用",
    "有毒": "毒性",
}

# 数据来源标注
SOURCE = "参考《中国药典》2020年版及常见中药学资料（示例编撰）"

# 毒性说明生成（CSV 未提供毒性说明，按安全等级给出通用表述）
TOXICITY_MAP = {
    "普通": "",
    "慎用": "含微量毒性或需谨慎使用的成分，须严格按剂量并在医师指导下使用。",
    "毒性": "含毒性成分，使用不当可危及健康。须经炮制、严格控量并遵医嘱，切勿自行服用。",
}


def map_safety_level(raw: str) -> str:
    """将 CSV 的 safety_level 文案映射为模型枚举值。"""
    key = (raw or "").strip()
    return SAFETY_LEVEL_MAP.get(key, "普通")


def parse_csv(path: str = DEFAULT_CSV_PATH) -> list[dict]:
    """解析 CSV 为导入字典列表（utf-8 带 BOM 兼容）。"""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            rows.append(row)
    return rows


def build_herb(row: dict) -> Herb:
    """将一行 CSV 数据映射为 Herb 对象。"""
    safety = map_safety_level(row.get("safety_level") or "")
    return Herb(
        name=(row.get("name") or "").strip(),
        safety_level=safety,
        source=SOURCE,
        category=(row.get("category") or "").strip(),
        similar_herbs=(row.get("similar_herbs") or "").strip(),
        nature_flavor=(row.get("properties") or "").strip(),
        effects=(row.get("functions") or "").strip(),
        usage=(row.get("usage_dosage") or "").strip(),
        contraindications=(row.get("contraindications") or "").strip(),
        toxicity=TOXICITY_MAP[safety],
        description="",
    )


def import_herbs(path: str = DEFAULT_CSV_PATH) -> int:
    """导入 CSV 药材到数据库（幂等：同名已存在则跳过）。返回新增条数。"""
    rows = parse_csv(path)
    created = 0
    skipped = 0
    with SessionLocal() as db:
        for row in rows:
            name = (row.get("name") or "").strip()
            exists = db.scalar(select(Herb).where(Herb.name == name))
            if exists:
                skipped += 1
                continue
            db.add(build_herb(row))
            created += 1
        db.commit()
    logger.info("CSV 导入完成：总 %s 条，新增 %s，跳过 %s", len(rows), created, skipped)
    return created


def main() -> None:
    """入口：导入并打印结果。"""
    logging.basicConfig(level=logging.INFO)
    count = import_herbs()
    logger.info("药材知识库导入完成，新增 %s 条。", count)


if __name__ == "__main__":
    main()
