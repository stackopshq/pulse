"""Dépendances FastAPI : session DB et utilisateur courant."""

from typing import Optional

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from .db import get_session
from .models import User


class RedirectException(Exception):
    """Levée pour rediriger (ex. vers /login) hors d'une réponse HTML."""

    def __init__(self, location: str):
        self.location = location


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = session.get(User, user_id)
    if user and user.is_active:
        return user
    return None


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise RedirectException("/login")
    return user


def redirect_exception_handler(request: Request, exc: RedirectException) -> RedirectResponse:
    return RedirectResponse(exc.location, status_code=303)
