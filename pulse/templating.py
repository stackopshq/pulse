"""Configuration Jinja2 partagée."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _timeago(value: datetime | None) -> str:
    """Rendu court d'une date relative (ex. « il y a 3 h »)."""
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - value
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "à l'instant"
    minutes = seconds // 60
    if minutes < 60:
        return f"il y a {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"il y a {hours} h"
    days = hours // 24
    if days < 30:
        return f"il y a {days} j"
    return value.strftime("%d/%m/%Y")


templates.env.filters["timeago"] = _timeago


def _recent_alert_count() -> int:
    """Nombre d'alertes déclenchées sur les 7 derniers jours (badge de nav)."""
    from datetime import timedelta

    from sqlalchemy import func
    from sqlmodel import Session, select

    from .db import engine
    from .models import AlertHit

    since = datetime.now(timezone.utc) - timedelta(days=7)
    with Session(engine) as session:
        return session.exec(
            select(func.count()).select_from(AlertHit).where(AlertHit.created_at >= since)
        ).one()


templates.env.globals["recent_alert_count"] = _recent_alert_count
