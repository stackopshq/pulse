"""Gestion des sources (flux) et import/export OPML."""

import feedparser
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session, select

from ..db import get_session
from ..deps import require_user
from ..feeds import collect_one
from ..models import Article, ArticleState, Category, Source, User
from ..opml import export_opml, import_opml
from ..templating import templates

router = APIRouter(tags=["sources"])


@router.get("/sources")
def list_sources(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    sources = session.exec(select(Source).order_by(Source.title)).all()
    categories = session.exec(select(Category).order_by(Category.name)).all()
    cats = {c.id: c for c in categories}
    return templates.TemplateResponse(
        request,
        "sources.html",
        {"user": user, "sources": sources, "categories": categories, "cats": cats},
    )


@router.post("/sources")
def create_source(
    request: Request,
    feed_url: str = Form(...),
    title: str = Form(""),
    category_id: str = Form(""),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    feed_url = feed_url.strip()
    existing = session.exec(select(Source).where(Source.feed_url == feed_url)).first()
    if existing is not None:
        return RedirectResponse("/sources", status_code=303)

    resolved_title = title.strip()
    site_url = None
    if not resolved_title:
        parsed = feedparser.parse(feed_url)
        resolved_title = parsed.feed.get("title", feed_url)
        site_url = parsed.feed.get("link")

    source = Source(
        title=resolved_title,
        feed_url=feed_url,
        site_url=site_url,
        category_id=int(category_id) if category_id else None,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    collect_one(source.id)
    return RedirectResponse("/sources", status_code=303)


@router.post("/sources/{source_id}/toggle")
def toggle_source(
    source_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    source = session.get(Source, source_id)
    if source is not None:
        source.is_active = not source.is_active
        session.add(source)
        session.commit()
    return RedirectResponse("/sources", status_code=303)


@router.post("/sources/{source_id}/collect")
def collect_source(
    source_id: int,
    user: User = Depends(require_user),
):
    collect_one(source_id)
    return RedirectResponse("/sources", status_code=303)


@router.post("/sources/{source_id}/delete")
def delete_source(
    source_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    source = session.get(Source, source_id)
    if source is not None:
        # Supprime les articles et états associés.
        articles = session.exec(select(Article).where(Article.source_id == source_id)).all()
        for article in articles:
            states = session.exec(
                select(ArticleState).where(ArticleState.article_id == article.id)
            ).all()
            for state in states:
                session.delete(state)
            session.delete(article)
        session.delete(source)
        session.commit()
    return RedirectResponse("/sources", status_code=303)


@router.get("/sources/export.opml")
def export(
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    content = export_opml(session)
    return Response(
        content,
        media_type="text/x-opml",
        headers={"Content-Disposition": "attachment; filename=pulse-sources.opml"},
    )


@router.post("/sources/import")
async def import_sources(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    raw = await file.read()
    try:
        import_opml(session, raw.decode("utf-8"))
    except Exception:  # noqa: BLE001  (fichier OPML invalide)
        pass
    return RedirectResponse("/sources", status_code=303)
