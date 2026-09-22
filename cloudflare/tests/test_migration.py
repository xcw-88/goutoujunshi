import sqlite3
from pathlib import Path


def test_initial_migration_has_cloud_storage_tables() -> None:
    sql = (Path(__file__).parents[1] / "migrations" / "0001_initial.sql").read_text(
        encoding="utf-8"
    )
    connection = sqlite3.connect(":memory:")
    connection.executescript(sql)
    tables = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {
        "people",
        "relationships",
        "memories",
        "conversations",
        "messages",
        "uploaded_files",
        "settings",
    } <= tables
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(uploaded_files)")
    }
    assert "object_key" in columns
    assert "path" not in columns
