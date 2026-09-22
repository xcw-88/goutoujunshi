from __future__ import annotations

import json
from typing import Any

from app.schemas.memory import MemoryContext
from app.skill.types import RouteDecision, SkillDocument


class PromptComposer:
    """Compose the complete model input in one auditable location."""

    def __init__(self, max_system_chars: int = 24_000, max_history_chars: int = 12_000) -> None:
        self.max_system_chars = max_system_chars
        self.max_history_chars = max_history_chars

    def compose(
        self,
        *,
        core_skill: SkillDocument,
        route: RouteDecision,
        user_message: str,
        references: list[SkillDocument],
        person: dict[str, Any] | None = None,
        relationship: dict[str, Any] | None = None,
        memories: MemoryContext | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        facts = memories.confirmed_facts if memories else []
        events = memories.events if memories else []
        hypotheses = memories.hypotheses if memories else []
        fixed_sections = [
            self._section("CORE SKILL RULES", core_skill.content),
            self._section(
                "CURRENT TASK",
                json.dumps(
                    {"intent": route.intent, "risk": route.risk},
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
            self._section("CURRENT PERSON PROFILE", self._json_or_unknown(person)),
            self._section("CURRENT RELATIONSHIP", self._json_or_unknown(relationship)),
            self._section("CONFIRMED FACTS", self._models_or_unknown(facts)),
            self._section("EVENTS", self._models_or_unknown(events)),
            self._section("HYPOTHESES — NOT FACTS", self._models_or_unknown(hypotheses)),
            self._section(
                "EVIDENCE BOUNDARIES",
                "Treat hypotheses only as tentative explanations. Never promote them to facts. "
                "Do not infer facts from names, MBTI, avatars, gender, message position, or tone. "
                "Mark missing information as unknown. For images, use only visible content and "
                "state when text is unreadable or cropped.",
            ),
            self._section(
                "OUTPUT CONSTRAINTS",
                "Respond in the user's language. Separate confirmed observations, reasonable "
                "interpretations, and unknowns. Lead with a clear, actionable recommendation; "
                "preserve consent, safety, dignity, and the user's final choice.",
            ),
        ]
        fixed = "\n\n".join(fixed_sections)
        remaining = max(self.max_system_chars - len(fixed) - 64, 0)
        reference_text = self._fit_references(references, remaining)
        system = f"{fixed}\n\n{self._section('SELECTED REFERENCES', reference_text)}"
        system = system[: self.max_system_chars]

        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        messages.extend(self._fit_history(history or []))
        messages.append({"role": "user", "content": user_message})
        return messages

    def _fit_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        used = 0
        for item in reversed(history[-12:]):
            if item.get("role") not in {"user", "assistant"}:
                continue
            content = str(item.get("content", ""))[:4000]
            if used + len(content) > self.max_history_chars:
                break
            result.append({"role": item["role"], "content": content})
            used += len(content)
        result.reverse()
        return result

    @staticmethod
    def _section(title: str, content: str) -> str:
        return f"## {title}\n{content.strip()}"

    @staticmethod
    def _json_or_unknown(value: dict[str, Any] | None) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str) if value else "Unknown"

    @staticmethod
    def _models_or_unknown(values: list[Any]) -> str:
        if not values:
            return "None recorded"
        payload = [item.model_dump(mode="json") for item in values]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _fit_references(references: list[SkillDocument], budget: int) -> str:
        if not references or budget <= 0:
            return "No reference excerpt fits the current context budget."
        per_document = max(budget // len(references), 1)
        excerpts = []
        for document in references:
            header = f"### {document.path}\n"
            available = max(per_document - len(header), 0)
            excerpt = document.content[:available]
            if len(document.content) > available:
                excerpt = f"{excerpt}\n[truncated for context budget]"
            excerpts.append(f"{header}{excerpt}")
        return "\n\n".join(excerpts)[:budget]

