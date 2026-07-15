"""Tests d'import/export OPML."""

from sqlmodel import select

from pulse.models import Category, Source
from pulse.opml import export_opml, import_opml

SAMPLE = """<?xml version="1.0"?>
<opml version="2.0">
  <head><title>Test</title></head>
  <body>
    <outline text="Sécurité">
      <outline type="rss" text="Krebs" xmlUrl="https://krebsonsecurity.com/feed/" htmlUrl="https://krebsonsecurity.com"/>
    </outline>
    <outline type="rss" text="Hacker News" xmlUrl="https://news.ycombinator.com/rss"/>
  </body>
</opml>"""


def test_import_opml_creates_sources_and_categories(session):
    added = import_opml(session, SAMPLE)
    assert added == 2

    sources = session.exec(select(Source)).all()
    urls = {s.feed_url for s in sources}
    assert "https://krebsonsecurity.com/feed/" in urls
    assert "https://news.ycombinator.com/rss" in urls

    cat = session.exec(select(Category).where(Category.name == "Sécurité")).first()
    assert cat is not None
    krebs = session.exec(
        select(Source).where(Source.feed_url == "https://krebsonsecurity.com/feed/")
    ).first()
    assert krebs.category_id == cat.id


def test_import_opml_is_idempotent(session):
    assert import_opml(session, SAMPLE) == 2
    # Deuxième import : rien de nouveau.
    assert import_opml(session, SAMPLE) == 0


def test_export_roundtrip(session):
    import_opml(session, SAMPLE)
    xml = export_opml(session)
    assert "krebsonsecurity.com/feed" in xml
    assert "news.ycombinator.com/rss" in xml
    assert "Sécurité" in xml
