"""Vue des alertes déclenchées par les règles de veille."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..db import get_session
from ..deps import require_user
from ..models import AlertHit, Article, Rule, Source, User
from ..templating import templates

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_class=HTMLResponse)
def list_alerts(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    rule_id: int | None = None,
):
    query = (
        select(AlertHit, Rule, Article, Source)
        .join(Rule, AlertHit.rule_id == Rule.id)
        .join(Article, AlertHit.article_id == Article.id)
        .join(Source, Article.source_id == Source.id)
        .order_by(AlertHit.created_at.desc())
    )
    if rule_id:
        query = query.where(AlertHit.rule_id == rule_id)

    rows = session.exec(query.limit(200)).all()
    hits = [
        {"hit": hit, "rule": rule, "article": article, "source": source}
        for hit, rule, article, source in rows
    ]
    rules = session.exec(select(Rule).order_by(Rule.name)).all()

    return templates.TemplateResponse(
        request,
        "alerts.html",
        {"user": user, "hits": hits, "rules": rules, "rule_id": rule_id},
    )
