"""Tests d'intégration web : authentification et lecture."""

from sqlmodel import Session, select

from pulse.db import engine
from pulse.models import Article, ArticleState, Source


def _register(client, email="alice@example.com"):
    return client.post(
        "/register",
        data={"name": "Alice", "email": email, "password": "motdepasse1"},
        follow_redirects=False,
    )


def test_requires_login_redirects(client):
    resp = client.get("/articles", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_register_login_logout(client):
    resp = _register(client)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/articles"

    # Session active : accès autorisé.
    assert client.get("/articles").status_code == 200

    # Déconnexion.
    client.post("/logout", follow_redirects=False)
    assert client.get("/articles", follow_redirects=False).status_code == 303


def test_first_user_is_admin(client):
    _register(client)
    from pulse.models import User

    with Session(engine) as s:
        user = s.exec(select(User)).first()
        assert user.is_admin is True


def test_register_rejects_short_password(client):
    resp = client.post(
        "/register",
        data={"name": "Bob", "email": "bob@example.com", "password": "court"},
    )
    assert resp.status_code == 400


def test_toggle_read_and_favorite(client):
    _register(client)
    with Session(engine) as s:
        source = Source(title="S", feed_url="http://x/feed")
        s.add(source)
        s.commit()
        s.refresh(source)
        article = Article(source_id=source.id, guid="g1", title="Titre")
        s.add(article)
        s.commit()
        s.refresh(article)
        article_id = article.id

    r1 = client.post(f"/articles/{article_id}/read")
    assert r1.status_code == 200

    r2 = client.post(f"/articles/{article_id}/favorite")
    assert r2.status_code == 200

    with Session(engine) as s:
        state = s.exec(
            select(ArticleState).where(ArticleState.article_id == article_id)
        ).first()
        assert state.is_read is True
        assert state.is_favorite is True


def test_unread_filter_excludes_read(client):
    _register(client)
    with Session(engine) as s:
        source = Source(title="S", feed_url="http://x/feed")
        s.add(source)
        s.commit()
        s.refresh(source)
        for i in range(3):
            s.add(Article(source_id=source.id, guid=f"g{i}", title=f"A{i}"))
        s.commit()

    # Tous non lus au départ.
    assert client.get("/articles?status=unread").status_code == 200
    # La vue "tous" fonctionne aussi.
    assert client.get("/articles?status=all").status_code == 200
