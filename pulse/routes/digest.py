"""Aperçu et export du digest de veille."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlmodel import Session

from ..db import get_session
from ..deps import require_user
from ..digest import build_digest, period_delta, render_markdown
from ..models import User
from ..templating import templates

router = APIRouter(tags=["digest"])


def _since(period: str) -> datetime:
    return datetime.now(timezone.utc) - period_delta(period)


@router.get("/digest", response_class=HTMLResponse)
def digest_page(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    period: str = Query("day", pattern="^(day|week)$"),
):
    data = build_digest(session, _since(period))
    return templates.TemplateResponse(
        request,
        "digest.html",
        {"user": user, "data": data, "period": period},
    )


@router.get("/digest.md", response_class=PlainTextResponse)
def digest_markdown(
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    period: str = Query("day", pattern="^(day|week)$"),
):
    data = build_digest(session, _since(period))
    markdown = render_markdown(data)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=pulse-digest-{period}.md"},
    )
