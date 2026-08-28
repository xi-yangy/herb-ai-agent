"""多模态问答接口冒烟测试（F12）。

Qwen 未配置凭证（测试环境 qwen_enabled 默认 false）时应自动降级为
知识库结构化展示，返回 fallback=true，不阻断主流程。
对应 PRD Q2 质量基线与 F12 功能验收的工程可运行性验证。
"""

from fastapi.testclient import TestClient


def test_qa_falls_back_without_qwen(client: TestClient) -> None:
    """未启用 Qwen 时，问答应返回 200 且触发知识库降级。"""
    resp = client.post(
        "/api/qa",
        json={
            "question": "它有什么禁忌？",
            "herb_name": "附子",
            "herb_context": {
                "effects": "回阳救逆，补火助阳，散寒止痛",
                "usage": "内服须炮制，先煎、久煎，3~15g",
                "contraindications": "孕妇禁用；不宜与半夏、瓜蒌等同用",
                "toxicity": "含乌头碱类生物碱，剧毒",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert data["fallback"] is True
    # 降级答案应含知识库字段关键词
    assert "附子" in data["answer"]
    assert "禁忌" in data["answer"]
    # 免责声明必须存在（合规红线）
    assert "不构成诊断或处方" in data["disclaimer"]


def test_qa_fallback_without_context(client: TestClient) -> None:
    """未传知识库上下文时，仍应降级返回结构化摘要（字段标注暂无）。"""
    resp = client.post("/api/qa", json={"question": "怎么用", "herb_name": "黄芪"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert data["fallback"] is True


def test_qa_rejects_empty_question(client: TestClient) -> None:
    """空问题应返回 422 校验错误。"""
    resp = client.post("/api/qa", json={"question": "", "herb_name": "黄芪"})
    assert resp.status_code == 422
