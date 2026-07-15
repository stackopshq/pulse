"""Modèle de données (SQLModel).

Modèle d'équipe : les sources et catégories sont partagées entre tous les
utilisateurs ; l'état de lecture (lu/non-lu, favori) est propre à chaque
utilisateur via ``ArticleState``.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    color: str = "#6366f1"


class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    feed_url: str = Field(index=True, unique=True)
    site_url: Optional[str] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", index=True)
    is_active: bool = True

    # En-têtes de collecte conditionnelle.
    etag: Optional[str] = None
    last_modified: Optional[str] = None

    last_fetched_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Article(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("source_id", "guid", name="uq_article_source_guid"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    guid: str = Field(index=True)
    title: str
    url: Optional[str] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = Field(default=None, index=True)
    fetched_at: datetime = Field(default_factory=utcnow, index=True)


class ArticleState(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_state_user_article"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    article_id: int = Field(foreign_key="article.id", index=True)
    is_read: bool = False
    is_favorite: bool = False
    updated_at: datetime = Field(default_factory=utcnow)
