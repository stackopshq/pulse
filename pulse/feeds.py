"""Collecte et parsing des flux RSS/Atom.

La collecte est volontairement synchrone (httpx.Client + feedparser) et
parallélisée par un pool de threads, ce qui évite de mélanger session ORM
synchrone et code asynchrone. Le scheduler l'appelle via ``asyncio.to_thread``.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from sqlmodel import Session, select

from .alerts import evaluate_rules
from .config import settings
from .db import engine
from .models import Article, Source

logger = logging.getLogger("pulse.feeds")

USER_AGENT = "Pulse/0.1 (+https://github.com/stackopshq/pulse)"


def _parse_date(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _entry_guid(entry: Any) -> str:
    return entry.get("id") or entry.get("link") or entry.get("title") or ""


def _extract_content(entry: Any) -> str | None:
    content = entry.get("content")
    if content:
        try:
            return content[0].get("value")
        except (IndexError, AttributeError):
            pass
    return entry.get("summary")


def fetch_source(source: Source) -> dict:
    """Récupère et parse un flux. N'écrit rien en base (thread-safe)."""
    headers = {"User-Agent": USER_AGENT}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified

    result: dict = {
        "source_id": source.id,
        "status": "error",
        "entries": [],
        "etag": source.etag,
        "last_modified": source.last_modified,
        "error": None,
    }
    try:
        with httpx.Client(timeout=settings.request_timeout, follow_redirects=True) as client:
            resp = client.get(source.feed_url, headers=headers)
        if resp.status_code == 304:
            result["status"] = "not_modified"
            return result
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        result.update(
            status="ok",
            entries=parsed.entries,
            etag=resp.headers.get("ETag"),
            last_modified=resp.headers.get("Last-Modified"),
        )
    except Exception as exc:  # noqa: BLE001  (on isole chaque flux)
        result["error"] = str(exc)
        logger.warning("Échec de collecte pour %s : %s", source.feed_url, exc)
    return result


def _store_result(session: Session, source: Source, result: dict) -> list[int]:
    """Enregistre les nouveaux articles. Retourne leurs identifiants."""
    source.last_fetched_at = datetime.now(timezone.utc)

    if result["status"] == "error":
        source.last_error = (result["error"] or "erreur inconnue")[:500]
        session.add(source)
        session.commit()
        return []

    source.last_error = None
    if result["status"] == "ok":
        source.etag = result.get("etag")
        source.last_modified = result.get("last_modified")

    new_articles: list[Article] = []
    for entry in result["entries"]:
        guid = _entry_guid(entry)
        if not guid:
            continue
        exists = session.exec(
            select(Article).where(Article.source_id == source.id, Article.guid == guid)
        ).first()
        if exists:
            continue
        article = Article(
            source_id=source.id,
            guid=guid,
            title=(entry.get("title") or "(sans titre)")[:500],
            url=entry.get("link"),
            author=entry.get("author"),
            summary=entry.get("summary"),
            content=_extract_content(entry),
            published_at=_parse_date(entry),
        )
        session.add(article)
        new_articles.append(article)

    session.add(source)
    session.commit()
    return [a.id for a in new_articles]


def collect_all() -> dict:
    """Collecte toutes les sources actives. Retourne un récapitulatif."""
    with Session(engine) as session:
        sources = list(session.exec(select(Source).where(Source.is_active == True)).all())  # noqa: E712

    if not sources:
        return {"sources": 0, "new_articles": 0, "detail": {}}

    workers = min(settings.max_concurrent_fetches, len(sources))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fetched = list(pool.map(fetch_source, sources))

    total_new = 0
    all_new_ids: list[int] = []
    detail: dict[str, int] = {}
    with Session(engine) as session:
        by_id = {s.id: s for s in session.exec(select(Source)).all()}
        for result in fetched:
            source = by_id.get(result["source_id"])
            if source is None:
                continue
            new_ids = _store_result(session, source, result)
            total_new += len(new_ids)
            all_new_ids.extend(new_ids)
            detail[source.feed_url] = len(new_ids)

        alerts = evaluate_rules(session, all_new_ids)

    logger.info("Collecte : %s nouveaux articles sur %s sources", total_new, len(sources))
    return {
        "sources": len(sources),
        "new_articles": total_new,
        "alerts": alerts,
        "detail": detail,
    }


def collect_one(source_id: int) -> int:
    """Collecte immédiate d'une source unique. Retourne le nb de nouveaux articles."""
    with Session(engine) as session:
        source = session.get(Source, source_id)
        if source is None:
            return 0
        result = fetch_source(source)
        new_ids = _store_result(session, source, result)
        evaluate_rules(session, new_ids)
        return len(new_ids)
