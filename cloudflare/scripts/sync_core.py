"""Bundle the local API's pure contracts and canonical Skill assets for Workers.

The generated package is ignored by Git. The original Skill remains the only
editable source; deployment cannot accidentally diverge from its text.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "cloudflare" / "src" / "app"
SCHEMAS = (
    "chat.py",
    "conversation.py",
    "file.py",
    "imports.py",
    "memory.py",
    "person.py",
    "settings.py",
)
SKILL_MODULES = ("composer.py", "router.py", "types.py")


def sync() -> None:
    (TARGET / "schemas").mkdir(parents=True, exist_ok=True)
    (TARGET / "skill").mkdir(parents=True, exist_ok=True)
    for directory in (TARGET, TARGET / "schemas", TARGET / "skill"):
        (directory / "__init__.py").write_text("", encoding="utf-8")
    for filename in SCHEMAS:
        shutil.copyfile(ROOT / "backend" / "app" / "schemas" / filename, TARGET / "schemas" / filename)
    for filename in SKILL_MODULES:
        shutil.copyfile(ROOT / "backend" / "app" / "skill" / filename, TARGET / "skill" / filename)

    documents = {"SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8")}
    for source in sorted((ROOT / "references").rglob("*.md")):
        documents[source.relative_to(ROOT).as_posix()] = source.read_text(encoding="utf-8")
    encoded = json.dumps(documents, ensure_ascii=False, sort_keys=True)
    (TARGET / "skill" / "assets.py").write_text(f"DOCUMENTS = {encoded}\n", encoding="utf-8")


if __name__ == "__main__":
    sync()
