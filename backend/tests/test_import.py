"""中草药知识库 CSV 导入与映射测试。

覆盖 CSV 解析、safety_level 值映射、字段映射与导入幂等性，
对应 PRD Q2 质量基线与 F5/F6 知识库扩充。
"""

import os

from app.services.import_herbs import (
    build_herb,
    import_herbs,
    map_safety_level,
    parse_csv,
)

# CSV 文件绝对路径（相对 backend/ 目录向上两级到 data/）
CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "中草药知识库.csv"
)


def test_map_safety_level() -> None:
    """safety_level 值映射：无毒→普通 / 小毒→慎用 / 有毒→毒性。"""
    assert map_safety_level("无毒") == "普通"
    assert map_safety_level("小毒") == "慎用"
    assert map_safety_level("有毒") == "毒性"
    assert map_safety_level("未知值") == "普通"  # 未知回落普通
    assert map_safety_level("") == "普通"


def test_parse_csv_contains_expected_count() -> None:
    """CSV 可解析，且含常见药材（含空行过滤）。"""
    rows = parse_csv(CSV_PATH)
    assert len(rows) >= 50  # 首批目标 50-100 种
    names = {r["name"].strip() for r in rows}
    assert "黄芪" in names
    assert "附子" in names
    assert "金银花" in names


def test_build_herb_field_mapping() -> None:
    """CSV 行字段映射到 Herb 对象正确。"""
    row = {
        "name": "黄芪",
        "category": "根茎类",
        "properties": "甘，微温。归脾、肺经",
        "functions": "补气升阳，固表止汗",
        "usage_dosage": "9~30g",
        "contraindications": "表实邪盛者慎用",
        "safety_level": "无毒",
        "similar_herbs": "人参、白术、防风",
    }
    herb = build_herb(row)
    assert herb.name == "黄芪"
    assert herb.category == "根茎类"
    assert herb.nature_flavor == "甘，微温。归脾、肺经"
    assert herb.effects == "补气升阳，固表止汗"
    assert herb.usage == "9~30g"
    assert herb.contraindications == "表实邪盛者慎用"
    assert herb.safety_level == "普通"  # 无毒→普通
    assert herb.similar_herbs == "人参、白术、防风"
    assert herb.source  # source 已补充
    assert herb.toxicity == ""  # 普通药材毒性说明为空
    assert herb.warning_label == ""  # 未配置防雷字段时为空
    assert herb.warning_message == ""


def test_build_herb_anti_deception_fields() -> None:
    """CSV 防雷字段（warning_label/warning_message）正确映射到 Herb。"""
    row = {
        "name": "金银花",
        "safety_level": "无毒",
        "similar_herbs": "连翘、蒲公英",
        "warning_label": "易与断肠草混淆",
        "warning_message": "金银花与剧毒植物断肠草（钩吻）在野外极易混淆，切勿自行采食。",
    }
    herb = build_herb(row)
    assert herb.warning_label == "易与断肠草混淆"
    assert "断肠草" in herb.warning_message
    assert herb.alias == ""  # 未配置别名时为空


def test_build_herb_alias_field() -> None:
    """CSV 别名（alias）字段正确映射到 Herb。"""
    row = {
        "name": "金银花",
        "safety_level": "无毒",
        "alias": "忍冬,金银藤",
    }
    herb = build_herb(row)
    assert herb.alias == "忍冬,金银藤"


def test_build_herb_toxicity_generated() -> None:
    """毒性药材的 toxicity 说明自动生成。"""
    row = {"name": "附子", "safety_level": "有毒"}
    herb = build_herb(row)
    assert herb.safety_level == "毒性"
    assert "毒性" in herb.toxicity


def test_import_herbs_idempotent(client) -> None:
    """导入幂等：同一 CSV 导入两次，药材总数不重复。"""
    first = import_herbs(CSV_PATH)
    second = import_herbs(CSV_PATH)
    # 第二次导入时应全部跳过
    assert second == 0
    # 数据库药材总数 = 首次新增数（未重复）
    total = client.get("/api/herbs").json()
    assert len(total) >= first
