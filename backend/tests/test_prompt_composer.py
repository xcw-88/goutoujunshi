from datetime import datetime, timezone

from app.schemas.memory import MemoryContext, MemoryRead
from app.skill.composer import PromptComposer
from app.skill.types import RouteDecision, SkillDocument


def memory(scope: str, key: str, value: str) -> MemoryRead:
    now = datetime.now(timezone.utc)
    return MemoryRead(
        id=f"{scope}-{key}",
        person_id=None if scope == "user" else "person-a",
        scope=scope,  # type: ignore[arg-type]
        key=key,
        value=value,
        confidence="low" if scope == "hypothesis" else None,
        source="assistant_inference" if scope == "hypothesis" else "user_explicit",
        occurred_at=None,
        created_at=now,
        updated_at=now,
    )


def test_composer_keeps_semantic_boundaries() -> None:
    messages = PromptComposer().compose(
        core_skill=SkillDocument("SKILL.md", "狗头军师", "先接住情绪，再分清事实。"),
        route=RouteDecision("reply_help", "normal", ("references/reply.md",)),
        user_message="我该怎么回？",
        references=[SkillDocument("references/reply.md", "回复", "给一句可发送成品。")],
        person={"id": "person-a", "display_name": "对象A"},
        relationship={"status": "dating"},
        memories=MemoryContext(
            confirmed_facts=[memory("object", "mbti", "INFP")],
            events=[memory("event", "invitation", "接受邀约")],
            hypotheses=[memory("hypothesis", "intent", "可能感兴趣")],
        ),
    )

    system = messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "我该怎么回？"}
    assert "## CONFIRMED FACTS" in system
    assert "## EVENTS" in system
    assert "## HYPOTHESES — NOT FACTS" in system
    assert "Never promote them to facts" in system
    assert "references/reply.md" in system


def test_composer_enforces_context_budget_and_history_roles() -> None:
    composer = PromptComposer(max_system_chars=1200, max_history_chars=40)
    messages = composer.compose(
        core_skill=SkillDocument("SKILL.md", "Skill", "core"),
        route=RouteDecision("general_relationship_analysis", "normal", ()),
        user_message="current",
        references=[SkillDocument("references/large.md", "Large", "x" * 5000)],
        history=[
            {"role": "system", "content": "must be dropped"},
            {"role": "user", "content": "old user"},
            {"role": "assistant", "content": "old assistant"},
        ],
    )

    assert len(messages[0]["content"]) <= 1200
    assert all(item["content"] != "must be dropped" for item in messages)
    assert messages[-1]["content"] == "current"
