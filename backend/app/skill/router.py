from __future__ import annotations

from app.skill.types import RouteDecision


REFERENCE = {
    "general_relationship_analysis": "references/knowledge/02-亲密关系心理学总论.md",
    "reply_help": "references/practical/实战话术编排器：从一句回复到后续分支.md",
    "conversation_analysis": "references/knowledge/09-在线约会与数字关系.md",
    "chat_import": "references/practical/ChatLab聊天记录分析适配.md",
    "conflict": "references/knowledge/07-沟通冲突与修复.md",
    "breakup": "references/knowledge/15-分手背叛与关系修复.md",
    "dating": "references/knowledge/06-吸引约会与关系启动.md",
    "personality": "references/knowledge/04-MBTI人格与匹配.md",
    "intimacy": "references/knowledge/08-同意边界性与亲密.md",
    "legal_safety": "references/knowledge/17-中国法律安全与危机转介.md",
}


class SkillRouter:
    """Small deterministic router for selecting one to three domain references."""

    high_risk_terms = (
        "家暴",
        "暴力",
        "殴打",
        "掐脖",
        "跟踪",
        "堵门",
        "下药",
        "强迫",
        "胁迫",
        "威胁",
        "勒索",
        "自杀",
        "自伤",
        "伤人",
        "报警",
        "保护令",
    )
    reply_terms = ("怎么回", "如何回", "回复她", "回复他", "回什么", "话术", "帮我回")
    conversation_terms = ("聊天记录", "聊天截图", "截图", "对话记录", "聊天分析")
    conflict_terms = ("吵架", "冲突", "冷战", "道歉", "争执", "沟通问题")
    breakup_terms = ("分手", "复合", "前任", "背叛", "出轨")
    dating_terms = ("邀约", "约会", "暧昧", "追求", "表白", "第一次见面")
    personality_terms = ("mbti", "人格", "依恋", "回避型", "焦虑型")
    intimacy_terms = ("同意", "边界", "亲密", "性行为", "避孕")

    def route(
        self,
        message: str,
        *,
        relationship_status: str | None = None,
        file_types: list[str] | None = None,
    ) -> RouteDecision:
        text = f"{message} {relationship_status or ''}".lower()
        types = {item.lower() for item in (file_types or [])}

        if self._contains(text, self.high_risk_terms):
            return RouteDecision(
                intent="legal_safety",
                risk="high",
                references=(REFERENCE["legal_safety"],),
            )

        intents: list[str] = []
        if self._contains(text, self.reply_terms):
            intents.append("reply_help")
        if self._contains(text, self.conversation_terms) or types.intersection(
            {"image/png", "image/jpeg", "image/webp", "text/plain", "text/csv", "application/json"}
        ):
            intents.append("conversation_analysis")
            if types.intersection({"text/plain", "text/csv", "application/json", "text/markdown"}):
                intents.append("chat_import")
        if self._contains(text, self.conflict_terms):
            intents.append("conflict")
        if self._contains(text, self.breakup_terms):
            intents.append("breakup")
        if self._contains(text, self.dating_terms):
            intents.append("dating")
        if self._contains(text, self.personality_terms):
            intents.append("personality")
        if self._contains(text, self.intimacy_terms):
            intents.append("intimacy")
        if not intents:
            intents.append("general_relationship_analysis")

        unique_intents = list(dict.fromkeys(intents))
        references = tuple(REFERENCE[intent] for intent in unique_intents[:3])
        risk = "sensitive" if "intimacy" in unique_intents else "normal"
        return RouteDecision(intent=unique_intents[0], risk=risk, references=references)

    @staticmethod
    def _contains(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

