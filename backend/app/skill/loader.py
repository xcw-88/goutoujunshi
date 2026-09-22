from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import REPOSITORY_ROOT
from app.skill.types import SkillDocument


class InvalidReferenceError(ValueError):
    pass


class SkillLoader:
    """Read the repository's canonical skill assets without copying them."""

    def __init__(self, root: Path = REPOSITORY_ROOT) -> None:
        self.root = root.resolve()
        self.references_root = (self.root / "references").resolve()

    @lru_cache(maxsize=1)
    def load_skill(self) -> SkillDocument:
        return self._read(self.root / "SKILL.md", "SKILL.md")

    @lru_cache(maxsize=64)
    def load_reference(self, relative_path: str) -> SkillDocument:
        normalized = relative_path.replace("\\", "/")
        if not normalized.startswith("references/") or not normalized.endswith(".md"):
            raise InvalidReferenceError("reference must be a Markdown file under references/")
        target = (self.root / normalized).resolve()
        if not target.is_relative_to(self.references_root):
            raise InvalidReferenceError("reference path escapes references/")
        if not target.is_file():
            raise InvalidReferenceError(f"reference does not exist: {relative_path}")
        return self._read(target, normalized)

    def load_references(self, paths: list[str] | tuple[str, ...]) -> list[SkillDocument]:
        if len(paths) > 3:
            raise InvalidReferenceError("a request may load at most three references")
        return [self.load_reference(path) for path in paths]

    def clear_cache(self) -> None:
        self.load_skill.cache_clear()
        self.load_reference.cache_clear()

    @staticmethod
    def _read(target: Path, relative_path: str) -> SkillDocument:
        if not target.is_file():
            raise FileNotFoundError(target)
        content = target.read_text(encoding="utf-8")
        title = next(
            (line.removeprefix("# ").strip() for line in content.splitlines() if line.startswith("# ")),
            target.stem,
        )
        return SkillDocument(path=relative_path, title=title, content=content)

