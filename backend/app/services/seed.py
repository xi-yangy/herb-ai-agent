"""示例药材数据录入脚本（P0 主链路演示数据）。

本脚本仅录入编撰的示例药材，source 统一标注为「示例(编撰)」，
以明确区分真实数据，避免误导。后续批量真实数据由第二批提供后替换。

用法（在 backend/ 目录下）：
    python -m app.services.seed
"""

import logging

from sqlalchemy import select

import app.models  # noqa: F401  确保所有模型注册到 Base.metadata
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.herb import Herb

# 确保建表（seed 脚本独立运行，不依赖 main 模块加载）
Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

# 编撰示例药材（字段对齐 herb 表 P0 结构）
EXAMPLE_HERBS: list[dict] = [
    {
        "name": "黄芪",
        "safety_level": "普通",
        "source": "示例(编撰)",
        "nature_flavor": "甘，微温。归脾、肺经",
        "effects": "补气升阳，固表止汗，利水消肿，生津养血，行滞通痹。用于气虚乏力、食少便溏、中气下陷、久泻脱肛、自汗、水肿、血虚萎黄等。",
        "usage": "煎服，9~30g。蜜炙可增强补中益气作用。",
        "contraindications": "表实邪盛、气滞湿阻、食积内停、阴虚阳亢者慎用。不宜与降压药、强心苷类同用。",
        "toxicity": "常规剂量下无毒。",
        "description": "豆科植物蒙古黄芪或膜荚黄芪的干燥根，为常用补气药。",
    },
    {
        "name": "附子",
        "safety_level": "毒性",
        "source": "示例(编撰)",
        "nature_flavor": "辛、甘，大热；有毒。归心、肾、脾经",
        "effects": "回阳救逆，补火助阳，散寒止痛。用于亡阳虚脱、肢冷脉微、心阳不足、虚寒吐泻、脘腹冷痛、肾阳虚衰、阳痿宫冷、阴寒水肿等。",
        "usage": "内服须炮制（制附子），先煎、久煎（0.5~1 小时）以降低毒性，3~15g。",
        "contraindications": "孕妇禁用；不宜与半夏、瓜蒌、贝母、白蔹、白及同用；阴虚阳亢、真热假寒者忌用。",
        "toxicity": "含乌头碱类生物碱，剧毒。生品禁内服，中毒可致心律失常、呼吸衰竭，严重可致死。",
        "description": "毛茛科植物乌头的子根加工品，为回阳救逆第一要药，须严格炮制与医嘱使用。",
        "warning_label": "易与白附子等根茎类药材混淆",
        "warning_message": "附子（乌头子根）与白附子、半夏等根茎类药材外观易混淆。附子生品含乌头碱类剧毒成分，未经充分炮制严禁内服；与其他药材混淆误用可致严重中毒。切勿仅凭外观自行辨认或采食，务必由专业药师核对后再使用。",
    },
]


def seed_herbs() -> int:
    """写入示例药材，返回新增条数（已存在则跳过）。"""
    created = 0
    with SessionLocal() as db:
        for item in EXAMPLE_HERBS:
            exists = db.scalar(select(Herb).where(Herb.name == item["name"]))
            if exists:
                logger.info("跳过已存在药材：%s", item["name"])
                continue
            db.add(Herb(**item))
            created += 1
        db.commit()
    return created


def main() -> None:
    """入口：录入示例数据并打印结果。"""
    count = seed_herbs()
    logger.info("示例药材录入完成，新增 %s 条。", count)


if __name__ == "__main__":
    main()
