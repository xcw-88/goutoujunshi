from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import build_engine, get_db, init_database
from app.main import app
from app.core.config import Settings, get_settings


@pytest.fixture
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = build_engine(tmp_path / "test.db")
    init_database(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        GOUTOU_DATABASE_PATH="test.db",
        GOUTOU_UPLOAD_DIR=str(session.bind.url.database) + "-uploads",  # type: ignore[union-attr]
    )
    app.state.skip_database_init = True
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.skip_database_init = False
