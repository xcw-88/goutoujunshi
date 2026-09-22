import pytest

from app.skill.loader import InvalidReferenceError, SkillLoader


def test_loads_canonical_skill_and_reference() -> None:
    loader = SkillLoader()

    skill = loader.load_skill()
    reference = loader.load_reference("references/knowledge/02-亲密关系心理学总论.md")

    assert skill.path == "SKILL.md"
    assert "先接住情绪" in skill.content
    assert reference.title == "亲密关系心理学总论"


def test_rejects_escape_and_bulk_loading() -> None:
    loader = SkillLoader()

    with pytest.raises(InvalidReferenceError):
        loader.load_reference("references/../SKILL.md")
    with pytest.raises(InvalidReferenceError):
        loader.load_references(
            [
                "references/knowledge/01-证据分级与内容边界.md",
                "references/knowledge/02-亲密关系心理学总论.md",
                "references/knowledge/03-依恋理论与情绪调节.md",
                "references/knowledge/04-MBTI人格与匹配.md",
            ]
        )
