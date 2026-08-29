"""``_match_herb`` 名称匹配逻辑单元测试。

覆盖匹配顺序：精确 → 去常见后缀 → 补常见后缀 → 别名整词 → 受限包含
（endswith + 修饰词 ≤2 字 + 最长优先），以及防误匹配反例。
对应 PRD Q2「高危判定/降级逻辑单测」要求。

说明：
- 测试库为 conftest 创建的独立临时 SQLite，已 seed 黄芪/附子；
  本模块在导入时补充构造药材（人参/枸杞子/金银花/芪），用于覆盖各匹配分支。
- 注意「人参果」会被既有「去单字后缀」逻辑误配为「人参」（stripped 后精确命中），
  属历史行为、不在本次受限包含匹配范围内，故不作为反例用例。
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.herb import Herb
from app.services.recognizer import _match_herb

# 构造药材：覆盖补后缀（枸杞子）、别名（金银花）、包含匹配最长优先（芪 vs 黄芪）等分支
_EXTRA_HERBS: list[dict] = [
    {"name": "人参", "safety_level": "普通"},
    {"name": "枸杞子", "safety_level": "普通"},
    # 金银花字段与 test_core_flow.test_match_herb_by_alias 期望一致，
    # 避免测试间插入同名药材字段不一致导致断言互相污染
    {
        "name": "金银花",
        "safety_level": "普通",
        "alias": "忍冬,二花",
        "warning_label": "易与断肠草混淆",
        "warning_message": "测试辨析文案",
    },
    {"name": "芪", "safety_level": "普通"},
]


def _ensure_extra_herbs() -> None:
    """向临时测试库补充构造药材（同名幂等，避免重复插入）。"""
    with SessionLocal() as db:
        for item in _EXTRA_HERBS:
            exists = db.scalar(select(Herb).where(Herb.name == item["name"]))
            if exists:
                continue
            db.add(Herb(**item))
        db.commit()


_ensure_extra_herbs()


def _match(name: str) -> Herb | None:
    """在临时库中执行一次名称匹配。"""
    with SessionLocal() as db:
        return _match_herb(db, name)


# ---- 匹配顺序正向用例 ----

def test_exact_match() -> None:
    """精确匹配（第 1 步）。"""
    assert _match("黄芪") is not None
    assert _match("黄芪").name == "黄芪"


def test_strip_suffix_match() -> None:
    """去常见后缀匹配（第 2 步）：「黄芪片」→「黄芪」。"""
    result = _match("黄芪片")
    assert result is not None
    assert result.name == "黄芪"


def test_expand_suffix_match() -> None:
    """补常见后缀匹配（第 3 步）：「枸杞」→「枸杞子」。"""
    result = _match("枸杞")
    assert result is not None
    assert result.name == "枸杞子"


def test_alias_match() -> None:
    """别名整词匹配（第 4 步）：「忍冬」→ 金银花。"""
    result = _match("忍冬")
    assert result is not None
    assert result.name == "金银花"


def test_containment_match() -> None:
    """受限包含匹配（第 5 步）：双字产地前缀 + 标准名。"""
    for name in ("蒙古黄芪", "膜荚黄芪"):
        result = _match(name)
        assert result is not None, f"{name} 应命中黄芪"
        assert result.name == "黄芪"


def test_containment_longest_priority() -> None:
    """受限包含匹配多候选命中时取名称最长者（「野黄芪」以「芪」「黄芪」结尾，取「黄芪」）。"""
    result = _match("野黄芪")
    assert result is not None
    assert result.name == "黄芪"


# ---- 防误匹配反例 ----

def test_containment_reject_too_long_modifier() -> None:
    """长度差超过 2 不命中：如「内蒙古黄芪」（差 3）不得误配「黄芪」。"""
    assert _match("内蒙古黄芪") is None


def test_containment_reject_unrelated_name() -> None:
    """非后缀关系不命中：百度返回「乌头」不得误配「附子」（库中附子无乌头别名）。"""
    assert _match("乌头") is None


def test_unknown_name_returns_none() -> None:
    """知识库未收录名称返回 None，维持未收录降级链路。"""
    assert _match("不存在品种") is None


def test_empty_name_returns_none() -> None:
    """空名称返回 None。"""
    assert _match("") is None
