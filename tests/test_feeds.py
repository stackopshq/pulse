"""Tests de collecte : parsing, extraction, déduplication."""

from datetime import datetime, timezone

from sqlmodel import select

from pulse.feeds import _entry_guid, _extract_content, _parse_date, _store_result
from pulse.models import Article, Source


def test_entry_guid_prefers_id():
    assert _entry_guid({"id": "abc", "link": "http://x"}) == "abc"
    assert _entry_guid({"link": "http://x"}) == "http://x"
    assert _entry_guid({"title": "t"}) == "t"
    assert _entry_guid({}) == ""


def test_parse_date():
    entry = {"published_parsed": (2026, 7, 15, 10, 30, 0, 0, 0, 0)}
    assert _parse_date(entry) == datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc)
    assert _parse_date({}) is None


def test_extract_content_fallback_to_summary():
    assert _extract_content({"content": [{"value": "corps"}]}) == "corps"
    assert _extract_content({"summary": "résumé"}) == "résumé"


def _make_result(source_id, entries):
    return {
        "source_id": source_id,
        "status": "ok",
        "entries": entries,
        "etag": '"e1"',
        "last_modified": None,
        "error": None,
    }


def test_store_result_dedup(session):
    source = Source(title="Test", feed_url="http://example.com/feed")
    session.add(source)
    session.commit()
    session.refresh(source)

    entries = [
        {"id": "g1", "title": "Article 1", "link": "http://x/1"},
        {"id": "g2", "title": "Article 2", "link": "http://x/2"},
    ]
    added = _store_result(session, source, _make_result(source.id, entries))
    assert added == 2
    assert source.etag == '"e1"'
    assert source.last_error is None

    # Deuxième passage : mêmes GUID -> aucun nouvel article.
    again = _store_result(session, source, _make_result(source.id, entries))
    assert again == 0

    total = session.exec(select(Article).where(Article.source_id == source.id)).all()
    assert len(total) == 2


def test_store_result_error_sets_last_error(session):
    source = Source(title="Test", feed_url="http://example.com/feed")
    session.add(source)
    session.commit()
    session.refresh(source)

    result = {
        "source_id": source.id,
        "status": "error",
        "entries": [],
        "etag": None,
        "last_modified": None,
        "error": "timeout",
    }
    added = _store_result(session, source, result)
    assert added == 0
    assert source.last_error == "timeout"
    assert source.last_fetched_at is not None
