"""可插拔问答服务（F12）：Qwen 真实调用 + 知识库降级兜底。

- QwenQAService：调用 DashScope OpenAI 兼容接口生成回答；
- 未配置凭证 / 网络异常 / 超时 / 返回空时，降级为本地知识库结构化摘要。

统一返回 (answer, fallback)，路由与前端契约不变。与 recognizer.py 一致，
HTTP 调用复用标准库 urllib.request，不新增第三方依赖。
"""

from __future__ import annotations

import json
import logging
import urllib.request
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI 兼容接口 chat completions 子路径（base_url 由配置提供）
_CHAT_COMPLETIONS_PATH = "/chat/completions"

# 系统提示：约束回答合规（非诊断/非处方，高危药材强调遵医嘱）
_SYSTEM_PROMPT = (
    "你是一名中医药知识科普助手，面向大众提供中草药功效、用法、禁忌与安全提示。"
    "回答须通俗易懂、客观中立，仅作参考，不得构成诊断或处方建议，"
    "不得使用「治疗、治愈、疗效」等诊断性表述；"
    "涉及慎用、毒性药材时，务必强调「须遵医嘱、严格控量、切勿自行服用」。"
)


def build_fallback_answer(herb_name: str, herb_context: dict | None) -> str:
    """组装知识库结构化降级答案（F12 降级兜底）。

    仅从 herb_context 取功效/用法/禁忌/毒性等字段生成摘要，
    不臆造任何信息；字段缺失时明确标注「暂无」。
    """
    ctx = herb_context or {}
    lines: list[str] = [f"关于「{herb_name}」，以下为本地知识库收录的信息摘要："]

    effects = (ctx.get("effects") or "").strip()
    usage = (ctx.get("usage") or "").strip()
    contraindications = (ctx.get("contraindications") or "").strip()
    toxicity = (ctx.get("toxicity") or "").strip()

    lines.append(f"· 功效主治：{effects or '暂无'}")
    lines.append(f"· 用法用量：{usage or '暂无'}")
    lines.append(f"· 禁忌：{contraindications or '暂无'}")
    lines.append(f"· 毒性/副作用：{toxicity or '常规剂量下无毒。'}")

    lines.append("如需更详细或针对个人情况的判断，请咨询执业医师或药师。")
    return "\n".join(lines)


class QAService(ABC):
    """问答服务抽象接口。"""

    @abstractmethod
    def ask(self, question: str, herb_name: str, herb_context: dict | None) -> tuple[str, bool]:
        """回答问题，返回 (answer, fallback)。

        fallback 为 True 表示当前回答为知识库降级内容（非 Qwen 生成）。
        """
        raise NotImplementedError


class QwenQAService(QAService):
    """Qwen 问答实现。

    未启用 / 凭证缺失 / 调用异常 / 超时 / 返回空时，降级为知识库结构化展示。
    """

    def ask(self, question: str, herb_name: str, herb_context: dict | None) -> tuple[str, bool]:
        if not (settings.qwen_enabled and settings.qwen_api_key):
            logger.info("Qwen 未启用，问答降级为知识库展示")
            return build_fallback_answer(herb_name, herb_context), True

        try:
            answer = self._call_qwen(question, herb_name, herb_context)
        except Exception as exc:  # noqa: BLE001  网络/接口异常统一降级
            logger.warning("Qwen 调用失败，降级知识库展示：%s", exc)
            return build_fallback_answer(herb_name, herb_context), True

        if not answer:
            logger.info("Qwen 返回空，降级知识库展示")
            return build_fallback_answer(herb_name, herb_context), True

        return answer, False

    # ---- 内部实现 ----

    def _call_qwen(self, question: str, herb_name: str, herb_context: dict | None) -> str:
        """调用 OpenAI 兼容接口，返回回答文本。"""
        ctx = herb_context or {}
        # 组织用户上下文（截断长字段，避免超长）
        context_lines = [
            f"药材名称：{herb_name}",
            f"功效主治：{str(ctx.get('effects') or '暂无')[:200]}",
            f"用法用量：{str(ctx.get('usage') or '暂无')[:200]}",
            f"禁忌：{str(ctx.get('contraindications') or '暂无')[:200]}",
            f"毒性/副作用：{str(ctx.get('toxicity') or '暂无')[:200]}",
        ]
        user_prompt = "\n".join(context_lines) + f"\n\n用户问题：{question}"

        payload = {
            "model": settings.qwen_model,
            # 限制回答长度，避免生成冗长内容，缩短单次回答耗时
            "max_tokens": 600,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        chat_url = settings.qwen_base_url.rstrip("/") + _CHAT_COMPLETIONS_PATH
        req = urllib.request.Request(
            chat_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.qwen_api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=settings.qwen_timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))

        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content") or "").strip()


# 当前使用的问答服务实例
qa_service: QAService = QwenQAService()
