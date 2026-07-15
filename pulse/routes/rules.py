"""Gestion des règles de veille (alertes par mots-clés)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..alerts import backfill_rule
from ..db import get_session
from ..deps import require_user
from ..models import AlertHit, Rule, User
from ..templating import templates

router = APIRouter(tags=["rules"])


@router.get("/rules")
def list_rules(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    rules = session.exec(select(Rule).order_by(Rule.name)).all()
    counts = {}
    for rule in rules:
        counts[rule.id] = len(
            session.exec(select(AlertHit).where(AlertHit.rule_id == rule.id)).all()
        )
    return templates.TemplateResponse(
        request,
        "rules.html",
        {"user": user, "rules": rules, "counts": counts},
    )


@router.post("/rules")
def create_rule(
    name: str = Form(...),
    keywords: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    name = name.strip()
    keywords = keywords.strip()
    if name and keywords:
        rule = Rule(name=name, keywords=keywords)
        session.add(rule)
        session.commit()
        session.refresh(rule)
        # Applique immédiatement la règle aux articles déjà collectés.
        backfill_rule(session, rule)
    return RedirectResponse("/rules", status_code=303)


@router.post("/rules/{rule_id}/toggle")
def toggle_rule(
    rule_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    rule = session.get(Rule, rule_id)
    if rule is not None:
        rule.is_active = not rule.is_active
        session.add(rule)
        session.commit()
    return RedirectResponse("/rules", status_code=303)


@router.post("/rules/{rule_id}/delete")
def delete_rule(
    rule_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    rule = session.get(Rule, rule_id)
    if rule is not None:
        hits = session.exec(select(AlertHit).where(AlertHit.rule_id == rule_id)).all()
        for hit in hits:
            session.delete(hit)
        session.delete(rule)
        session.commit()
    return RedirectResponse("/rules", status_code=303)
