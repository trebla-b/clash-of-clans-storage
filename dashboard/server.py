from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any

from flask import Flask, abort, render_template, request
import psycopg
from psycopg.rows import dict_row
from waitress import serve

from app.config import load_config

CONFIG = load_config()
DB_URL = os.getenv("DASHBOARD_DB_URL", CONFIG.db_url)
DEFAULT_CLAN_TAG = os.getenv("DASHBOARD_CLAN_TAG", CONFIG.clan_id)

SCALES: dict[str, dict[str, Any]] = {
    "7d": {"label": "7 jours", "days": 7, "snapshot_bucket": "hour", "war_bucket": "day"},
    "30d": {"label": "30 jours", "days": 30, "snapshot_bucket": "day", "war_bucket": "week"},
    "90d": {"label": "90 jours", "days": 90, "snapshot_bucket": "day", "war_bucket": "week"},
    "365d": {"label": "365 jours", "days": 365, "snapshot_bucket": "week", "war_bucket": "month"},
    "all": {"label": "Depuis le début", "days": None, "snapshot_bucket": "week", "war_bucket": "month"},
}
DEFAULT_SCALE = "30d"

app = Flask(__name__, template_folder="templates", static_folder="static")


def _connect() -> psycopg.Connection:
    return psycopg.connect(DB_URL, row_factory=dict_row)


