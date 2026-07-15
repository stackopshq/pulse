"""Application FastAPI Pulse."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import init_db
from .deps import RedirectException, redirect_exception_handler
from .routes import alerts, articles, auth, categories, digest, rules, sources
from .scheduler import shutdown_scheduler, start_scheduler
from .seed import seed_default_categories

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_default_categories()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Pulse", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=False,
)
app.add_exception_handler(RedirectException, redirect_exception_handler)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(sources.router)
app.include_router(categories.router)
app.include_router(rules.router)
app.include_router(alerts.router)
app.include_router(digest.router)


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/articles")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}
