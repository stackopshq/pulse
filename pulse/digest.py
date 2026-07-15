"""Génération et envoi des digests de veille."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from sqlmodel import Session, select

from .config import settings
from .models import AlertHit, Article, Category, Rule, Source

logger = logging.getLogger("pulse.digest")


def period_delta(period: str) -> timedelta:
    return timedelta(days=7) if period == "week" else timedelta(days=1)


def build_digest(session: Session, since: datetime) -> dict:
    """Construit les données du digest depuis ``since`` jusqu'à maintenant."""
    until = datetime.now(timezone.utc)

    categories = {c.id: c for c in session.exec(select(Category)).all()}
    sources = {s.id: s for s in session.exec(select(Source)).all()}

    articles = session.exec(
        select(Article)
        .where(Article.fetched_at >= since)
        .order_by(Article.fetched_at.desc())
    ).all()

    # Regroupement par catégorie (via la source).
    grouped: dict[str, list[Article]] = {}
    for article in articles:
        source = sources.get(article.source_id)
        category = categories.get(source.category_id) if source else None
        name = category.name if category else "Sans catégorie"
        grouped.setdefault(name, []).append(article)

    groups = [
        {"category": name, "articles": grouped[name]}
        for name in sorted(grouped)
    ]

    # Alertes déclenchées sur la période.
    hits = session.exec(
        select(AlertHit, Rule, Article)
        .join(Rule, AlertHit.rule_id == Rule.id)
        .join(Article, AlertHit.article_id == Article.id)
        .where(AlertHit.created_at >= since)
        .order_by(AlertHit.created_at.desc())
    ).all()
    alerts = [{"rule": rule, "article": article} for _hit, rule, article in hits]

    return {
        "since": since,
        "until": until,
        "total_new": len(articles),
        "groups": groups,
        "alerts": alerts,
        "sources": sources,
    }


def render_markdown(data: dict) -> str:
    lines = [
        "# Digest Pulse",
        "",
        f"_Du {data['since']:%d/%m/%Y %H:%M} au {data['until']:%d/%m/%Y %H:%M} — "
        f"{data['total_new']} nouvel(s) article(s)._",
        "",
    ]

    if data["alerts"]:
        lines.append(f"## Alertes ({len(data['alerts'])})")
        lines.append("")
        for item in data["alerts"]:
            article = item["article"]
            rule = item["rule"]
            link = article.url or ""
            lines.append(f"- **[{rule.name}]** [{article.title}]({link})")
        lines.append("")

    for group in data["groups"]:
        lines.append(f"## {group['category']} ({len(group['articles'])})")
        lines.append("")
        for article in group["articles"]:
            source = data["sources"].get(article.source_id)
            src_name = source.title if source else ""
            link = article.url or ""
            lines.append(f"- [{article.title}]({link}) — _{src_name}_")
        lines.append("")

    if not data["groups"] and not data["alerts"]:
        lines.append("_Aucune nouveauté sur la période._")

    return "\n".join(lines)


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.digest_from and settings.digest_to)


def send_digest_email(subject: str, markdown_body: str) -> bool:
    if not smtp_configured():
        logger.warning("Envoi du digest ignoré : SMTP non configuré.")
        return False

    recipients = [addr.strip() for addr in settings.digest_to.split(",") if addr.strip()]
    message = MIMEText(markdown_body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = settings.digest_from
    message["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.digest_from, recipients, message.as_string())
        logger.info("Digest envoyé à %s", recipients)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Échec de l'envoi du digest : %s", exc)
        return False


def generate_and_send(session: Session) -> dict:
    """Construit le digest de la période configurée et l'envoie par email."""
    since = datetime.now(timezone.utc) - period_delta(settings.digest_period)
    data = build_digest(session, since)
    body = render_markdown(data)
    subject = f"Digest Pulse — {data['total_new']} article(s), {len(data['alerts'])} alerte(s)"
    sent = send_digest_email(subject, body)
    return {"sent": sent, "total_new": data["total_new"], "alerts": len(data["alerts"])}
