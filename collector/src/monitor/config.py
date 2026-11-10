"""Validated collector configuration with environment-over-YAML precedence."""

from functools import lru_cache
from pathlib import Path
from typing import ClassVar

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config.yaml"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Runtime configuration; secrets are masked in repr and model dumps."""

    yaml_file: ClassVar[Path] = DEFAULT_CONFIG
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        case_sensitive=False,
    )

    database_url: SecretStr = Field(
        validation_alias=AliasChoices("SUPABASE_DB_URL", "database_url")
    )
    lab_database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("LAB_DB_URL", "lab_database_url"),
    )
    collect_interval_seconds: int = Field(
        default=15,
        ge=10,
        le=3600,
        validation_alias=AliasChoices("COLLECT_INTERVAL_SECONDS", "collect_interval_seconds"),
    )
    probe_timeout_seconds: int = Field(default=8, ge=1, le=8)
    max_probe_workers: int = Field(default=8, ge=1, le=32)
    icmp_hosts: dict[str, str] = Field(
        default_factory=lambda: {
            "web": "nginx",
            "db": "postgres",
            "dns": "coredns",
            "smtp": "postfix",
        }
    )
    web_probe_url: str = "http://nginx/"
    dns_nameserver: str = "172.28.0.53"
    dns_query_name: str = "web.lab.local"
    dns_missing_query_name: str = "missing.lab.local"
    dns_external_query_name: str = "example.com"
    smtp_host: str = "postfix"
    smtp_port: int = Field(default=25, ge=1, le=65535)
    mailhog_api_url: str = "http://mailhog:8025"
    smtp_probe_from: str = "monitor@devops.local"
    smtp_probe_to: str = "probe@devops.local"
    smtp_probe_timeout_seconds: int = Field(default=6, ge=2, le=8)
    nginx_access_log: Path = Path("/var/log/nginx/access.log")
    stub_status_url: str = "http://nginx/nginx_status"
    coredns_metrics_url: str = "http://coredns:9153/metrics"
    postfix_version: str = ""  # fallback when the SMTP banner hides the version

    # Alert e-mail channel (dedicated SMTP; MailHog in dev, Gmail/app password in demo)
    alert_smtp_host: str = "mailhog"
    alert_smtp_port: int = Field(default=1025, ge=1, le=65535)
    alert_smtp_user: str = ""
    alert_smtp_password: SecretStr = SecretStr("")
    alert_email_to: str = ""
    alert_email_from: str = "alertas@devops.local"
    dashboard_url: str = "http://localhost:3000"
    nvd_api_key: SecretStr = SecretStr("")

    # label -> path inside the collector container (labels match accept_config_baseline)
    config_watch_files: dict[str, str] = Field(
        default_factory=lambda: {
            "nginx.conf": "/monitor-config/nginx.conf",
            "Corefile": "/monitor-config/Corefile",
            "postgresql.conf": "/monitor-config/postgresql.conf",
            "main.cf": "/monitor-config/main.cf",
        }
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Keep explicit arguments and env values ahead of non-secret YAML defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=cls.yaml_file),
            file_secret_settings,
        )


def load_settings(
    config_file: Path = DEFAULT_CONFIG,
    env_file: str | Path | None = DEFAULT_ENV_FILE,
) -> Settings:
    """Load a chosen YAML file while retaining standard env override behavior."""

    class RuntimeSettings(Settings):
        yaml_file = config_file

    return RuntimeSettings(_env_file=env_file)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return load_settings()
