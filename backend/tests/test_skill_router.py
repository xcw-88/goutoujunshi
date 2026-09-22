import pytest

from app.skill.router import SkillRouter


@pytest.mark.parametrize(
    ("message", "expected_intent", "expected_fragment"),
    [
        ("她最近忽冷忽热，我该怎么看这段关系？", "general_relationship_analysis", "02-亲密关系心理学总论"),
        ("她说最近很忙，我怎么回复她？", "reply_help", "实战话术编排器"),
        ("帮我分析这份聊天记录", "conversation_analysis", "09-在线约会与数字关系"),
        ("我们吵架后一直冷战", "conflict", "07-沟通冲突与修复"),
    ],
)
def test_routes_common_intents(message: str, expected_intent: str, expected_fragment: str) -> None:
    decision = SkillRouter().route(message)

    assert decision.intent == expected_intent
    assert expected_fragment in decision.references[0]
    assert 1 <= len(decision.references) <= 3


def test_routes_safety_before_other_intents() -> None:
    decision = SkillRouter().route("他威胁并跟踪我，我该怎么回复？")

    assert decision.intent == "legal_safety"
    assert decision.risk == "high"
    assert decision.references == ("references/knowledge/17-中国法律安全与危机转介.md",)


def test_routes_uploaded_chat_without_loading_everything() -> None:
    decision = SkillRouter().route("请看看这份导出", file_types=["text/csv"])

    assert decision.intent == "conversation_analysis"
    assert len(decision.references) == 2
    assert any("ChatLab聊天记录分析适配" in item for item in decision.references)
