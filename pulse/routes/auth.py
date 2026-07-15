"""Authentification : inscription, connexion, déconnexion."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import User
from ..security import hash_password, verify_password
from ..templating import templates

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"user": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"user": None, "error": "Identifiants invalides."},
            status_code=401,
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/articles", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request, "register.html", {"user": None})


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"user": None, "error": "Le mot de passe doit faire au moins 8 caractères."},
            status_code=400,
        )
    if session.exec(select(User).where(User.email == email)).first() is not None:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"user": None, "error": "Cette adresse est déjà utilisée."},
            status_code=400,
        )

    # Le premier compte créé est administrateur.
    is_first = session.exec(select(User)).first() is None
    user = User(
        name=name.strip(),
        email=email,
        password_hash=hash_password(password),
        is_admin=is_first,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse("/articles", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
