from __future__ import annotations

import sqlite3
from pathlib import Path


class Statement:
    def __init__(self, connection: sqlite3.Connection, sql: str, values: tuple = ()) -> None:
        self.connection = connection
        self.sql = sql
        self.values = values

    def bind(self, *values):
        return Statement(self.connection, self.sql, values)

    async def all(self):
        rows = self.connection.execute(self.sql, self.values).fetchall()
        return {"results": [dict(row) for row in rows]}

    async def first(self):
        row = self.connection.execute(self.sql, self.values).fetchone()
        return dict(row) if row is not None else None

    async def run(self):
        cursor = self.connection.execute(self.sql, self.values)
        self.connection.commit()
        return {"meta": {"changes": cursor.rowcount}}


class D1Binding:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            (Path(__file__).parents[1] / "migrations" / "0001_initial.sql").read_text(encoding="utf-8")
        )

    def prepare(self, sql: str) -> Statement:
        return Statement(self.connection, sql)

    async def batch(self, statements: list[Statement]):
        with self.connection:
            for statement in statements:
                self.connection.execute(statement.sql, statement.values)


class R2Object:
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def arrayBuffer(self) -> bytes:
        return self.data


class R2Binding:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, content: bytes) -> None:
        self.objects[key] = content

    async def get(self, key: str) -> R2Object | None:
        return R2Object(self.objects[key]) if key in self.objects else None

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)
