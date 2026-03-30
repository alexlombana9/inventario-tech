"""Configuracion centralizada con validacion de tipos."""
import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

# Determinar directorio base (compatible con PyInstaller frozen)
if getattr(sys, "frozen", False):  # pragma: no cover
    _base_dir = os.path.dirname(sys.executable)  # pragma: no cover
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

_env_path = os.path.join(_base_dir, ".env")


class Settings(BaseSettings):
    """Configuracion de TechStock con validacion."""

    # Base de datos
    database_url: str = "postgresql://techstock:techstock@localhost:5433/techstock"

    # Entorno
    environment: str = "development"  # development, production, test
    testing: bool = False

    # Seguridad
    cookie_secure: bool = False
    security_headers: bool = True
    idle_timeout_minutes: int = 30
    backup_encryption: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # text o json

    # Chatbot IA
    gemini_api_key: str = ""
    chatbot_ai_enabled: bool = False
    chatbot_ai_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=_env_path if os.path.exists(_env_path) else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
