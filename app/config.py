from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import yaml

DEFAULT_DB_URL = "postgresql://coc:coc@db:5432/coc"
DEFAULT_API_BASE_URL = "https://api.clashofclans.com/v1"
DEFAULT_FETCH_CRON = "0 * * * *"


@dataclass(frozen=True)
class AppConfig:
    clan_id: str
    fetch_cron: str
    db_url: str
    api_base_url: str
    request_timeout_seconds: int


def _normalize_tag(tag: str) -> str:
    normalized = tag.strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    return normalized


def load_config(path: str | None = None) -> AppConfig:
    config_path = Path(path or os.getenv("APP_CONFIG", "/app/config/config.yml"))
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    clan_id_raw = str(raw.get("clan_id", "") or "").strip()
    if not clan_id_raw:
        raise ValueError("clan_id must be set in config")
    clan_id = _normalize_tag(clan_id_raw)
    fetch_cron = str(raw.get("fetch_cron", DEFAULT_FETCH_CRON)).strip()
    db_url = str(raw.get("db_url", DEFAULT_DB_URL)).strip() or DEFAULT_DB_URL
    api_base_url = str(raw.get("api_base_url", DEFAULT_API_BASE_URL)).strip() or DEFAULT_API_BASE_URL
    request_timeout_seconds = int(raw.get("request_timeout_seconds", 20))

    if not fetch_cron:
        raise ValueError("fetch_cron must be set in config")

    return AppConfig(
        clan_id=clan_id,
        fetch_cron=fetch_cron,
        db_url=db_url,
        api_base_url=api_base_url,
        request_timeout_seconds=request_timeout_seconds,
    )
