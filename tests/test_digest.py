"""Tests de génération du digest."""

from datetime import datetime, timedelta, timezone

from pulse.digest import build_digest, render_markdown
from pulse.models import Article, Category, Rule, Source


def _setup(session):
    cat = Category(name="Sécurité", color="#ef4444")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    source = Source(title="Krebs", feed_url="http://k/feed", category_id=cat.id)
    session.add(source)
    session.commit()
    session.refresh(source)
    for i, title in enumerate(["CVE grave", "Patch Tuesday"]):
        session.add(Article(source_id=source.id, guid=f"g{i}", title=title))
    session.commit()
    return source


def test_build_digest_groups_by_category(session):
    _setup(session)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    data = build_digest(session, since)

    assert data["total_new"] == 2
    assert len(data["groups"]) == 1
    assert data["groups"][0]["category"] == "Sécurité"
    assert len(data["groups"][0]["articles"]) == 2


def test_build_digest_excludes_old_articles(session):
    _setup(session)
    # Fenêtre dans le futur : rien ne doit remonter.
    since = datetime.now(timezone.utc) + timedelta(days=1)
    data = build_digest(session, since)
    assert data["total_new"] == 0


def test_render_markdown_contains_titles(session):
    _setup(session)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    data = build_digest(session, since)
    md = render_markdown(data)
    assert "# Digest Pulse" in md
    assert "CVE grave" in md
    assert "Sécurité" in md


def test_digest_includes_alerts(session):
    source = _setup(session)
    from pulse.alerts import backfill_rule

    rule = Rule(name="Failles", keywords="CVE")
    session.add(rule)
    session.commit()
    session.refresh(rule)
    backfill_rule(session, rule)

    since = datetime.now(timezone.utc) - timedelta(days=1)
    data = build_digest(session, since)
    assert len(data["alerts"]) == 1
    assert "Alertes" in render_markdown(data)
