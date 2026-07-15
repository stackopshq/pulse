"""Tests des règles de veille et alertes."""

from sqlmodel import select

from pulse.alerts import article_matches, backfill_rule, evaluate_rules, parse_keywords
from pulse.models import AlertHit, Article, Rule, Source


def test_parse_keywords():
    assert parse_keywords("CVE, Kubernetes ,, log4j") == ["cve", "kubernetes", "log4j"]
    assert parse_keywords("") == []


def test_article_matches_case_insensitive():
    article = Article(source_id=1, guid="g", title="Nouvelle CVE critique", summary="")
    assert article_matches(article, ["cve"]) is True
    assert article_matches(article, ["kubernetes"]) is False
    assert article_matches(article, []) is False


def _seed_source_articles(session):
    source = Source(title="Sec", feed_url="http://sec/feed")
    session.add(source)
    session.commit()
    session.refresh(source)
    ids = []
    for i, title in enumerate(["Faille CVE-2026-1", "Sortie de Python 3.13", "RCE dans nginx"]):
        a = Article(source_id=source.id, guid=f"g{i}", title=title)
        session.add(a)
        session.commit()
        session.refresh(a)
        ids.append(a.id)
    return ids


def test_evaluate_rules_creates_hits(session):
    ids = _seed_source_articles(session)
    session.add(Rule(name="Sécurité", keywords="CVE, RCE"))
    session.commit()

    created = evaluate_rules(session, ids)
    assert created == 2  # CVE + RCE

    # Idempotent : pas de doublon.
    assert evaluate_rules(session, ids) == 0
    assert len(session.exec(select(AlertHit)).all()) == 2


def test_inactive_rule_ignored(session):
    ids = _seed_source_articles(session)
    session.add(Rule(name="Off", keywords="CVE", is_active=False))
    session.commit()
    assert evaluate_rules(session, ids) == 0


def test_backfill_rule(session):
    _seed_source_articles(session)
    rule = Rule(name="Python", keywords="python")
    session.add(rule)
    session.commit()
    session.refresh(rule)

    created = backfill_rule(session, rule)
    assert created == 1
    hit = session.exec(select(AlertHit).where(AlertHit.rule_id == rule.id)).first()
    assert hit is not None
