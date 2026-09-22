"""Small async adapter over the D1 prepared-statement binding.

No SQL or user input is interpolated into identifiers; callers supply fixed SQL
and values travel through D1's bind operation.
"""

from __future__ import annotations

from typing import Any


def _native(value: Any) -> Any:
    if hasattr(value, "to_py"):
        return value.to_py()
    return value


def _field(value: Any, name: str) -> Any:
    value = _native(value)
    if isinstance(value, dict):
        return value.get(name)
    return _native(getattr(value, name, None))


class Database:
    def __init__(self, binding: Any) -> None:
        self.binding = binding

    def _statement(self, sql: str, values: tuple[Any, ...]) -> Any:
        statement = self.binding.prepare(sql)
        return statement.bind(*values) if values else statement

    async def all(self, sql: str, *values: Any) -> list[dict[str, Any]]:
        result = await self._statement(sql, values).all()
        return [dict(_native(row)) for row in (_field(result, "results") or [])]

    async def one(self, sql: str, *values: Any) -> dict[str, Any] | None:
        row = await self._statement(sql, values).first()
        return dict(_native(row)) if row is not None else None

    async def run(self, sql: str, *values: Any) -> int:
        result = await self._statement(sql, values).run()
        meta = _field(result, "meta")
        return int(_field(meta, "changes") or 0)

    async def batch(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        await self.binding.batch([self._statement(sql, values) for sql, values in statements])
