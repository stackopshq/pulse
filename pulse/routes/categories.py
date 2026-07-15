"""Gestion des catégories partagées."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..db import get_session
from ..deps import require_user
from ..models import Category, Source, User
from ..templating import templates

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    categories = session.exec(select(Category).order_by(Category.name)).all()
    counts = {}
    for category in categories:
        counts[category.id] = len(
            session.exec(select(Source).where(Source.category_id == category.id)).all()
        )
    return templates.TemplateResponse(
        request,
        "categories.html",
        {"user": user, "categories": categories, "counts": counts},
    )


@router.post("/categories")
def create_category(
    name: str = Form(...),
    color: str = Form("#6366f1"),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    name = name.strip()
    if name and session.exec(select(Category).where(Category.name == name)).first() is None:
        session.add(Category(name=name, color=color))
        session.commit()
    return RedirectResponse("/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(
    category_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    category = session.get(Category, category_id)
    if category is not None:
        # Détache les sources de la catégorie supprimée.
        sources = session.exec(
            select(Source).where(Source.category_id == category_id)
        ).all()
        for source in sources:
            source.category_id = None
            session.add(source)
        session.delete(category)
        session.commit()
    return RedirectResponse("/categories", status_code=303)
