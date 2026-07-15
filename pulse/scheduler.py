"""Planification de la collecte périodique des flux."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .feeds import collect_all

logger = logging.getLogger("pulse.scheduler")

scheduler = AsyncIOScheduler()


async def _collect_job() -> None:
    # La collecte est synchrone : on l'exécute dans un thread pour ne pas
    # bloquer la boucle d'événements.
    await asyncio.to_thread(collect_all)


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
    scheduler.start()
    logger.info(
        "Scheduler démarré (collecte toutes les %s min)",
        settings.fetch_interval_minutes,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
