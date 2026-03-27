from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any

from flask import Flask, abort, jsonify, request
import psycopg
from psycopg.rows import dict_row
from waitress import serve

from app.config import DEFAULT_DB_URL, load_config
from app import storage as app_storage
from dashboard.metrics import (
    compute_clan_health as _compute_clan_health,
    compute_delta as _compute_delta,
    compute_monthly_progress as _compute_monthly_progress,
    compute_participation_rate as _compute_participation_rate,
    compute_player_activity_score as _compute_player_activity_score,
    dt_label as _dt_label,
    safe_float as _safe_float,
    safe_int as _safe_int,
    serialize_json as _serialize_json,
    war_bucket_key as _war_bucket_key,
    war_summary_row as _war_summary_row,
)

try:
    CONFIG = load_config()
except Exception:  # noqa: BLE001
    CONFIG = None

DB_URL = os.getenv("DASHBOARD_DB_URL") or (CONFIG.db_url if CONFIG else DEFAULT_DB_URL)
DEFAULT_CLAN_TAG = os.getenv("DASHBOARD_CLAN_TAG") or (CONFIG.clan_id if CONFIG else "")
APP_VERSION_PATH = os.getenv("APP_VERSION_FILE", "/app/VERSION")
APP_VERSION_OVERRIDE = os.getenv("APP_VERSION")

SCALES: dict[str, dict[str, Any]] = {
    "7d": {"label": "7 jours", "days": 7, "snapshot_bucket": "hour", "war_bucket": "day"},
    "30d": {"label": "30 jours", "days": 30, "snapshot_bucket": "day", "war_bucket": "week"},
    "90d": {"label": "90 jours", "days": 90, "snapshot_bucket": "day", "war_bucket": "week"},
    "365d": {"label": "365 jours", "days": 365, "snapshot_bucket": "week", "war_bucket": "month"},
    "all": {"label": "Depuis le début", "days": None, "snapshot_bucket": "week", "war_bucket": "month"},
}
DEFAULT_SCALE = "30d"

app = Flask(__name__)
_SCHEMA_READY = False


def _connect() -> psycopg.Connection:
    return psycopg.connect(DB_URL, row_factory=dict_row)


def _ensure_runtime_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _connect() as conn:
        app_storage.ensure_runtime_schema(conn)
        conn.commit()
    _SCHEMA_READY = True


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


def _app_version() -> str:
    if APP_VERSION_OVERRIDE:
        return APP_VERSION_OVERRIDE.strip()
    try:
        with open(APP_VERSION_PATH, "r", encoding="utf-8") as file:
            version = file.read().strip()
            if version:
                return version
    except OSError:
        pass
    return "0.0.0"


def _meta_payload(scale_key: str, scale_conf: dict[str, Any]) -> dict[str, Any]:
    return {
        "scale": scale_key,
        "scale_label": scale_conf["label"],
        "scales": _scale_options(),
        "app_version": _app_version(),
        "generated_at": datetime.now(timezone.utc),
    }


def _empty_overview_payload(scale_key: str, scale_conf: dict[str, Any]) -> dict[str, Any]:
    return {
        "meta": _meta_payload(scale_key, scale_conf),
        "clan": {"tag": DEFAULT_CLAN_TAG, "name": "Aucune donnée", "members": 0},
        "kpis": {},
        "wars": {
            "overall": _war_summary_row({}),
            "gdc": _war_summary_row({}),
            "ldc": _war_summary_row({}),
        },
        "health": {"score": 0.0, "grade": "D", "components": {}},
        "players": [],
        "at_risk": [],
        "top_contributors": [],
        "capital": {
            "latest": {},
            "top_members": [],
            "used_attacks": 0,
            "capacity_attacks": 0,
            "history": [],
            "summary": {},
        },
        "freshness": {},
        "charts": {
            "clan_points": [],
            "war_outcomes": {"gdc": [], "ldc": [], "overall": []},
            "health_components": [],
            "clan_games": [],
            "capital_weekends": [],
        },
    }


