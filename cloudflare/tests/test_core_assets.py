from pathlib import Path

from app.skill.assets import DOCUMENTS
from app.skill.router import REFERENCE


def test_bundled_skill_is_canonical() -> None:
    root = Path(__file__).parents[2]
    assert DOCUMENTS["SKILL.md"] == (root / "SKILL.md").read_text(encoding="utf-8")
    for path in REFERENCE.values():
        assert DOCUMENTS[path] == (root / path).read_text(encoding="utf-8")
