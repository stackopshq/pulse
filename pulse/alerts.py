"""Évaluation des règles de veille (alertes par mots-clés)."""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from .models import AlertHit, Article, Rule

logger = logging.getLogger("pulse.alerts")


def parse_keywords(raw: str) -> list[str]:
    """Découpe une liste de mots-clés séparés par des virgules (nettoyée)."""
    return [kw.strip().lower() for kw in raw.split(",") if kw.strip()]


def _article_haystack(article: Article) -> str:
    parts = [article.title or "", article.summary or "", article.content or ""]
    return " ".join(parts).lower()


def article_matches(article: Article, keywords: list[str]) -> bool:
    if not keywords:
        return False
    haystack = _article_haystack(article)
    return any(kw in haystack for kw in keywords)


def evaluate_rules(session: Session, article_ids: list[int]) -> int:
    """Confronte les articles donnés aux règles actives. Crée les hits manquants.

    Retourne le nombre de nouvelles alertes créées.
    """
    if not article_ids:
        return 0

    rules = list(session.exec(select(Rule).where(Rule.is_active == True)).all())  # noqa: E712
    if not rules:
        return 0

    compiled = [(rule, parse_keywords(rule.keywords)) for rule in rules]
    created = 0

    for article_id in article_ids:
        article = session.get(Article, article_id)
        if article is None:
            continue
        for rule, keywords in compiled:
            if not article_matches(article, keywords):
                continue
            exists = session.exec(
                select(AlertHit).where(
                    AlertHit.rule_id == rule.id,
                    AlertHit.article_id == article_id,
                )
            ).first()
            if exists is None:
                session.add(AlertHit(rule_id=rule.id, article_id=article_id))
                created += 1

    if created:
        session.commit()
        logger.info("%s nouvelle(s) alerte(s) créée(s)", created)
    return created


def backfill_rule(session: Session, rule: Rule) -> int:
    """Applique une règle à tous les articles existants (à sa création)."""
    if not rule.is_active:
        return 0
    ids = [a.id for a in session.exec(select(Article)).all()]
    keywords = parse_keywords(rule.keywords)
    created = 0
    for article_id in ids:
        article = session.get(Article, article_id)
        if article and article_matches(article, keywords):
            exists = session.exec(
                select(AlertHit).where(
                    AlertHit.rule_id == rule.id,
                    AlertHit.article_id == article_id,
                )
            ).first()
            if exists is None:
                session.add(AlertHit(rule_id=rule.id, article_id=article_id))
                created += 1
    if created:
        session.commit()
    return created