def _load_overview(scale_key: str) -> dict[str, Any]:
    _ensure_runtime_schema()
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
                return _empty_overview_payload(scale_key, scale_conf)

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

            clan_games_params: list[Any] = [clan_tag]
            clan_games_time_clause = ""
            display_month_floor: datetime | None = None
            if from_time is not None:
                lookup_from = from_time - timedelta(days=40)
                clan_games_time_clause = "AND fetched_at >= %s"
                clan_games_params.append(lookup_from)
                display_month_floor = from_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            clan_games_monthly_raw = _all(
                cur,
                f"""
                WITH monthly_player AS (
                    SELECT
                        player_tag,
                        date_trunc('month', fetched_at) AS month_bucket,
                        MAX(clan_games_points_total)::BIGINT AS month_total,
                        MIN(clan_games_points_total)::BIGINT AS month_floor_total
                    FROM player_snapshots
                    WHERE clan_tag = %s
                      {clan_games_time_clause}
                    GROUP BY 1, 2
                ),
                monthly_clan AS (
                    SELECT
                        month_bucket,
                        COALESCE(SUM(month_total), 0)::BIGINT AS clan_total,
                        COALESCE(SUM(month_floor_total), 0)::BIGINT AS clan_floor_total
                    FROM monthly_player
                    GROUP BY 1
                )
                SELECT
                    month_bucket,
                    clan_total,
                    clan_floor_total
                FROM monthly_clan
                ORDER BY month_bucket
                """,
                tuple(clan_games_params),
            )

            clan_games_monthly = []
            previous_clan_games_total: int | None = None
            for row in clan_games_monthly_raw:
                row["monthly_delta"] = _compute_monthly_progress(
                    row.get("clan_total"),
                    previous_total=previous_clan_games_total,
                    month_floor_total=row.get("clan_floor_total"),
                )
                previous_clan_games_total = _safe_int(row.get("clan_total"))
                month_bucket = row.get("month_bucket")
                if display_month_floor is not None and isinstance(month_bucket, datetime) and month_bucket < display_month_floor:
                    continue
                clan_games_monthly.append(row)

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

            war_summary_rows = _all(
                cur,
                f"""
                SELECT
                    COALESCE(NULLIF(war_type, ''), 'regular') AS war_type,
                    COUNT(*) FILTER (WHERE state = 'warEnded')::INT AS wars_ended,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'win')::INT AS wins,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'loss')::INT AS losses,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'draw')::INT AS draws
                FROM clan_wars
                WHERE clan_tag = %s
                  {time_clause_war}
                GROUP BY 1
                """,
                tuple(params_war),
            )

            participation_rows = _all(
                cur,
                f"""
                SELECT
                    COALESCE(NULLIF(w.war_type, ''), 'regular') AS war_type,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                            END
                        ),
                        0
                    )::INT AS attack_capacity,
                    COALESCE(SUM(wmp.attacks_used), 0)::INT AS attacks_used,
                    COALESCE(
                        SUM(
                            GREATEST(
                                CASE
                                    WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                    ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                END - COALESCE(wmp.attacks_used, 0),
                                0
                            )
                        ),
                        0
                    )::INT AS missed_attacks
                FROM war_member_performances wmp
                JOIN clan_wars w ON w.war_id = wmp.war_id
                WHERE w.clan_tag = %s
                  AND wmp.is_our_clan = TRUE
                  AND w.state = 'warEnded'
                  {time_clause_war}
                GROUP BY 1
                """,
                tuple(params_war),
            )

            summary_raw = {
                "gdc": {},
                "ldc": {},
            }
            for row in war_summary_rows:
                summary_raw[_war_bucket_key(str(row.get("war_type") or "regular"))] = row

            participation_raw = {
                "gdc": {},
                "ldc": {},
            }
            for row in participation_rows:
                participation_raw[_war_bucket_key(str(row.get("war_type") or "regular"))] = row

            wars_by_type: dict[str, dict[str, Any]] = {}
            for key in ("gdc", "ldc"):
                merged = {
                    **summary_raw.get(key, {}),
                    **participation_raw.get(key, {}),
                }
                wars_by_type[key] = _war_summary_row(merged)

            wars_overall = _war_summary_row(
                {
                    "wars_ended": wars_by_type["gdc"]["wars_ended"] + wars_by_type["ldc"]["wars_ended"],
                    "wins": wars_by_type["gdc"]["wins"] + wars_by_type["ldc"]["wins"],
                    "losses": wars_by_type["gdc"]["losses"] + wars_by_type["ldc"]["losses"],
                    "draws": wars_by_type["gdc"]["draws"] + wars_by_type["ldc"]["draws"],
                    "attack_capacity": wars_by_type["gdc"]["attack_capacity"] + wars_by_type["ldc"]["attack_capacity"],
                    "attacks_used": wars_by_type["gdc"]["attacks_used"] + wars_by_type["ldc"]["attacks_used"],
                    "missed_attacks": wars_by_type["gdc"]["missed_attacks"] + wars_by_type["ldc"]["missed_attacks"],
                }
            )

            war_outcomes_rows = _all(
                cur,
                f"""
                SELECT
                    date_trunc('{scale_conf['war_bucket']}', start_time) AS bucket,
                    COALESCE(NULLIF(war_type, ''), 'regular') AS war_type,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'win')::INT AS wins,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'loss')::INT AS losses,
                    COUNT(*) FILTER (WHERE state = 'warEnded' AND outcome = 'draw')::INT AS draws
                FROM clan_wars
                WHERE clan_tag = %s
                  {time_clause_war}
                GROUP BY 1, 2
                ORDER BY 1, 2
                """,
                tuple(params_war),
            )

            latest_capital = _one(
                cur,
                """
                SELECT
                    season_start_time,
                    season_end_time,
                    state,
                    capital_total_loot,
                    total_attacks,
                    enemy_districts_destroyed,
                    offensive_reward,
                    defensive_reward
                FROM capital_raid_seasons
                WHERE clan_tag = %s
                ORDER BY season_start_time DESC
                LIMIT 1
                """,
                (clan_tag,),
            )

            capital_history_rows = _all(
                cur,
                f"""
                WITH usage AS (
                    SELECT
                        clan_tag,
                        season_start_time,
                        COUNT(*)::INT AS roster_size,
                        COUNT(*) FILTER (
                            WHERE COALESCE(attacks, 0) > 0 OR COALESCE(capital_resources_looted, 0) > 0
                        )::INT AS active_raiders,
                        COALESCE(SUM(attacks), 0)::INT AS used_attacks,
                        COALESCE(SUM(attack_limit), 0)::INT + COALESCE(SUM(bonus_attack_limit), 0)::INT AS capacity_attacks
                    FROM capital_raid_member_stats
                    WHERE clan_tag = %s
                    GROUP BY 1, 2
                )
                SELECT
                    s.season_start_time,
                    s.season_end_time,
                    s.state,
                    s.capital_total_loot,
                    s.total_attacks,
                    s.enemy_districts_destroyed,
                    s.offensive_reward,
                    s.defensive_reward,
                    COALESCE(u.roster_size, 0)::INT AS roster_size,
                    COALESCE(u.active_raiders, 0)::INT AS active_raiders,
                    COALESCE(u.used_attacks, 0)::INT AS used_attacks,
                    COALESCE(u.capacity_attacks, 0)::INT AS capacity_attacks
                FROM capital_raid_seasons s
                LEFT JOIN usage u
                  ON u.clan_tag = s.clan_tag
                 AND u.season_start_time = s.season_start_time
                WHERE s.clan_tag = %s
                  {"AND s.season_start_time >= %s" if from_time is not None else ""}
                ORDER BY s.season_start_time DESC
                """,
                tuple([clan_tag, clan_tag] + ([from_time] if from_time is not None else [])),
            )

            capital_top: list[dict[str, Any]] = []
            latest_capital_members_by_tag: dict[str, dict[str, Any]] = {}
            capital_capacity = 0
            capital_used = 0
            if latest_capital:
                capital_members = _all(
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
                    """,
                    (clan_tag, latest_capital["season_start_time"]),
                )
                latest_capital_members_by_tag = {
                    str(row.get("player_tag")): row for row in capital_members if row.get("player_tag")
                }
                capital_top = sorted(
                    capital_members,
                    key=lambda row: (
                        -_safe_int(row.get("capital_resources_looted")),
                        -_safe_int(row.get("attacks")),
                    ),
                )[:12]
                capital_used = sum(_safe_int(row.get("attacks")) for row in capital_members)
                capital_capacity = sum(
                    _safe_int(row.get("attack_limit")) + _safe_int(row.get("bonus_attack_limit"))
                    for row in capital_members
                )

            now_utc = datetime.now(timezone.utc)
            capital_history: list[dict[str, Any]] = []
            for row in capital_history_rows:
                used_attacks = _safe_int(row.get("used_attacks"), _safe_int(row.get("total_attacks")))
                capacity_attacks = _safe_int(row.get("capacity_attacks"))
                total_loot = _safe_int(row.get("capital_total_loot"))
                season_end_time = row.get("season_end_time")
                is_completed = isinstance(season_end_time, datetime) and season_end_time <= now_utc
                capital_history.append(
                    {
                        **row,
                        "used_attacks": used_attacks,
                        "capacity_attacks": capacity_attacks,
                        "participation_rate": _compute_participation_rate(used_attacks, capacity_attacks),
                        "loot_per_attack": round((total_loot / used_attacks), 1) if used_attacks > 0 else 0.0,
                        "is_completed": is_completed,
                    }
                )

            capital_history_chrono = list(reversed(capital_history))
            previous_capital_row: dict[str, Any] | None = None
            for row in capital_history_chrono:
                row["capital_total_loot_delta"] = _compute_delta(
                    _safe_int(row.get("capital_total_loot")),
                    _safe_int(previous_capital_row.get("capital_total_loot")) if previous_capital_row else None,
                )
                row["used_attacks_delta"] = _compute_delta(
                    _safe_int(row.get("used_attacks")),
                    _safe_int(previous_capital_row.get("used_attacks")) if previous_capital_row else None,
                )
                row["enemy_districts_destroyed_delta"] = _compute_delta(
                    _safe_int(row.get("enemy_districts_destroyed")),
                    _safe_int(previous_capital_row.get("enemy_districts_destroyed")) if previous_capital_row else None,
                )
                row["participation_rate_delta"] = _compute_delta(
                    _safe_float(row.get("participation_rate")),
                    _safe_float(previous_capital_row.get("participation_rate")) if previous_capital_row else None,
                )
                previous_capital_row = row

            latest_completed_capital = next((row for row in capital_history if row.get("is_completed")), {})
            best_capital_weekend = (
                max(capital_history, key=lambda row: _safe_int(row.get("capital_total_loot"))) if capital_history else {}
            )
            completed_capital_weekends = [row for row in capital_history if row.get("is_completed")]
            average_loot = round(
                sum(_safe_int(row.get("capital_total_loot")) for row in completed_capital_weekends) / len(completed_capital_weekends),
                1,
            ) if completed_capital_weekends else 0.0
            average_participation = round(
                sum(_safe_float(row.get("participation_rate")) for row in completed_capital_weekends) / len(completed_capital_weekends),
                1,
            ) if completed_capital_weekends else 0.0
            recent_completed = completed_capital_weekends[:3]
            previous_completed = completed_capital_weekends[3:6]
            recent_completed_avg_loot = round(
                sum(_safe_int(row.get("capital_total_loot")) for row in recent_completed) / len(recent_completed),
                1,
            ) if recent_completed else 0.0
            previous_completed_avg_loot = round(
                sum(_safe_int(row.get("capital_total_loot")) for row in previous_completed) / len(previous_completed),
                1,
            ) if previous_completed else 0.0
            recent_completed_avg_participation = round(
                sum(_safe_float(row.get("participation_rate")) for row in recent_completed) / len(recent_completed),
                1,
            ) if recent_completed else 0.0
            previous_completed_avg_participation = round(
                sum(_safe_float(row.get("participation_rate")) for row in previous_completed) / len(previous_completed),
                1,
            ) if previous_completed else 0.0

            clan_games_player_monthly_rows = _all(
                cur,
                """
                WITH monthly AS (
                    SELECT
                        player_tag,
                        date_trunc('month', fetched_at) AS month_bucket,
                        MAX(clan_games_points_total)::INT AS month_total,
                        MIN(clan_games_points_total)::INT AS month_floor_total
                    FROM player_snapshots
                    WHERE clan_tag = %s
                      AND fetched_at >= date_trunc('month', NOW()) - INTERVAL '1 month'
                    GROUP BY 1, 2
                )
                SELECT
                    player_tag,
                    MAX(month_total) FILTER (WHERE month_bucket = date_trunc('month', NOW()))::INT AS current_month_total,
                    MAX(month_floor_total) FILTER (WHERE month_bucket = date_trunc('month', NOW()))::INT AS current_month_floor_total,
                    MAX(month_total) FILTER (
                        WHERE month_bucket = date_trunc('month', NOW()) - INTERVAL '1 month'
                    )::INT AS previous_month_total
                FROM monthly
                GROUP BY player_tag
                """,
                (clan_tag,),
            )
            clan_games_delta_by_player: dict[str, int] = {}
            for row in clan_games_player_monthly_rows:
                player_tag = row.get("player_tag")
                if not player_tag:
                    continue
                clan_games_delta_by_player[str(player_tag)] = _compute_monthly_progress(
                    row.get("current_month_total"),
                    previous_total=row.get("previous_month_total"),
                    month_floor_total=row.get("current_month_floor_total"),
                )

            snapshot_activity_rows = _all(
                cur,
                """
                WITH deltas AS (
                    SELECT
                        player_tag,
                        fetched_at,
                        ROW_NUMBER() OVER (PARTITION BY player_tag ORDER BY fetched_at DESC) AS rn,
                        GREATEST(
                            COALESCE(trophies, 0)
                                - COALESCE(LAG(trophies) OVER (PARTITION BY player_tag ORDER BY fetched_at), COALESCE(trophies, 0)),
                            0
                        )::BIGINT AS trophies_delta,
                        GREATEST(
                            COALESCE(war_stars, 0)
                                - COALESCE(LAG(war_stars) OVER (PARTITION BY player_tag ORDER BY fetched_at), COALESCE(war_stars, 0)),
                            0
                        )::BIGINT AS war_stars_delta,
                        GREATEST(
                            COALESCE(looted_resources_total, 0)
                                - COALESCE(
                                    LAG(looted_resources_total) OVER (PARTITION BY player_tag ORDER BY fetched_at),
                                    COALESCE(looted_resources_total, 0)
                                ),
                            0
                        )::BIGINT AS looted_resources_delta,
                        GREATEST(
                            COALESCE(clan_capital_contributions, 0)
                                - COALESCE(
                                    LAG(clan_capital_contributions) OVER (PARTITION BY player_tag ORDER BY fetched_at),
                                    COALESCE(clan_capital_contributions, 0)
                                ),
                            0
                        )::BIGINT AS capital_delta,
                        GREATEST(
                            COALESCE(donations, 0)
                                - COALESCE(LAG(donations) OVER (PARTITION BY player_tag ORDER BY fetched_at), COALESCE(donations, 0)),
                            0
                        )::BIGINT AS donations_delta
                    FROM player_snapshots
                    WHERE clan_tag = %s
                ),
                changes AS (
                    SELECT
                        player_tag,
                        fetched_at,
                        rn,
                        (
                            trophies_delta > 0
                            OR war_stars_delta > 0
                            OR looted_resources_delta > 0
                            OR capital_delta > 0
                            OR donations_delta > 0
                        ) AS has_change
                    FROM deltas
                )
                SELECT
                    player_tag,
                    MAX(fetched_at) FILTER (WHERE has_change) AS last_change_at,
                    MAX(fetched_at) FILTER (WHERE rn = 1 AND has_change) AS last_fetch_change_at
                FROM changes
                GROUP BY player_tag
                """,
                (clan_tag,),
            )
            snapshot_activity_by_tag = {
                str(row.get("player_tag")): row for row in snapshot_activity_rows if row.get("player_tag")
            }

            player_rows = _all(
                cur,
                f"""
                WITH war AS (
                    SELECT
                        wmp.player_tag,
                        MAX(wmp.player_name) AS player_name,
                        SUM(
                            CASE
                                WHEN w.state = 'warEnded' THEN
                                    CASE
                                        WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                        ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                    END
                                ELSE 0
                            END
                        )::INT AS attack_capacity,
                        SUM(COALESCE(wmp.attacks_used, 0)) FILTER (WHERE w.state = 'warEnded')::INT AS attacks_used,
                        SUM(
                            CASE
                                WHEN w.state = 'warEnded' THEN
                                    GREATEST(
                                        CASE
                                            WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                            ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                        END - COALESCE(wmp.attacks_used, 0),
                                        0
                                    )
                                ELSE 0
                            END
                        )::INT AS missed_attacks,
                        SUM(wmp.total_attack_stars) FILTER (WHERE w.state = 'warEnded')::INT AS attack_stars,
                        ROUND(AVG(COALESCE(wmp.total_attack_destruction, 0)) FILTER (WHERE w.state = 'warEnded'), 2)
                            AS avg_attack_destruction,
                        SUM(
                            GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                        ) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                        )::INT AS gdc_attack_capacity,
                        SUM(COALESCE(wmp.attacks_used, 0)) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                        )::INT
                            AS gdc_attacks_used,
                        SUM(
                            GREATEST(GREATEST(COALESCE(wmp.attack_capacity, 2), 1) - COALESCE(wmp.attacks_used, 0), 0)
                        ) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                        )::INT AS gdc_missed_attacks,
                        SUM(1) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                        )::INT AS ldc_attack_capacity,
                        SUM(COALESCE(wmp.attacks_used, 0)) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                        )::INT
                            AS ldc_attacks_used,
                        SUM(GREATEST(1 - COALESCE(wmp.attacks_used, 0), 0)) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                        )::INT AS ldc_missed_attacks
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
                    m.looted_resources_total,
                    m.clan_capital_contributions,
                    COALESCE(w.attack_capacity, 0)::INT AS attack_capacity,
                    COALESCE(w.attacks_used, 0)::INT AS attacks_used,
                    COALESCE(w.missed_attacks, 0)::INT AS missed_attacks,
                    COALESCE(w.attack_stars, 0)::INT AS attack_stars,
                    COALESCE(w.avg_attack_destruction, 0)::NUMERIC(8,2) AS avg_attack_destruction,
                    COALESCE(w.gdc_attack_capacity, 0)::INT AS gdc_attack_capacity,
                    COALESCE(w.gdc_attacks_used, 0)::INT AS gdc_attacks_used,
                    COALESCE(w.gdc_missed_attacks, 0)::INT AS gdc_missed_attacks,
                    COALESCE(w.ldc_attack_capacity, 0)::INT AS ldc_attack_capacity,
                    COALESCE(w.ldc_attacks_used, 0)::INT AS ldc_attacks_used,
                    COALESCE(w.ldc_missed_attacks, 0)::INT AS ldc_missed_attacks,
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
                overall_capacity = _safe_int(row.get("attack_capacity"))
                overall_used = _safe_int(row.get("attacks_used"))
                overall_missed = _safe_int(row.get("missed_attacks"))

                gdc_capacity = _safe_int(row.get("gdc_attack_capacity"))
                gdc_used = _safe_int(row.get("gdc_attacks_used"))
                gdc_missed = _safe_int(row.get("gdc_missed_attacks"))

                ldc_capacity = _safe_int(row.get("ldc_attack_capacity"))
                ldc_used = _safe_int(row.get("ldc_attacks_used"))
                ldc_missed = _safe_int(row.get("ldc_missed_attacks"))

                player_tag = str(row.get("player_tag") or "")
                player_cap_entry = latest_capital_members_by_tag.get(player_tag)
                player_raid_loot = 0
                if player_cap_entry:
                    player_raid_loot = _safe_int(player_cap_entry.get("capital_resources_looted"))
                row["latest_raid_loot"] = player_raid_loot
                row["clan_games_monthly_delta"] = clan_games_delta_by_player.get(player_tag, 0)
                row["looted_resources_total"] = _safe_int(row.get("looted_resources_total"))

                activity_row = snapshot_activity_by_tag.get(player_tag, {})
                estimated_last_activity_at = activity_row.get("last_fetch_change_at") or activity_row.get("last_change_at")
                row["estimated_last_activity_at"] = estimated_last_activity_at
                if isinstance(estimated_last_activity_at, datetime):
                    row["last_activity_hours"] = round(
                        max((now_utc - estimated_last_activity_at).total_seconds() / 3600.0, 0.0),
                        1,
                    )
                else:
                    row["last_activity_hours"] = 9999.0

                row["overall"] = {
                    "attack_capacity": overall_capacity,
                    "attacks_used": overall_used,
                    "missed_attacks": overall_missed,
                    "attack_stars": _safe_int(row.get("attack_stars")),
                    "avg_attack_destruction": _safe_float(row.get("avg_attack_destruction")),
                    "participation_rate": _compute_participation_rate(overall_used, overall_capacity),
                }
                row["gdc"] = {
                    "attack_capacity": gdc_capacity,
                    "attacks_used": gdc_used,
                    "missed_attacks": gdc_missed,
                    "participation_rate": _compute_participation_rate(gdc_used, gdc_capacity),
                }
                row["ldc"] = {
                    "attack_capacity": ldc_capacity,
                    "attacks_used": ldc_used,
                    "missed_attacks": ldc_missed,
                    "participation_rate": _compute_participation_rate(ldc_used, ldc_capacity),
                }

                row["health_score"] = _compute_player_activity_score(
                    attack_stars=_safe_int(row.get("overall", {}).get("attack_stars")),
                    donations=_safe_int(row.get("donations")),
                    raid_loot=_safe_int(row.get("latest_raid_loot")),
                    jdc=_safe_int(row.get("clan_games_monthly_delta")),
                    missed_attacks=overall_missed,
                )

                row["player_slug"] = str(row.get("player_tag") or "").lstrip("#")

            at_risk = sorted(
                player_rows,
                key=lambda row: (
                    -_safe_int(row.get("overall", {}).get("missed_attacks")),
                    _safe_float(row.get("health_score")),
                ),
            )[:10]

            top_contributors = sorted(
                player_rows,
                key=lambda row: (
                    -_safe_int(row.get("donations")),
                    -_safe_int(row.get("clan_capital_contributions")),
                    -_safe_int(row.get("overall", {}).get("attack_stars")),
                ),
            )[:10]

            freshness = _one(
                cur,
                """
                SELECT
                    (SELECT MIN(fetched_at) FROM clan_snapshots WHERE clan_tag = %s) AS first_snapshot,
                    (SELECT MAX(fetched_at) FROM clan_snapshots WHERE clan_tag = %s) AS latest_snapshot,
                    (SELECT MAX(updated_at) FROM clan_wars WHERE clan_tag = %s) AS latest_war,
                    (SELECT MAX(updated_at) FROM capital_raid_seasons WHERE clan_tag = %s) AS latest_capital,
                    (SELECT MAX(updated_at) FROM players WHERE clan_tag = %s) AS latest_players
                """,
                (clan_tag, clan_tag, clan_tag, clan_tag, clan_tag),
            )

    latest_snapshot = freshness.get("latest_snapshot")
    freshness_hours = 9999.0
    if isinstance(latest_snapshot, datetime):
        freshness_hours = max((datetime.now(timezone.utc) - latest_snapshot).total_seconds() / 3600.0, 0.0)

    health = _compute_clan_health(
        war_capacity=wars_overall["attack_capacity"],
        war_missed=wars_overall["missed_attacks"],
        donations_avg=_safe_float(members_agg.get("avg_social_score")),
        capital_capacity=capital_capacity,
        capital_used=capital_used,
        freshness_hours=freshness_hours,
    )

    chart_points = [
        {
            "label": _dt_label(point.get("bucket"), scale_conf["snapshot_bucket"]),
            "bucket": point.get("bucket"),
            "clan_points": _safe_int(point.get("clan_points")),
            "members": _safe_int(point.get("members")),
        }
        for point in clan_points_series
    ]

    war_outcomes = {
        "gdc": [],
        "ldc": [],
        "overall": [],
    }
    overall_by_bucket: dict[str, dict[str, Any]] = {}

    for row in war_outcomes_rows:
        bucket_dt = row.get("bucket")
        bucket_label = _dt_label(bucket_dt, scale_conf["war_bucket"])
        item = {
            "label": bucket_label,
            "bucket": bucket_dt,
            "wins": _safe_int(row.get("wins")),
            "losses": _safe_int(row.get("losses")),
            "draws": _safe_int(row.get("draws")),
        }
        bucket_key = _war_bucket_key(str(row.get("war_type") or "regular"))
        war_outcomes[bucket_key].append(item)

        agg = overall_by_bucket.setdefault(
            bucket_label,
            {
                "label": bucket_label,
                "bucket": bucket_dt,
                "wins": 0,
                "losses": 0,
                "draws": 0,
            },
        )
        agg["wins"] += item["wins"]
        agg["losses"] += item["losses"]
        agg["draws"] += item["draws"]

    war_outcomes["overall"] = sorted(
        overall_by_bucket.values(),
        key=lambda row: row["bucket"].timestamp() if isinstance(row.get("bucket"), datetime) else 0.0,
    )

    clan_games_chart = [
        {
            "label": point.get("month_bucket").astimezone().strftime("%m/%Y")
            if isinstance(point.get("month_bucket"), datetime)
            else "-",
            "bucket": point.get("month_bucket"),
            "clan_total": _safe_int(point.get("clan_total")),
            "monthly_delta": _safe_int(point.get("monthly_delta")),
        }
        for point in clan_games_monthly
    ]
    clan_games_current_month_delta = _safe_int(clan_games_chart[-1].get("monthly_delta")) if clan_games_chart else 0
    clan_games_previous_month_delta = _safe_int(clan_games_chart[-2].get("monthly_delta")) if len(clan_games_chart) > 1 else 0

    chart_capital_weekends = [
        {
            "label": row.get("season_start_time").astimezone().strftime("%d/%m")
            if isinstance(row.get("season_start_time"), datetime)
            else "-",
            "bucket": row.get("season_start_time"),
            "loot": _safe_int(row.get("capital_total_loot")),
            "attacks": _safe_int(row.get("used_attacks")),
            "capacity": _safe_int(row.get("capacity_attacks")),
            "districts": _safe_int(row.get("enemy_districts_destroyed")),
            "active_raiders": _safe_int(row.get("active_raiders")),
            "participation_rate": _safe_float(row.get("participation_rate")),
            "loot_per_attack": _safe_float(row.get("loot_per_attack")),
            "is_completed": bool(row.get("is_completed")),
        }
        for row in capital_history_chrono
    ]

    return {
        "meta": _meta_payload(scale_key, scale_conf),
        "clan": clan,
        "kpis": {
            "active_members": _safe_int(members_agg.get("active_members")),
            "avg_trophies": round(_safe_float(members_agg.get("avg_trophies")), 1),
            "donations_sent": _safe_int(members_agg.get("donations_sent")),
            "donations_received": _safe_int(members_agg.get("donations_received")),
            "clan_games_current_month_delta": clan_games_current_month_delta,
            "clan_games_previous_month_delta": clan_games_previous_month_delta,
            "capital_contributions": _safe_int(members_agg.get("capital_contributions")),
            "clan_points_delta": points_delta,
            "members_delta": members_delta,
        },
        "wars": {
            "overall": wars_overall,
            "gdc": wars_by_type["gdc"],
            "ldc": wars_by_type["ldc"],
        },
        "health": health,
        "players": player_rows,
        "at_risk": at_risk,
        "top_contributors": top_contributors,
        "capital": {
            "latest": latest_capital,
            "top_members": capital_top,
            "used_attacks": capital_used,
            "capacity_attacks": capital_capacity,
            "history": capital_history,
            "summary": {
                "latest_completed": latest_completed_capital,
                "best_weekend": best_capital_weekend,
                "average_loot": average_loot,
                "average_participation": average_participation,
                "recent_completed_avg_loot": recent_completed_avg_loot,
                "previous_completed_avg_loot": previous_completed_avg_loot,
                "recent_completed_avg_participation": recent_completed_avg_participation,
                "previous_completed_avg_participation": previous_completed_avg_participation,
                "completed_weekends": len(completed_capital_weekends),
            },
        },
        "freshness": freshness,
        "charts": {
            "clan_points": chart_points,
            "war_outcomes": war_outcomes,
            "health_components": [
                {"label": key.replace("_", " ").title(), "value": _safe_float(value)}
                for key, value in health["components"].items()
            ],
            "clan_games": clan_games_chart,
            "capital_weekends": chart_capital_weekends,
        },
    }