def _one(cur: psycopg.Cursor, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    cur.execute(query, params)
    row = cur.fetchone()
    return dict(row) if row else {}


def _all(cur: psycopg.Cursor, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


def _normalize_tag(tag: str) -> str:
    normalized = tag.strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    return normalized


def _resolve_scale(raw: str | None) -> str:
    key = (raw or DEFAULT_SCALE).strip().lower()
    return key if key in SCALES else DEFAULT_SCALE


def _scale_options() -> list[dict[str, str]]:
    return [{"key": key, "label": value["label"]} for key, value in SCALES.items()]


def _from_time(scale_key: str) -> datetime | None:
    days = SCALES[scale_key]["days"]
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=int(days))


def _dt_label(value: datetime | None, bucket: str) -> str:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _compute_clan_health(
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
        "grade": _grade(score),
        "components": {
            "discipline_guerre": round(war_score, 1),
            "execution_capitale": round(capital_score, 1),
            "solidarite_dons": round(donation_score, 1),
            "fraicheur_data": round(freshness_score, 1),
        },
    }


def _compute_player_health(
    attacks_used: int,
    attack_capacity: int,
    missed_attacks: int,
    donations: int,
    capital_ratio: float,
    freshness_hours: float,
) -> float:
    participation_score = 65.0
    if attack_capacity > 0:
        participation_score = max(0.0, min(100.0, (1.0 - (missed_attacks / attack_capacity)) * 100.0))

    donations_score = max(0.0, min(100.0, (donations / 280.0) * 100.0))
    capital_score = max(0.0, min(100.0, capital_ratio * 100.0)) if capital_ratio > 0 else 60.0

    freshness_score = 25.0
    if freshness_hours <= 4:
        freshness_score = 100.0
    elif freshness_hours <= 12:
        freshness_score = 75.0
    elif freshness_hours <= 48:
        freshness_score = 55.0

    return round(
        (participation_score * 0.45)
        + (donations_score * 0.2)
        + (capital_score * 0.2)
        + (freshness_score * 0.15),
        1,
    )


@app.template_filter("intfmt")
def intfmt(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


@app.template_filter("pctfmt")
def pctfmt(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


@app.template_filter("dtfmt")
def dtfmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, datetime):
        return value.astimezone().strftime("%d/%m/%Y %H:%M")
    return str(value)


def _load_overview(scale_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from_time = _from_time(scale_key)
    scale_conf = SCALES[scale_key]

    with _connect() as conn:
        with conn.cursor() as cur:
            clan = _one(
                cur,
                """
                SELECT
                    tag,
                    name,
                    members,
                    clan_level,
                    clan_points,
                    war_wins,
                    war_losses,
                    war_ties,
                    updated_at
                FROM clans
                WHERE tag = %s
                """,
                (DEFAULT_CLAN_TAG,),
            )

            if not clan:
                clan = _one(
                    cur,
                    """
                    SELECT
                        tag,
                        name,
                        members,
                        clan_level,
                        clan_points,
                        war_wins,
                        war_losses,
                        war_ties,
                        updated_at
                    FROM clans
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                )

            if not clan:
                empty = {
                    "clan": {"tag": DEFAULT_CLAN_TAG, "name": "Aucune donnée", "members": 0},
                    "clan_tag": DEFAULT_CLAN_TAG,
                    "kpis": {},
                    "war_summary": {},
                    "health": {"score": 0, "grade": "D", "components": {}},
                    "players": [],
                    "capital_top": [],
                    "at_risk": [],
                    "freshness": {},
                }
                empty_chart = {
                    "clan_points": [],
                    "war_outcomes": [],
                    "health_components": [],
                    "scale": scale_key,
                }
                return empty, empty_chart

            clan_tag = str(clan["tag"])

            members_agg = _one(
                cur,
                """
                SELECT
                    COUNT(*)::INT AS active_members,
                    COALESCE(AVG(trophies), 0)::NUMERIC(12,2) AS avg_trophies,
                    COALESCE(SUM(donations), 0)::BIGINT AS donations_sent,
                    COALESCE(SUM(donations_received), 0)::BIGINT AS donations_received,
                    COALESCE(AVG(clan_games_points_total), 0)::NUMERIC(12,2) AS avg_clan_games,
                    COALESCE(SUM(clan_capital_contributions), 0)::BIGINT AS capital_contributions,
                    COALESCE(AVG((COALESCE(donations,0) + COALESCE(donations_received,0)) / 2.0), 0)::NUMERIC(12,2)
                        AS avg_social_score
                FROM v_current_clan_members
                WHERE clan_tag = %s
                """,
                (clan_tag,),
            )

            params_snap: list[Any] = [clan_tag]
            time_clause_snap = ""
            if from_time is not None:
                time_clause_snap = "AND fetched_at >= %s"
                params_snap.append(from_time)

            clan_points_series = _all(
                cur,
                f"""
                SELECT
                    date_trunc('{scale_conf['snapshot_bucket']}', fetched_at) AS bucket,
                    MAX(clan_points)::INT AS clan_points,
                    MAX(members)::INT AS members
                FROM clan_snapshots
                WHERE clan_tag = %s
                  {time_clause_snap}
                GROUP BY 1
                ORDER BY 1
                """,
                tuple(params_snap),
            )

            points_delta = 0
            members_delta = 0
            if len(clan_points_series) >= 2:
                points_delta = _safe_int(clan_points_series[-1].get("clan_points")) - _safe_int(
                    clan_points_series[0].get("clan_points")
                )
                members_delta = _safe_int(clan_points_series[-1].get("members")) - _safe_int(
                    clan_points_series[0].get("members")
                )

            params_war: list[Any] = [clan_tag]
            time_clause_war = ""
            if from_time is not None:
                time_clause_war = "AND start_time >= %s"
                params_war.append(from_time)

            war_summary = _one(
                cur,
                f"""
                SELECT
                    COUNT(*) FILTER (WHERE state = 'warEnded')::INT AS wars_ended,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'win')::INT AS wins,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'loss')::INT AS losses,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'draw')::INT AS draws
                FROM clan_wars
                WHERE clan_tag = %s
                  {time_clause_war}
                """,
                tuple(params_war),
            )

            war_summary["win_rate"] = 0.0
            wars_ended = _safe_int(war_summary.get("wars_ended"))
            if wars_ended > 0:
                war_summary["win_rate"] = round(
                    (_safe_int(war_summary.get("wins")) / wars_ended) * 100.0,
                    1,
                )

            war_outcomes_series = _all(
                cur,
                f"""
                SELECT
                    date_trunc('{scale_conf['war_bucket']}', start_time) AS bucket,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'win')::INT AS wins,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'loss')::INT AS losses,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'draw')::INT AS draws
                FROM clan_wars
                WHERE clan_tag = %s
                  {time_clause_war}
                GROUP BY 1
                ORDER BY 1
                """,
                tuple(params_war),
            )

            war_participation = _one(
                cur,
                f"""
                SELECT
                    COALESCE(SUM(wmp.attack_capacity), 0)::INT AS attack_capacity,
                    COALESCE(SUM(wmp.attacks_used), 0)::INT AS attacks_used,
                    COALESCE(SUM(wmp.missed_attacks), 0)::INT AS missed_attacks
                FROM war_member_performances wmp
                JOIN clan_wars w ON w.war_id = wmp.war_id
                WHERE w.clan_tag = %s
                  AND wmp.is_our_clan = TRUE
                  {time_clause_war}
                """,
                tuple(params_war),
            )

            latest_capital = _one(
                cur,
                """
                SELECT
                    season_start_time,
                    season_end_time,
                    capital_total_loot,
                    total_attacks,
                    enemy_districts_destroyed
                FROM capital_raid_seasons
                WHERE clan_tag = %s
                ORDER BY season_start_time DESC
                LIMIT 1
                """,
                (clan_tag,),
            )

            capital_top: list[dict[str, Any]] = []
            capital_capacity = 0
            capital_used = 0
            if latest_capital:
                capital_top = _all(
                    cur,
                    """
                    SELECT
                        player_tag,
                        player_name,
                        attacks,
                        attack_limit,
                        bonus_attack_limit,
                        capital_resources_looted
                    FROM capital_raid_member_stats
                    WHERE clan_tag = %s
                      AND season_start_time = %s
                    ORDER BY capital_resources_looted DESC NULLS LAST, attacks DESC
                    LIMIT 10
                    """,
                    (clan_tag, latest_capital["season_start_time"]),
                )

                cap_agg = _one(
                    cur,
                    """
                    SELECT
                        COALESCE(SUM(attacks), 0)::INT AS attacks_used,
                        COALESCE(SUM(attack_limit + bonus_attack_limit), 0)::INT AS attacks_capacity
                    FROM capital_raid_member_stats
                    WHERE clan_tag = %s
                      AND season_start_time = %s
                    """,
                    (clan_tag, latest_capital["season_start_time"]),
                )
                capital_used = _safe_int(cap_agg.get("attacks_used"))
                capital_capacity = _safe_int(cap_agg.get("attacks_capacity"))

            player_rows = _all(
                cur,
                f"""
                WITH war AS (
                    SELECT
                        wmp.player_tag,
                        MAX(wmp.player_name) AS player_name,
                        SUM(wmp.attack_capacity)::INT AS attack_capacity,
                        SUM(wmp.attacks_used)::INT AS attacks_used,
                        SUM(wmp.missed_attacks)::INT AS missed_attacks,
                        SUM(wmp.total_attack_stars)::INT AS attack_stars,
                        ROUND(AVG(COALESCE(wmp.total_attack_destruction, 0)), 2) AS avg_attack_destruction
                    FROM war_member_performances wmp
                    JOIN clan_wars w ON w.war_id = wmp.war_id
                    WHERE w.clan_tag = %s
                      AND wmp.is_our_clan = TRUE
                      {time_clause_war}
                    GROUP BY wmp.player_tag
                ),
                freshness AS (
                    SELECT player_tag, MAX(fetched_at) AS last_snapshot_at
                    FROM player_snapshots
                    WHERE clan_tag = %s
                    GROUP BY player_tag
                )
                SELECT
                    m.player_tag,
                    m.name,
                    m.town_hall_level,
                    m.trophies,
                    m.league_tier_name,
                    m.donations,
                    m.donations_received,
                    m.clan_games_points_total,
                    m.clan_capital_contributions,
                    COALESCE(w.attack_capacity, 0)::INT AS attack_capacity,
                    COALESCE(w.attacks_used, 0)::INT AS attacks_used,
                    COALESCE(w.missed_attacks, 0)::INT AS missed_attacks,
                    COALESCE(w.attack_stars, 0)::INT AS attack_stars,
                    COALESCE(w.avg_attack_destruction, 0)::NUMERIC(8,2) AS avg_attack_destruction,
                    f.last_snapshot_at
                FROM v_current_clan_members m
                LEFT JOIN war w ON w.player_tag = m.player_tag
                LEFT JOIN freshness f ON f.player_tag = m.player_tag
                WHERE m.clan_tag = %s
                ORDER BY COALESCE(w.missed_attacks, 0) DESC, m.trophies DESC
                """,
                tuple([clan_tag] + ([from_time] if from_time is not None else []) + [clan_tag, clan_tag]),
            )

            now_utc = datetime.now(timezone.utc)
            for row in player_rows:
                last_snapshot = row.get("last_snapshot_at")
                freshness_hours = 9999.0
                if isinstance(last_snapshot, datetime):
                    freshness_hours = max((now_utc - last_snapshot).total_seconds() / 3600.0, 0.0)

                attack_capacity = _safe_int(row.get("attack_capacity"))
                missed_attacks = _safe_int(row.get("missed_attacks"))
                row["participation_rate"] = round(
                    ((attack_capacity - missed_attacks) / attack_capacity) * 100.0,
                    1,
                ) if attack_capacity > 0 else 0.0

                capital_ratio = 0.0
                if latest_capital:
                    player_cap_entry = next(
                        (p for p in capital_top if p.get("player_tag") == row.get("player_tag")),
                        None,
                    )
                    if player_cap_entry:
                        cap = _safe_int(player_cap_entry.get("attack_limit")) + _safe_int(
                            player_cap_entry.get("bonus_attack_limit")
                        )
                        if cap > 0:
                            capital_ratio = _safe_int(player_cap_entry.get("attacks")) / cap

                row["health_score"] = _compute_player_health(
                    attacks_used=_safe_int(row.get("attacks_used")),
                    attack_capacity=attack_capacity,
                    missed_attacks=missed_attacks,
                    donations=_safe_int(row.get("donations")),
                    capital_ratio=capital_ratio,
                    freshness_hours=freshness_hours,
                )

                row["player_slug"] = str(row.get("player_tag") or "").lstrip("#")

            at_risk = sorted(
                player_rows,
                key=lambda row: (
                    -_safe_int(row.get("missed_attacks")),
                    _safe_float(row.get("health_score")),
                ),
            )[:8]

            top_contributors = sorted(
                player_rows,
                key=lambda row: (
                    -_safe_int(row.get("donations")),
                    -_safe_int(row.get("clan_capital_contributions")),
                    -_safe_int(row.get("attack_stars")),
                ),
            )[:8]

            freshness = _one(
                cur,
                """
                SELECT
                    (SELECT MAX(fetched_at) FROM clan_snapshots WHERE clan_tag = %s) AS latest_snapshot,
                    (SELECT MAX(updated_at) FROM clan_wars WHERE clan_tag = %s) AS latest_war,
                    (SELECT MAX(updated_at) FROM capital_raid_seasons WHERE clan_tag = %s) AS latest_capital,
                    (SELECT MAX(updated_at) FROM players WHERE clan_tag = %s) AS latest_players
                """,
                (clan_tag, clan_tag, clan_tag, clan_tag),
            )

    latest_snapshot = freshness.get("latest_snapshot")
    freshness_hours = 9999.0
    if isinstance(latest_snapshot, datetime):
        freshness_hours = max((datetime.now(timezone.utc) - latest_snapshot).total_seconds() / 3600.0, 0.0)

    health = _compute_clan_health(
        war_capacity=_safe_int(war_participation.get("attack_capacity")),
        war_missed=_safe_int(war_participation.get("missed_attacks")),
        donations_avg=_safe_float(members_agg.get("avg_social_score")),
        capital_capacity=capital_capacity,
        capital_used=capital_used,
        freshness_hours=freshness_hours,
    )

    chart_points = [
        {
            "label": _dt_label(point.get("bucket"), scale_conf["snapshot_bucket"]),
            "clan_points": _safe_int(point.get("clan_points")),
            "members": _safe_int(point.get("members")),
        }
        for point in clan_points_series
    ]

    chart_wars = [
        {
            "label": _dt_label(point.get("bucket"), scale_conf["war_bucket"]),
            "wins": _safe_int(point.get("wins")),
            "losses": _safe_int(point.get("losses")),
            "draws": _safe_int(point.get("draws")),
        }
        for point in war_outcomes_series
    ]

    chart_payload = {
        "scale": scale_key,
        "clan_points": chart_points,
        "war_outcomes": chart_wars,
        "health_components": [
            {"label": key.replace("_", " ").title(), "value": _safe_float(value)}
            for key, value in health["components"].items()
        ],
    }

    data_payload: dict[str, Any] = {
        "clan": clan,
        "clan_tag": clan_tag,
        "scale_key": scale_key,
        "scale_label": scale_conf["label"],
        "scales": _scale_options(),
        "kpis": {
            "active_members": _safe_int(members_agg.get("active_members")),
            "avg_trophies": round(_safe_float(members_agg.get("avg_trophies")), 1),
            "donations_sent": _safe_int(members_agg.get("donations_sent")),
            "donations_received": _safe_int(members_agg.get("donations_received")),
            "avg_clan_games": round(_safe_float(members_agg.get("avg_clan_games")), 1),
            "capital_contributions": _safe_int(members_agg.get("capital_contributions")),
            "clan_points_delta": points_delta,
            "members_delta": members_delta,
        },
        "war_summary": {
            "wars_ended": _safe_int(war_summary.get("wars_ended")),
            "wins": _safe_int(war_summary.get("wins")),
            "losses": _safe_int(war_summary.get("losses")),
            "draws": _safe_int(war_summary.get("draws")),
            "win_rate": _safe_float(war_summary.get("win_rate")),
            "attack_capacity": _safe_int(war_participation.get("attack_capacity")),
            "attacks_used": _safe_int(war_participation.get("attacks_used")),
            "missed_attacks": _safe_int(war_participation.get("missed_attacks")),
        },
        "health": health,
        "players": player_rows,
        "at_risk": at_risk,
        "top_contributors": top_contributors,
        "latest_capital": latest_capital,
        "capital_top": capital_top,
        "freshness": freshness,
    }

    return data_payload, chart_payload


def _load_player_detail(player_tag: str, scale_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    tag = _normalize_tag(player_tag)
    scale_conf = SCALES[scale_key]
    from_time = _from_time(scale_key)

    with _connect() as conn:
        with conn.cursor() as cur:
            player = _one(
                cur,
                """
                SELECT
                    tag,
                    name,
                    clan_tag,
                    role,
                    town_hall_level,
                    trophies,
                    best_trophies,
                    league_tier_name,
                    donations,
                    donations_received,
                    clan_games_points_total,
                    clan_capital_contributions,
                    updated_at
                FROM players
                WHERE tag = %s
                """,
                (tag,),
            )

            if not player:
                abort(404, f"Joueur introuvable: {tag}")

            clan_tag = str(player.get("clan_tag") or DEFAULT_CLAN_TAG)

            params_snap: list[Any] = [tag]
            time_clause_snap = ""
            if from_time is not None:
                time_clause_snap = "AND fetched_at >= %s"
                params_snap.append(from_time)

            snapshots = _all(
                cur,
                f"""
                SELECT
                    date_trunc('{scale_conf['snapshot_bucket']}', fetched_at) AS bucket,
                    MAX(trophies)::INT AS trophies,
                    MAX(donations)::INT AS donations,
                    MAX(donations_received)::INT AS donations_received,
                    MAX(clan_games_points_total)::INT AS clan_games_points_total,
                    MAX(clan_capital_contributions)::INT AS clan_capital_contributions
                FROM player_snapshots
                WHERE player_tag = %s
                  {time_clause_snap}
                GROUP BY 1
                ORDER BY 1
                """,
                tuple(params_snap),
            )

            last_values = {
                "donations": None,
                "clan_games_points_total": None,
                "clan_capital_contributions": None,
            }
            for row in snapshots:
                for metric in (
                    "donations",
                    "clan_games_points_total",
                    "clan_capital_contributions",
                ):
                    current = _safe_int(row.get(metric))
                    previous = last_values[metric]
                    delta = 0
                    if previous is not None:
                        delta = max(current - _safe_int(previous), 0)
                    row[f"{metric}_delta"] = delta
                    last_values[metric] = current

            params_war: list[Any] = [tag, clan_tag]
            time_clause_war = ""
            if from_time is not None:
                time_clause_war = "AND w.start_time >= %s"
                params_war.append(from_time)

            war_history = _all(
                cur,
                f"""
                SELECT
                    w.war_id,
                    w.war_type,
                    w.state,
                    w.start_time,
                    w.end_time,
                    w.opponent_name,
                    w.outcome,
                    wmp.attacks_used,
                    wmp.attack_capacity,
                    wmp.missed_attacks,
                    wmp.total_attack_stars,
                    wmp.total_attack_destruction
                FROM war_member_performances wmp
                JOIN clan_wars w ON w.war_id = wmp.war_id
                WHERE wmp.player_tag = %s
                  AND wmp.is_our_clan = TRUE
                  AND w.clan_tag = %s
                  {time_clause_war}
                ORDER BY w.start_time DESC
                LIMIT 40
                """,
                tuple(params_war),
            )

            war_summary = _one(
                cur,
                f"""
                SELECT
                    COALESCE(SUM(wmp.attacks_used), 0)::INT AS attacks_used,
                    COALESCE(SUM(wmp.attack_capacity), 0)::INT AS attack_capacity,
                    COALESCE(SUM(wmp.missed_attacks), 0)::INT AS missed_attacks,
                    COALESCE(SUM(wmp.total_attack_stars), 0)::INT AS attack_stars,
                    ROUND(AVG(COALESCE(wmp.total_attack_destruction, 0)), 2) AS avg_attack_destruction
                FROM war_member_performances wmp
                JOIN clan_wars w ON w.war_id = wmp.war_id
                WHERE wmp.player_tag = %s
                  AND wmp.is_our_clan = TRUE
                  AND w.clan_tag = %s
                  {time_clause_war}
                """,
                tuple(params_war),
            )

            capital_history = _all(
                cur,
                """
                SELECT
                    season_start_time,
                    attacks,
                    attack_limit,
                    bonus_attack_limit,
                    capital_resources_looted
                FROM capital_raid_member_stats
                WHERE clan_tag = %s
                  AND player_tag = %s
                ORDER BY season_start_time DESC
                LIMIT 24
                """,
                (clan_tag, tag),
            )

            player_last_snapshot = _one(
                cur,
                """
                SELECT MAX(fetched_at) AS last_snapshot
                FROM player_snapshots
                WHERE player_tag = %s
                """,
                (tag,),
            )

    now_utc = datetime.now(timezone.utc)
    freshness_hours = 9999.0
    if isinstance(player_last_snapshot.get("last_snapshot"), datetime):
        freshness_hours = max(
            (now_utc - player_last_snapshot["last_snapshot"]).total_seconds() / 3600.0,
            0.0,
        )

    latest_cap = capital_history[0] if capital_history else {}
    cap_limit = _safe_int(latest_cap.get("attack_limit")) + _safe_int(latest_cap.get("bonus_attack_limit"))
    cap_ratio = (_safe_int(latest_cap.get("attacks")) / cap_limit) if cap_limit > 0 else 0.0

    player_health = _compute_player_health(
        attacks_used=_safe_int(war_summary.get("attacks_used")),
        attack_capacity=_safe_int(war_summary.get("attack_capacity")),
        missed_attacks=_safe_int(war_summary.get("missed_attacks")),
        donations=_safe_int(player.get("donations")),
        capital_ratio=cap_ratio,
        freshness_hours=freshness_hours,
    )

    chart_snapshots = [
        {
            "label": _dt_label(point.get("bucket"), scale_conf["snapshot_bucket"]),
            "trophies": _safe_int(point.get("trophies")),
            "donations_delta": _safe_int(point.get("donations_delta")),
            "clan_games_delta": _safe_int(point.get("clan_games_points_total_delta")),
            "capital_delta": _safe_int(point.get("clan_capital_contributions_delta")),
        }
        for point in snapshots
    ]

    war_history_chrono = list(reversed(war_history))
    chart_wars = [
        {
            "label": row.get("start_time").astimezone().strftime("%d/%m") if isinstance(row.get("start_time"), datetime) else "-",
            "used": _safe_int(row.get("attacks_used")),
            "capacity": _safe_int(row.get("attack_capacity")),
            "missed": _safe_int(row.get("missed_attacks")),
            "stars": _safe_int(row.get("total_attack_stars")),
        }
        for row in war_history_chrono
    ]

    capital_history_chrono = list(reversed(capital_history))
    chart_capital = [
        {
            "label": row.get("season_start_time").astimezone().strftime("%d/%m")
            if isinstance(row.get("season_start_time"), datetime)
            else "-",
            "loot": _safe_int(row.get("capital_resources_looted")),
            "attacks": _safe_int(row.get("attacks")),
            "capacity": _safe_int(row.get("attack_limit")) + _safe_int(row.get("bonus_attack_limit")),
        }
        for row in capital_history_chrono
    ]

    chart_payload = {
        "scale": scale_key,
        "snapshots": chart_snapshots,
        "war_history": chart_wars,
        "capital_history": chart_capital,
    }

    data_payload: dict[str, Any] = {
        "player": player,
        "clan_tag": clan_tag,
        "scale_key": scale_key,
        "scale_label": scale_conf["label"],
        "scales": _scale_options(),
        "player_health": player_health,
        "war_summary": {
            "attacks_used": _safe_int(war_summary.get("attacks_used")),
            "attack_capacity": _safe_int(war_summary.get("attack_capacity")),
            "missed_attacks": _safe_int(war_summary.get("missed_attacks")),
            "attack_stars": _safe_int(war_summary.get("attack_stars")),
            "avg_attack_destruction": _safe_float(war_summary.get("avg_attack_destruction")),
        },
        "war_history": war_history,
        "capital_history": capital_history,
        "freshness_hours": round(freshness_hours, 1),
    }

    return data_payload, chart_payload


@app.get("/")
def dashboard() -> str:
    scale_key = _resolve_scale(request.args.get("scale"))
    data, chart_data = _load_overview(scale_key)
    return render_template("index.html", data=data, chart_data=chart_data)


@app.get("/players/<player_tag>")
def player_detail(player_tag: str) -> str:
    scale_key = _resolve_scale(request.args.get("scale"))
    data, chart_data = _load_player_detail(player_tag, scale_key)
    return render_template("player.html", data=data, chart_data=chart_data)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


def main() -> int:
    port = int(os.getenv("PORT", "8120"))
    serve(app, host="0.0.0.0", port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
