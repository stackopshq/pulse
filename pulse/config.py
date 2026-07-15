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

    debug: bool = False


settings = Settings()
