"""Spectrum global configuration — loaded from .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class WordPressSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WP_")

    base_url: str = "https://dogsstate.co.il"
    user: str = ""
    app_password: str = ""


class WooCommerceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WC_")

    consumer_key: str = ""
    consumer_secret: str = ""


class AISettings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    content_model: str = "claude-sonnet-4-6"
    qa_model: str = "claude-opus-4-6"


class GoogleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    service_account_json: str = ""
    search_console_site_url: str = "https://dogsstate.co.il"
    merchant_id: str = ""


class GA4Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GA4_")

    property_id: str = ""


class SEOToolsSettings(BaseSettings):
    semrush_api_key: str = ""
    serper_api_key: str = ""


class SocialSettings(BaseSettings):
    facebook_page_access_token: str = ""
    facebook_page_id: str = ""
    instagram_access_token: str = ""
    instagram_business_id: str = ""


class NotificationSettings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""


class SystemSettings(BaseSettings):
    log_level: str = "INFO"
    snapshot_interval_minutes: int = 30
    scheduler_enabled: bool = True
    data_dir: Path = _ROOT / "data"
    snapshots_dir: Path = _ROOT / "snapshots"


class Settings(BaseSettings):
    """Aggregate settings — single source of truth."""

    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    wp: WordPressSettings = Field(default_factory=WordPressSettings)
    wc: WooCommerceSettings = Field(default_factory=WooCommerceSettings)
    ai: AISettings = Field(default_factory=AISettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    ga4: GA4Settings = Field(default_factory=GA4Settings)
    seo: SEOToolsSettings = Field(default_factory=SEOToolsSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    system: SystemSettings = Field(default_factory=SystemSettings)


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
