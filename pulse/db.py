"""Moteur SQLModel et gestion des sessions."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    connect_args=connect_args,
)


def init_db() -> None:
    """Crée les tables si elles n'existent pas (dev/MVP ; Alembic en prod)."""
    from . import models  # noqa: F401  (enregistre les tables)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
