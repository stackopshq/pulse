"""Planification de la collecte périodique des flux."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .feeds import collect_all

logger = logging.getLogger("pulse.scheduler")

scheduler = AsyncIOScheduler()


async def _collect_job() -> None:
    # La collecte est synchrone : on l'exécute dans un thread pour ne pas
    # bloquer la boucle d'événements.
    await asyncio.to_thread(collect_all)


def _run_digest() -> None:
    from sqlmodel import Session

    from .db import engine
    from .digest import generate_and_send

    with Session(engine) as session:
        generate_and_send(session)


async def _digest_job() -> None:
    await asyncio.to_thread(_run_digest)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _collect_job,
        trigger="interval",
        minutes=settings.fetch_interval_minutes,
        id="collect",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    if settings.digest_enabled:
        if settings.digest_period == "week":
            trigger = CronTrigger(day_of_week="mon", hour=settings.digest_hour, minute=0)
        else:
            trigger = CronTrigger(hour=settings.digest_hour, minute=0)
        scheduler.add_job(
            _digest_job,
            trigger=trigger,
            id="digest",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info(
            "Digest planifié (%s à %sh)", settings.digest_period, settings.digest_hour
        )

    scheduler.start()
    logger.info(
        "Scheduler démarré (collecte toutes les %s min)",
        settings.fetch_interval_minutes,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
