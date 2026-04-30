from __future__ import annotations

from datetime import datetime
from typing import Any

WAR_TYPE_MAP = {
    "regular": "gdc",
    "cwl": "ldc",
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def compute_clan_health(
    war_capacity: int,
    war_missed: int,
    donations_avg: float,
    capital_capacity: int,
    capital_used: int,
    freshness_hours: float,
) -> dict[str, Any]:
    war_score = 70.0
    if war_capacity > 0:
        war_score = max(0.0, min(100.0, (1.0 - (war_missed / war_capacity)) * 100.0))

    donation_score = max(0.0, min(100.0, (donations_avg / 350.0) * 100.0))

    capital_score = 65.0
    if capital_capacity > 0:
        capital_score = max(0.0, min(100.0, (capital_used / capital_capacity) * 100.0))

    freshness_score = 20.0
    if freshness_hours <= 2:
        freshness_score = 100.0
    elif freshness_hours <= 6:
        freshness_score = 85.0
    elif freshness_hours <= 24:
        freshness_score = 60.0
    elif freshness_hours <= 48:
        freshness_score = 45.0

    score = (war_score * 0.42) + (capital_score * 0.25) + (donation_score * 0.18) + (freshness_score * 0.15)
    score = round(score, 1)

    return {
        "score": score,
        "grade": grade(score),
        "components": {
            "discipline_guerre": round(war_score, 1),
            "execution_capitale": round(capital_score, 1),
            "solidarite_dons": round(donation_score, 1),
            "fraicheur_data": round(freshness_score, 1),
        },
    }


def compute_player_activity_score(
    *,
    attack_stars: int,
    donations: int,
    raid_loot: int,
    jdc: int,
    missed_attacks: int,
) -> float:
    return round((attack_stars * 500.0) + donations + (raid_loot / 5.0) + jdc - (missed_attacks * 1000.0), 1)


def dt_label(value: datetime | None, bucket: str) -> str:
    if value is None:
        return "-"
    local = value.astimezone()
    if bucket == "hour":
        return local.strftime("%d/%m %Hh")
    if bucket == "day":
        return local.strftime("%d/%m")
    if bucket == "week":
        return "S" + local.strftime("%V")
    return local.strftime("%m/%Y")


def war_bucket_key(raw_type: str | None) -> str:
    return WAR_TYPE_MAP.get(str(raw_type or "").lower(), "gdc")


def war_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    wars_ended = safe_int(row.get("wars_ended"))
    wins = safe_int(row.get("wins"))
    return {
        "wars_ended": wars_ended,
        "wins": wins,
        "losses": safe_int(row.get("losses")),
        "draws": safe_int(row.get("draws")),
        "attack_capacity": safe_int(row.get("attack_capacity")),
        "attacks_used": safe_int(row.get("attacks_used")),
        "missed_attacks": safe_int(row.get("missed_attacks")),
        "win_rate": round((wins / wars_ended) * 100.0, 1) if wars_ended > 0 else 0.0,
    }


def compute_participation_rate(attacks_used: int, attack_capacity: int) -> float:
    if attack_capacity <= 0:
        return 0.0
    return round((attacks_used / attack_capacity) * 100.0, 1)


def compute_delta(current: int | float, previous: int | float | None) -> float:
    if previous is None:
        return 0.0
    return round(float(current) - float(previous), 1)


def compute_monthly_progress(
    current_total: int | float | None,
    *,
    previous_total: int | float | None = None,
    month_floor_total: int | float | None = None,
) -> int:
    current = safe_int(current_total)
    if previous_total is not None:
        previous = safe_int(previous_total)
        if current >= previous:
            return current - previous
    if month_floor_total is not None:
        return max(current - safe_int(month_floor_total), 0)
    return 0


def serialize_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_json(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_json(item) for key, item in value.items()}
    return value