def _load_player_detail(player_tag: str, scale_key: str) -> dict[str, Any]:
    _ensure_runtime_schema()
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
                    looted_resources_total,
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
                    MAX(looted_resources_total)::BIGINT AS looted_resources_total,
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
                "looted_resources_total": None,
                "clan_capital_contributions": None,
            }
            for row in snapshots:
                for metric in (
                    "donations",
                    "clan_games_points_total",
                    "looted_resources_total",
                    "clan_capital_contributions",
                ):
                    current = _safe_int(row.get(metric))
                    previous = last_values[metric]
                    delta = 0
                    if previous is not None:
                        delta = max(current - _safe_int(previous), 0)
                    row[f"{metric}_delta"] = delta
                    last_values[metric] = current

            player_clan_games_params: list[Any] = [tag]
            player_clan_games_time_clause = ""
            player_display_month_floor: datetime | None = None
            if from_time is not None:
                player_clan_games_time_clause = "AND fetched_at >= %s"
                player_clan_games_params.append(from_time - timedelta(days=40))
                player_display_month_floor = from_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            player_clan_games_monthly_raw = _all(
                cur,
                f"""
                WITH monthly AS (
                    SELECT
                        date_trunc('month', fetched_at) AS month_bucket,
                        MAX(clan_games_points_total)::BIGINT AS month_total,
                        MIN(clan_games_points_total)::BIGINT AS month_floor_total
                    FROM player_snapshots
                    WHERE player_tag = %s
                      {player_clan_games_time_clause}
                    GROUP BY 1
                )
                SELECT
                    month_bucket,
                    month_total,
                    month_floor_total
                FROM monthly
                ORDER BY month_bucket
                """,
                tuple(player_clan_games_params),
            )

            player_clan_games_monthly = []
            previous_player_clan_games_total: int | None = None
            for row in player_clan_games_monthly_raw:
                row["monthly_delta"] = _compute_monthly_progress(
                    row.get("month_total"),
                    previous_total=previous_player_clan_games_total,
                    month_floor_total=row.get("month_floor_total"),
                )
                previous_player_clan_games_total = _safe_int(row.get("month_total"))
                month_bucket = row.get("month_bucket")
                if (
                    player_display_month_floor is not None
                    and isinstance(month_bucket, datetime)
                    and month_bucket < player_display_month_floor
                ):
                    continue
                player_clan_games_monthly.append(row)

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
                    COALESCE(wmp.attacks_used, 0)::INT AS attacks_used,
                    (
                        CASE
                            WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                            ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                        END
                    )::INT AS attack_capacity,
                    (
                        CASE
                            WHEN w.state = 'warEnded' THEN
                                GREATEST(
                                    CASE
                                        WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                        ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                    END - COALESCE(wmp.attacks_used, 0),
                                    0
                                )
                            ELSE 0
                        END
                    )::INT AS missed_attacks,
                    wmp.total_attack_stars,
                    wmp.total_attack_destruction
                FROM war_member_performances wmp
                JOIN clan_wars w ON w.war_id = wmp.war_id
                WHERE wmp.player_tag = %s
                  AND wmp.is_our_clan = TRUE
                  AND w.clan_tag = %s
                  {time_clause_war}
                ORDER BY w.start_time DESC
                LIMIT 60
                """,
                tuple(params_war),
            )

            war_summary = _one(
                cur,
                f"""
                SELECT
                    COALESCE(SUM(wmp.attacks_used) FILTER (WHERE w.state = 'warEnded'), 0)::INT AS attacks_used,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN w.state = 'warEnded' THEN
                                    CASE
                                        WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                        ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                    END
                                ELSE 0
                            END
                        ),
                        0
                    )::INT AS attack_capacity,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN w.state = 'warEnded' THEN
                                    GREATEST(
                                        CASE
                                            WHEN COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl' THEN 1
                                            ELSE GREATEST(COALESCE(wmp.attack_capacity, 2), 1)
                                        END - COALESCE(wmp.attacks_used, 0),
                                        0
                                    )
                                ELSE 0
                            END
                        ),
                        0
                    )::INT AS missed_attacks,
                    COALESCE(SUM(wmp.total_attack_stars) FILTER (WHERE w.state = 'warEnded'), 0)::INT AS attack_stars,
                    ROUND(
                        AVG(COALESCE(wmp.total_attack_destruction, 0)) FILTER (WHERE w.state = 'warEnded'),
                        2
                    ) AS avg_attack_destruction,
                    COALESCE(
                        SUM(wmp.attacks_used) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                        ),
                        0
                    )::INT AS gdc_attacks_used,
                    COALESCE(
                        SUM(GREATEST(COALESCE(wmp.attack_capacity, 2), 1)) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                        ),
                        0
                    )::INT AS gdc_attack_capacity,
                    COALESCE(
                        SUM(GREATEST(GREATEST(COALESCE(wmp.attack_capacity, 2), 1) - COALESCE(wmp.attacks_used, 0), 0))
                            FILTER (
                                WHERE w.state = 'warEnded'
                                  AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'regular'
                            ),
                        0
                    )::INT AS gdc_missed_attacks,
                    COALESCE(
                        SUM(wmp.attacks_used) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                        ),
                        0
                    )::INT AS ldc_attacks_used,
                    COALESCE(
                        SUM(1) FILTER (
                            WHERE w.state = 'warEnded'
                              AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                        ),
                        0
                    )::INT AS ldc_attack_capacity,
                    COALESCE(
                        SUM(GREATEST(1 - COALESCE(wmp.attacks_used, 0), 0))
                            FILTER (
                                WHERE w.state = 'warEnded'
                                  AND COALESCE(NULLIF(w.war_type, ''), 'regular') = 'cwl'
                            ),
                        0
                    )::INT AS ldc_missed_attacks
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

            snapshot_activity = _one(
                cur,
                """
                WITH deltas AS (
                    SELECT
                        fetched_at,
                        ROW_NUMBER() OVER (ORDER BY fetched_at DESC) AS rn,
                        GREATEST(COALESCE(trophies, 0) - COALESCE(LAG(trophies) OVER (ORDER BY fetched_at), COALESCE(trophies, 0)), 0)
                            AS trophies_delta,
                        GREATEST(COALESCE(war_stars, 0) - COALESCE(LAG(war_stars) OVER (ORDER BY fetched_at), COALESCE(war_stars, 0)), 0)
                            AS war_stars_delta,
                        GREATEST(
                            COALESCE(clan_capital_contributions, 0)
                                - COALESCE(
                                    LAG(clan_capital_contributions) OVER (ORDER BY fetched_at),
                                    COALESCE(clan_capital_contributions, 0)
                                ),
                            0
                        ) AS capital_delta,
                        GREATEST(
                            COALESCE(looted_resources_total, 0)
                                - COALESCE(
                                    LAG(looted_resources_total) OVER (ORDER BY fetched_at),
                                    COALESCE(looted_resources_total, 0)
                                ),
                            0
                        ) AS looted_resources_delta,
                        GREATEST(COALESCE(donations, 0) - COALESCE(LAG(donations) OVER (ORDER BY fetched_at), COALESCE(donations, 0)), 0)
                            AS donations_delta
                    FROM player_snapshots
                    WHERE player_tag = %s
                ),
                changes AS (
                    SELECT
                        fetched_at,
                        rn,
                        (
                            trophies_delta > 0
                            OR war_stars_delta > 0
                            OR looted_resources_delta > 0
                            OR capital_delta > 0
                            OR donations_delta > 0
                        ) AS has_change
                    FROM deltas
                )
                SELECT
                    MAX(fetched_at) FILTER (WHERE has_change) AS last_change_at,
                    MAX(fetched_at) FILTER (WHERE rn = 1 AND has_change) AS last_fetch_change_at
                FROM changes
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

    estimated_last_activity_at = snapshot_activity.get("last_fetch_change_at") or snapshot_activity.get("last_change_at")
    estimated_last_activity_hours = 9999.0
    if isinstance(estimated_last_activity_at, datetime):
        estimated_last_activity_hours = round(
            max((now_utc - estimated_last_activity_at).total_seconds() / 3600.0, 0.0),
            1,
        )

    latest_cap = capital_history[0] if capital_history else {}

    summary = {
        "overall": {
            "attacks_used": _safe_int(war_summary.get("attacks_used")),
            "attack_capacity": _safe_int(war_summary.get("attack_capacity")),
            "missed_attacks": _safe_int(war_summary.get("missed_attacks")),
            "attack_stars": _safe_int(war_summary.get("attack_stars")),
            "avg_attack_destruction": _safe_float(war_summary.get("avg_attack_destruction")),
        },
        "gdc": {
            "attacks_used": _safe_int(war_summary.get("gdc_attacks_used")),
            "attack_capacity": _safe_int(war_summary.get("gdc_attack_capacity")),
            "missed_attacks": _safe_int(war_summary.get("gdc_missed_attacks")),
        },
        "ldc": {
            "attacks_used": _safe_int(war_summary.get("ldc_attacks_used")),
            "attack_capacity": _safe_int(war_summary.get("ldc_attack_capacity")),
            "missed_attacks": _safe_int(war_summary.get("ldc_missed_attacks")),
        },
    }
    summary["clan_games_current_month_delta"] = (
        _safe_int(player_clan_games_monthly[-1].get("monthly_delta")) if player_clan_games_monthly else 0
    )
    summary["clan_games_previous_month_delta"] = (
        _safe_int(player_clan_games_monthly[-2].get("monthly_delta")) if len(player_clan_games_monthly) > 1 else 0
    )

    summary["overall"]["participation_rate"] = _compute_participation_rate(
        summary["overall"]["attacks_used"],
        summary["overall"]["attack_capacity"],
    )
    summary["gdc"]["participation_rate"] = _compute_participation_rate(
        summary["gdc"]["attacks_used"],
        summary["gdc"]["attack_capacity"],
    )
    summary["ldc"]["participation_rate"] = _compute_participation_rate(
        summary["ldc"]["attacks_used"],
        summary["ldc"]["attack_capacity"],
    )

    player_activity_score = _compute_player_activity_score(
        attack_stars=summary["overall"]["attack_stars"],
        donations=_safe_int(player.get("donations")),
        raid_loot=_safe_int(latest_cap.get("capital_resources_looted")),
        jdc=_safe_int(summary["clan_games_current_month_delta"]),
        missed_attacks=summary["overall"]["missed_attacks"],
    )

    war_history_chrono = list(reversed(war_history))
    for row in war_history_chrono:
        row["war_family"] = _war_bucket_key(str(row.get("war_type") or "regular"))

    chart_snapshots = [
        {
            "label": _dt_label(point.get("bucket"), scale_conf["snapshot_bucket"]),
            "bucket": point.get("bucket"),
            "trophies": _safe_int(point.get("trophies")),
            "donations_delta": _safe_int(point.get("donations_delta")),
            "clan_games_delta": _safe_int(point.get("clan_games_points_total_delta")),
            "capital_delta": _safe_int(point.get("clan_capital_contributions_delta")),
        }
        for point in snapshots
    ]

    chart_wars_all = [
        {
            "label": row.get("start_time").astimezone().strftime("%d/%m") if isinstance(row.get("start_time"), datetime) else "-",
            "bucket": row.get("start_time"),
            "used": _safe_int(row.get("attacks_used")),
            "capacity": _safe_int(row.get("attack_capacity")),
            "missed": _safe_int(row.get("missed_attacks")),
            "stars": _safe_int(row.get("total_attack_stars")),
            "war_family": row.get("war_family"),
            "state": row.get("state") or "unknown",
        }
        for row in war_history_chrono
    ]
    chart_wars_gdc = [row for row in chart_wars_all if row["war_family"] == "gdc"]
    chart_wars_ldc = [row for row in chart_wars_all if row["war_family"] == "ldc"]

    capital_history_chrono = list(reversed(capital_history))
    chart_capital = [
        {
            "label": row.get("season_start_time").astimezone().strftime("%d/%m")
            if isinstance(row.get("season_start_time"), datetime)
            else "-",
            "bucket": row.get("season_start_time"),
            "loot": _safe_int(row.get("capital_resources_looted")),
            "attacks": _safe_int(row.get("attacks")),
            "capacity": _safe_int(row.get("attack_limit")) + _safe_int(row.get("bonus_attack_limit")),
        }
        for row in capital_history_chrono
    ]
    chart_clan_games_monthly = [
        {
            "label": row.get("month_bucket").astimezone().strftime("%m/%Y")
            if isinstance(row.get("month_bucket"), datetime)
            else "-",
            "bucket": row.get("month_bucket"),
            "month_total": _safe_int(row.get("month_total")),
            "monthly_delta": _safe_int(row.get("monthly_delta")),
        }
        for row in player_clan_games_monthly
    ]

    return {
        "meta": _meta_payload(scale_key, scale_conf),
        "player": player,
        "summary": {
            **summary,
            "player_health": player_activity_score,
            "freshness_hours": round(freshness_hours, 1),
            "last_activity_at": estimated_last_activity_at,
            "last_activity_hours": estimated_last_activity_hours,
        },
        "histories": {
            "wars": war_history,
            "capital": capital_history,
            "snapshots": snapshots,
        },
        "charts": {
            "snapshots": chart_snapshots,
            "war_history": {
                "overall": chart_wars_all,
                "gdc": chart_wars_gdc,
                "ldc": chart_wars_ldc,
            },
            "capital_history": chart_capital,
            "clan_games_monthly": chart_clan_games_monthly,
        },
    }


@app.get("/")
def root() -> tuple[dict[str, Any], int]:
    return {
        "service": "clash-dashboard-api",
        "status": "ok",
        "endpoints": ["/health", "/api/overview", "/api/player/<player_tag>"],
    }, 200


@app.get("/api/overview")
def api_overview() -> tuple[Any, int]:
    scale_key = _resolve_scale(request.args.get("scale"))
    payload = _load_overview(scale_key)
    return jsonify(_serialize_json(payload)), 200


@app.get("/api/player/<player_tag>")
def api_player(player_tag: str) -> tuple[Any, int]:
    scale_key = _resolve_scale(request.args.get("scale"))
    payload = _load_player_detail(player_tag, scale_key)
    return jsonify(_serialize_json(payload)), 200


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


def main() -> int:
    port = int(os.getenv("PORT", "8121"))
    serve(app, host="0.0.0.0", port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
