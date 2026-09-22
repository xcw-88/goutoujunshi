import asyncio

from src.db import Database
from tests.fake_bindings import D1Binding


def test_d1_adapter_uses_bound_values() -> None:
    async def check() -> None:
        binding = D1Binding()
        db = Database(binding)
        await db.run(
            "INSERT INTO people (id, display_name, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            "one", "O'Reilly", "", "2026-01-01", "2026-01-01",
        )
        assert (await db.one("SELECT display_name FROM people WHERE id = ?", "one"))["display_name"] == "O'Reilly"
        assert await db.all("SELECT id FROM people WHERE id = ?", "missing") == []

    asyncio.run(check())
