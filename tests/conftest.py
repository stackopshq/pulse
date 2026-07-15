"""Configuration des tests : base SQLite temporaire et isolée."""

import os
import pathlib
import tempfile

# Doit être défini AVANT tout import de pulse (settings lit l'environnement).
_DB_PATH = pathlib.Path(tempfile.gettempdir()) / "pulse_test.db"
if _DB_PATH.exists():
    _DB_PATH.unlink()
os.environ["PULSE_DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["PULSE_SECRET_KEY"] = "test-secret-key"

import pytest  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import pulse.models  # noqa: E402,F401  (peuple les métadonnées)
from pulse.db import engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    SQLModel.metadata.drop_all(engine)
    init_db()
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session():
    from sqlmodel import Session

    with Session(engine) as s:
        yield s


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from pulse.main import app

    # Sans context manager : le lifespan (et le scheduler) ne démarre pas.
    return TestClient(app)
