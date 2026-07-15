"""Lecture des articles : liste filtrée, détail, marquage lu/favori."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlmodel import Session, select

from ..db import get_session
from ..deps import require_user
from ..models import Article, ArticleState, Category, Source, User
from ..templating import templates

router = APIRouter(tags=["articles"])

PAGE_SIZE = 25


def _get_or_create_state(session: Session, user_id: int, article_id: int) -> ArticleState:
    state = session.exec(
        select(ArticleState).where(
            ArticleState.user_id == user_id,
            ArticleState.article_id == article_id,
        )
    ).first()
    if state is None:
        state = ArticleState(user_id=user_id, article_id=article_id)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


@router.get("/articles", response_class=HTMLResponse)
def list_articles(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    status: str = Query("unread", pattern="^(unread|all|favorites)$"),
    category_id: int | None = None,
    source_id: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
):
    query = select(Article, Source).join(Source, Article.source_id == Source.id)

    # Jointure de l'état de lecture propre à l'utilisateur.
    query = query.join(
        ArticleState,
        (ArticleState.article_id == Article.id) & (ArticleState.user_id == user.id),
        isouter=True,
    ).add_columns(ArticleState)

    if category_id:
        query = query.where(Source.category_id == category_id)
    if source_id:
        query = query.where(Article.source_id == source_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(Article.title.ilike(like) | Article.summary.ilike(like))
    if status == "unread":
        query = query.where((ArticleState.is_read == False) | (ArticleState.id == None))  # noqa: E711,E712
    elif status == "favorites":
        query = query.where(ArticleState.is_favorite == True)  # noqa: E712

    query = query.order_by(
        func.coalesce(Article.published_at, Article.fetched_at).desc()
    ).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)

    rows = session.exec(query).all()
    has_next = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]

    articles = [
        {"article": article, "source": source, "state": state}
        for article, source, state in rows
    ]

    categories = session.exec(select(Category).order_by(Category.name)).all()
    sources = session.exec(select(Source).order_by(Source.title)).all()

    context = {
        "user": user,
        "articles": articles,
        "categories": categories,
        "sources": sources,
        "status": status,
        "category_id": category_id,
        "source_id": source_id,
        "q": q or "",
        "page": page,
        "has_next": has_next,
    }

    template = "partials/article_list.html" if request.headers.get("HX-Request") else "articles.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/articles/{article_id}", response_class=HTMLResponse)
def article_detail(
    article_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    article = session.get(Article, article_id)
    if article is None:
        return templates.TemplateResponse(
            request, "not_found.html", {"user": user}, status_code=404
        )
    source = session.get(Source, article.source_id)
    state = _get_or_create_state(session, user.id, article_id)
    if not state.is_read:
        state.is_read = True
        session.add(state)
        session.commit()
    return templates.TemplateResponse(
        request,
        "article_detail.html",
        {"user": user, "article": article, "source": source, "state": state},
    )


@router.post("/articles/{article_id}/read", response_class=HTMLResponse)
def toggle_read(
    article_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    state = _get_or_create_state(session, user.id, article_id)
    state.is_read = not state.is_read
    session.add(state)
    session.commit()
    article = session.get(Article, article_id)
    source = session.get(Source, article.source_id)
    return templates.TemplateResponse(
        request,
        "partials/article_card.html",
        {"user": user, "item": {"article": article, "source": source, "state": state}},
    )


@router.post("/articles/{article_id}/favorite", response_class=HTMLResponse)
def toggle_favorite(
    article_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    state = _get_or_create_state(session, user.id, article_id)
    state.is_favorite = not state.is_favorite
    session.add(state)
    session.commit()
    article = session.get(Article, article_id)
    source = session.get(Source, article.source_id)
    return templates.TemplateResponse(
        request,
        "partials/article_card.html",
        {"user": user, "item": {"article": article, "source": source, "state": state}},
    )
