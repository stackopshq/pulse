"""Configuration applicative chargée depuis l'environnement (préfixe PULSE_)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PULSE_",
        extra="ignore",
    )

    # Base de données. PostgreSQL par défaut ; SQLite accepté pour les tests.
    database_url: str = "postgresql+psycopg://pulse:pulse@localhost:5432/pulse"

    # Signature des cookies de session.
    secret_key: str = "change-me-in-production"

    # Collecte des flux.
    fetch_interval_minutes: int = 30
    request_timeout: float = 15.0
    max_concurrent_fetches: int = 8

    # Digest périodique par email (optionnel).
    digest_enabled: bool = False
    digest_period: str = "day"  # "day" ou "week"
    digest_hour: int = 8  # heure d'envoi (0-23)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    digest_from: str = ""
    digest_to: str = ""  # destinataires séparés par des virgules

    debug: bool = False


settings = Settings()
