"""Données initiales (catégories thématiques IT par défaut)."""

from sqlmodel import Session, select

from .db import engine
from .models import Category

DEFAULT_CATEGORIES = [
    ("Sécurité / CVE", "#ef4444"),
    ("Cloud", "#3b82f6"),
    ("DevOps", "#22c55e"),
    ("Langages & Dev", "#a855f7"),
    ("Réseau", "#f59e0b"),
    ("IA / Data", "#ec4899"),
    ("Général", "#64748b"),
]


def seed_default_categories() -> None:
    with Session(engine) as session:
        if session.exec(select(Category)).first() is not None:
            return
        for name, color in DEFAULT_CATEGORIES:
            session.add(Category(name=name, color=color))
        session.commit()
