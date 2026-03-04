from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import psycopg
from psycopg.types.json import Json

CLAN_GAMES_ACHIEVEMENT_NAME = "games champion"


def connect(db_url: str) -> psycopg.Connection:
    return psycopg.connect(db_url)


def parse_coc_time(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def extract_clan_games_points(player: dict) -> int | None:
    achievements = player.get("achievements") or []
    for achievement in achievements:
        name = str(achievement.get("name") or "").strip().lower()
        if name == CLAN_GAMES_ACHIEVEMENT_NAME:
            try:
                return int(achievement.get("value") or 0)
            except (TypeError, ValueError):
                return None
    return None


def extract_league_tier(player: dict) -> dict:
    # API variants can expose either league or leagueTier.
    league_tier = player.get("leagueTier") or player.get("league") or {}
    return league_tier if isinstance(league_tier, dict) else {}


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _compute_war_outcome(war: dict, clan_tag: str) -> str | None:
    state = str(war.get("state") or "")
    if state != "warEnded":
        return None

    our = war.get("clan") or {}
    opp = war.get("opponent") or {}
    our_tag = our.get("tag")

    if our_tag and clan_tag and our_tag != clan_tag:
        our, opp = opp, our

    our_stars = _safe_int(our.get("stars"), 0)
    opp_stars = _safe_int(opp.get("stars"), 0)
    if our_stars > opp_stars:
        return "win"
    if our_stars < opp_stars:
        return "loss"

    our_destruction = _safe_float(our.get("destructionPercentage"), 0.0)
    opp_destruction = _safe_float(opp.get("destructionPercentage"), 0.0)
    if our_destruction > opp_destruction:
        return "win"
    if our_destruction < opp_destruction:
        return "loss"
    return "draw"


def build_war_id(war: dict, war_type: str, clan_tag: str) -> str:
    war_tag = war.get("warTag")
    if war_tag:
        return str(war_tag)

    start_time = war.get("startTime") or war.get("preparationStartTime") or "na"
    clan = war.get("clan") or {}
    opponent = war.get("opponent") or {}

    our = clan
    opp = opponent
    if clan.get("tag") and clan_tag and clan.get("tag") != clan_tag:
        our = opponent
        opp = clan

    opponent_tag = opp.get("tag") or "unknown"
    our_tag = our.get("tag") or clan_tag or "unknown"
    return f"{war_type}:{our_tag}:{opponent_tag}:{start_time}"


def upsert_clan(conn: psycopg.Connection, clan: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clans (
                tag,
                name,
                description,
                clan_level,
                members,
                clan_points,
                war_wins,
                war_losses,
                war_ties,
                war_win_streak,
                is_war_log_public,
                required_trophies,
                raw_json,
                updated_at
            )
            VALUES (
                %(tag)s,
                %(name)s,
                %(description)s,
                %(clanLevel)s,
                %(members)s,
                %(clanPoints)s,
                %(warWins)s,
                %(warLosses)s,
                %(warTies)s,
                %(warWinStreak)s,
                %(isWarLogPublic)s,
                %(requiredTrophies)s,
                %(raw_json)s,
                NOW()
            )
            ON CONFLICT (tag)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                clan_level = EXCLUDED.clan_level,
                members = EXCLUDED.members,
                clan_points = EXCLUDED.clan_points,
                war_wins = EXCLUDED.war_wins,
                war_losses = EXCLUDED.war_losses,
                war_ties = EXCLUDED.war_ties,
                war_win_streak = EXCLUDED.war_win_streak,
                is_war_log_public = EXCLUDED.is_war_log_public,
                required_trophies = EXCLUDED.required_trophies,
                raw_json = EXCLUDED.raw_json,
                updated_at = NOW()
            """,
            {
                "tag": clan.get("tag"),
                "name": clan.get("name"),
                "description": clan.get("description"),
                "clanLevel": clan.get("clanLevel"),
                "members": clan.get("members"),
                "clanPoints": clan.get("clanPoints"),
                "warWins": clan.get("warWins"),
                "warLosses": clan.get("warLosses"),
                "warTies": clan.get("warTies"),
                "warWinStreak": clan.get("warWinStreak"),
                "isWarLogPublic": clan.get("isWarLogPublic"),
                "requiredTrophies": clan.get("requiredTrophies"),
                "raw_json": Json(clan),
            },
        )


def insert_clan_snapshot(conn: psycopg.Connection, clan: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clan_snapshots (
                clan_tag,
                members,
                clan_points,
                war_wins,
                war_losses,
                war_ties,
                raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clan.get("tag"),
                clan.get("members"),
                clan.get("clanPoints"),
                clan.get("warWins"),
                clan.get("warLosses"),
                clan.get("warTies"),
                Json(clan),
            ),
        )


def upsert_player(conn: psycopg.Connection, player: dict) -> None:
    clan = player.get("clan") or {}
    league_tier = extract_league_tier(player)
    builder_base_league = player.get("builderBaseLeague") or {}
    clan_games_points_total = extract_clan_games_points(player)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO players (
                tag,
                name,
                clan_tag,
                role,
                exp_level,
                town_hall_level,
                town_hall_weapon_level,
                builder_hall_level,
                trophies,
                best_trophies,
                builder_base_trophies,
                best_builder_base_trophies,
                war_stars,
                attack_wins,
                defense_wins,
                donations,
                donations_received,
                clan_capital_contributions,
                league_tier_id,
                league_tier_name,
                builder_base_league_id,
                builder_base_league_name,
                current_league_group_tag,
                current_league_season_id,
                previous_league_group_tag,
                previous_league_season_id,
                clan_games_points_total,
                raw_json,
                updated_at
            )
            VALUES (
                %(tag)s,
                %(name)s,
                %(clan_tag)s,
                %(role)s,
                %(expLevel)s,
                %(townHallLevel)s,
                %(townHallWeaponLevel)s,
                %(builderHallLevel)s,
                %(trophies)s,
                %(bestTrophies)s,
                %(builderBaseTrophies)s,
                %(bestBuilderBaseTrophies)s,
                %(warStars)s,
                %(attackWins)s,
                %(defenseWins)s,
                %(donations)s,
                %(donationsReceived)s,
                %(clanCapitalContributions)s,
                %(league_tier_id)s,
                %(league_tier_name)s,
                %(builder_base_league_id)s,
                %(builder_base_league_name)s,
                %(currentLeagueGroupTag)s,
                %(currentLeagueSeasonId)s,
                %(previousLeagueGroupTag)s,
                %(previousLeagueSeasonId)s,
                %(clan_games_points_total)s,
                %(raw_json)s,
                NOW()
            )
            ON CONFLICT (tag)
            DO UPDATE SET
                name = EXCLUDED.name,
                clan_tag = EXCLUDED.clan_tag,
                role = EXCLUDED.role,
                exp_level = EXCLUDED.exp_level,
                town_hall_level = EXCLUDED.town_hall_level,
                town_hall_weapon_level = EXCLUDED.town_hall_weapon_level,
                builder_hall_level = EXCLUDED.builder_hall_level,
                trophies = EXCLUDED.trophies,
                best_trophies = EXCLUDED.best_trophies,
                builder_base_trophies = EXCLUDED.builder_base_trophies,
                best_builder_base_trophies = EXCLUDED.best_builder_base_trophies,
                war_stars = EXCLUDED.war_stars,
                attack_wins = EXCLUDED.attack_wins,
                defense_wins = EXCLUDED.defense_wins,
                donations = EXCLUDED.donations,
                donations_received = EXCLUDED.donations_received,
                clan_capital_contributions = EXCLUDED.clan_capital_contributions,
                league_tier_id = EXCLUDED.league_tier_id,
                league_tier_name = EXCLUDED.league_tier_name,
                builder_base_league_id = EXCLUDED.builder_base_league_id,
                builder_base_league_name = EXCLUDED.builder_base_league_name,
                current_league_group_tag = EXCLUDED.current_league_group_tag,
                current_league_season_id = EXCLUDED.current_league_season_id,
                previous_league_group_tag = EXCLUDED.previous_league_group_tag,
                previous_league_season_id = EXCLUDED.previous_league_season_id,
                clan_games_points_total = EXCLUDED.clan_games_points_total,
                raw_json = EXCLUDED.raw_json,
                updated_at = NOW()
            """,
            {
                "tag": player.get("tag"),
                "name": player.get("name"),
                "clan_tag": clan.get("tag"),
                "role": player.get("role"),
                "expLevel": player.get("expLevel"),
                "townHallLevel": player.get("townHallLevel"),
                "townHallWeaponLevel": player.get("townHallWeaponLevel"),
                "builderHallLevel": player.get("builderHallLevel"),
                "trophies": player.get("trophies"),
                "bestTrophies": player.get("bestTrophies"),
                "builderBaseTrophies": player.get("builderBaseTrophies"),
                "bestBuilderBaseTrophies": player.get("bestBuilderBaseTrophies"),
                "warStars": player.get("warStars"),
                "attackWins": player.get("attackWins"),
                "defenseWins": player.get("defenseWins"),
                "donations": player.get("donations"),
                "donationsReceived": player.get("donationsReceived"),
                "clanCapitalContributions": player.get("clanCapitalContributions"),
                "league_tier_id": league_tier.get("id"),
                "league_tier_name": league_tier.get("name"),
                "builder_base_league_id": builder_base_league.get("id"),
                "builder_base_league_name": builder_base_league.get("name"),
                "currentLeagueGroupTag": player.get("currentLeagueGroupTag"),
                "currentLeagueSeasonId": player.get("currentLeagueSeasonId"),
                "previousLeagueGroupTag": player.get("previousLeagueGroupTag"),
                "previousLeagueSeasonId": player.get("previousLeagueSeasonId"),
                "clan_games_points_total": clan_games_points_total,
                "raw_json": Json(player),
            },
        )


def insert_player_snapshot(conn: psycopg.Connection, player: dict) -> None:
    clan = player.get("clan") or {}
    league_tier = extract_league_tier(player)
    builder_base_league = player.get("builderBaseLeague") or {}
    clan_games_points_total = extract_clan_games_points(player)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO player_snapshots (
                player_tag,
                clan_tag,
                trophies,
                town_hall_level,
                war_stars,
                donations,
                donations_received,
                clan_capital_contributions,
                league_tier_name,
                builder_base_league_name,
                clan_games_points_total,
                raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                player.get("tag"),
                clan.get("tag"),
                player.get("trophies"),
                player.get("townHallLevel"),
                player.get("warStars"),
                player.get("donations"),
                player.get("donationsReceived"),
                player.get("clanCapitalContributions"),
                league_tier.get("name"),
                builder_base_league.get("name"),
                clan_games_points_total,
                Json(player),
            ),
        )


def sync_memberships(conn: psycopg.Connection, clan_tag: str, member_tags: Iterable[str]) -> None:
    tags = sorted(set(member_tags))

    with conn.cursor() as cur:
        for player_tag in tags:
            cur.execute(
                """
                INSERT INTO clan_memberships (clan_tag, player_tag, first_seen_at, last_seen_at, is_active)
                VALUES (%s, %s, NOW(), NOW(), TRUE)
                ON CONFLICT (clan_tag, player_tag)
                DO UPDATE SET
                    last_seen_at = NOW(),
                    is_active = TRUE
                """,
                (clan_tag, player_tag),
            )

        if not tags:
            cur.execute(
                """
                UPDATE clan_memberships
                SET is_active = FALSE
                WHERE clan_tag = %s AND is_active = TRUE
                """,
                (clan_tag,),
            )
        else:
            cur.execute(
                """
                UPDATE clan_memberships
                SET is_active = FALSE
                WHERE clan_tag = %s
                  AND is_active = TRUE
                  AND NOT (player_tag = ANY(%s))
                """,
                (clan_tag, tags),
            )


def get_finalized_war_ids(conn: psycopg.Connection, war_ids: Iterable[str]) -> set[str]:
    ids = sorted({wid for wid in war_ids if wid})
    if not ids:
        return set()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT war_id
            FROM clan_wars
            WHERE war_id = ANY(%s)
              AND state = 'warEnded'
            """,
            (ids,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def upsert_war(
    conn: psycopg.Connection,
    war: dict,
    *,
    war_type: str,
    clan_tag: str,
    league_group_season: str | None = None,
    league_group_state: str | None = None,
) -> str:
    war_id = build_war_id(war, war_type=war_type, clan_tag=clan_tag)
    war_tag = war.get("warTag")

    clan = war.get("clan") or {}
    opponent = war.get("opponent") or {}
    if clan.get("tag") and clan_tag and clan.get("tag") != clan_tag:
        clan, opponent = opponent, clan

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clan_wars (
                war_id,
                war_tag,
                war_type,
                league_group_season,
                league_group_state,
                state,
                team_size,
                attacks_per_member,
                battle_modifier,
                preparation_start_time,
                start_time,
                end_time,
                clan_tag,
                clan_name,
                clan_stars,
                clan_destruction_percentage,
                clan_attacks,
                opponent_tag,
                opponent_name,
                opponent_stars,
                opponent_destruction_percentage,
                opponent_attacks,
                outcome,
                raw_json,
                fetched_at,
                updated_at
            )
            VALUES (
                %(war_id)s,
                %(war_tag)s,
                %(war_type)s,
                %(league_group_season)s,
                %(league_group_state)s,
                %(state)s,
                %(team_size)s,
                %(attacks_per_member)s,
                %(battle_modifier)s,
                %(preparation_start_time)s,
                %(start_time)s,
                %(end_time)s,
                %(clan_tag)s,
                %(clan_name)s,
                %(clan_stars)s,
                %(clan_destruction_percentage)s,
                %(clan_attacks)s,
                %(opponent_tag)s,
                %(opponent_name)s,
                %(opponent_stars)s,
                %(opponent_destruction_percentage)s,
                %(opponent_attacks)s,
                %(outcome)s,
                %(raw_json)s,
                NOW(),
                NOW()
            )
            ON CONFLICT (war_id)
            DO UPDATE SET
                war_tag = EXCLUDED.war_tag,
                war_type = EXCLUDED.war_type,
                league_group_season = EXCLUDED.league_group_season,
                league_group_state = EXCLUDED.league_group_state,
                state = EXCLUDED.state,
                team_size = EXCLUDED.team_size,
                attacks_per_member = EXCLUDED.attacks_per_member,
                battle_modifier = EXCLUDED.battle_modifier,
                preparation_start_time = EXCLUDED.preparation_start_time,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                clan_tag = EXCLUDED.clan_tag,
                clan_name = EXCLUDED.clan_name,
                clan_stars = EXCLUDED.clan_stars,
                clan_destruction_percentage = EXCLUDED.clan_destruction_percentage,
                clan_attacks = EXCLUDED.clan_attacks,
                opponent_tag = EXCLUDED.opponent_tag,
                opponent_name = EXCLUDED.opponent_name,
                opponent_stars = EXCLUDED.opponent_stars,
                opponent_destruction_percentage = EXCLUDED.opponent_destruction_percentage,
                opponent_attacks = EXCLUDED.opponent_attacks,
                outcome = EXCLUDED.outcome,
                raw_json = EXCLUDED.raw_json,
                fetched_at = NOW(),
                updated_at = NOW()
            """,
            {
                "war_id": war_id,
                "war_tag": war_tag,
                "war_type": war_type,
                "league_group_season": league_group_season,
                "league_group_state": league_group_state,
                "state": war.get("state"),
                "team_size": war.get("teamSize"),
                "attacks_per_member": war.get("attacksPerMember"),
                "battle_modifier": war.get("battleModifier"),
                "preparation_start_time": parse_coc_time(war.get("preparationStartTime")),
                "start_time": parse_coc_time(war.get("startTime") or war.get("warStartTime")),
                "end_time": parse_coc_time(war.get("endTime")),
                "clan_tag": clan.get("tag") or clan_tag,
                "clan_name": clan.get("name"),
                "clan_stars": clan.get("stars"),
                "clan_destruction_percentage": clan.get("destructionPercentage"),
                "clan_attacks": clan.get("attacks"),
                "opponent_tag": opponent.get("tag"),
                "opponent_name": opponent.get("name"),
                "opponent_stars": opponent.get("stars"),
                "opponent_destruction_percentage": opponent.get("destructionPercentage"),
                "opponent_attacks": opponent.get("attacks"),
                "outcome": _compute_war_outcome(war, clan_tag),
                "raw_json": Json(war),
            },
        )

    return war_id


def upsert_war_members(conn: psycopg.Connection, war_id: str, war: dict, clan_tag: str) -> None:
    team_size = _safe_int(war.get("teamSize"), 0)
    attacks_per_member = _safe_int(war.get("attacksPerMember"), 2)
    attack_capacity = attacks_per_member if attacks_per_member > 0 else 2
    war_ended = str(war.get("state") or "") == "warEnded"

    with conn.cursor() as cur:
        cur.execute("DELETE FROM war_member_performances WHERE war_id = %s", (war_id,))

        for side_key in ("clan", "opponent"):
            side = war.get(side_key) or {}
            side_tag = side.get("tag") or "UNKNOWN"
            is_our_clan = side_tag == clan_tag
            members = side.get("members") or []

            for member in members:
                attacks = member.get("attacks") or []
                attacks_used = len(attacks)
                total_attack_stars = sum(_safe_int(attack.get("stars")) for attack in attacks)
                total_attack_destruction = sum(
                    _safe_float(attack.get("destructionPercentage")) for attack in attacks
                )
                best_opp = member.get("bestOpponentAttack") or {}

                cur.execute(
                    """
                    INSERT INTO war_member_performances (
                        war_id,
                        clan_tag,
                        player_tag,
                        player_name,
                        town_hall_level,
                        map_position,
                        attacks_used,
                        attack_capacity,
                        total_attack_stars,
                        total_attack_destruction,
                        opponent_attacks,
                        best_opponent_stars,
                        best_opponent_destruction,
                        missed_attacks,
                        is_our_clan,
                        raw_json,
                        updated_at
                    )
                    VALUES (
                        %(war_id)s,
                        %(clan_tag)s,
                        %(player_tag)s,
                        %(player_name)s,
                        %(town_hall_level)s,
                        %(map_position)s,
                        %(attacks_used)s,
                        %(attack_capacity)s,
                        %(total_attack_stars)s,
                        %(total_attack_destruction)s,
                        %(opponent_attacks)s,
                        %(best_opponent_stars)s,
                        %(best_opponent_destruction)s,
                        %(missed_attacks)s,
                        %(is_our_clan)s,
                        %(raw_json)s,
                        NOW()
                    )
                    ON CONFLICT (war_id, clan_tag, player_tag)
                    DO UPDATE SET
                        player_name = EXCLUDED.player_name,
                        town_hall_level = EXCLUDED.town_hall_level,
                        map_position = EXCLUDED.map_position,
                        attacks_used = EXCLUDED.attacks_used,
                        attack_capacity = EXCLUDED.attack_capacity,
                        total_attack_stars = EXCLUDED.total_attack_stars,
                        total_attack_destruction = EXCLUDED.total_attack_destruction,
                        opponent_attacks = EXCLUDED.opponent_attacks,
                        best_opponent_stars = EXCLUDED.best_opponent_stars,
                        best_opponent_destruction = EXCLUDED.best_opponent_destruction,
                        missed_attacks = EXCLUDED.missed_attacks,
                        is_our_clan = EXCLUDED.is_our_clan,
                        raw_json = EXCLUDED.raw_json,
                        updated_at = NOW()
                    """,
                    {
                        "war_id": war_id,
                        "clan_tag": side_tag,
                        "player_tag": member.get("tag"),
                        "player_name": member.get("name"),
                        "town_hall_level": member.get("townhallLevel"),
                        "map_position": member.get("mapPosition"),
                        "attacks_used": attacks_used,
                        "attack_capacity": attack_capacity,
                        "total_attack_stars": total_attack_stars,
                        "total_attack_destruction": total_attack_destruction,
                        "opponent_attacks": member.get("opponentAttacks"),
                        "best_opponent_stars": best_opp.get("stars"),
                        "best_opponent_destruction": best_opp.get("destructionPercentage"),
                        "missed_attacks": max(attack_capacity - attacks_used, 0) if war_ended else 0,
                        "is_our_clan": is_our_clan,
                        "raw_json": Json(member),
                    },
                )

    # When no members are present (for preparation / notInWar), we still keep prior rows deleted.
    if team_size <= 0:
        return


def upsert_war_attacks(conn: psycopg.Connection, war_id: str, war: dict, clan_tag: str) -> None:
    clan = war.get("clan") or {}
    opponent = war.get("opponent") or {}

    member_to_clan: dict[str, str] = {}
    for side_key, side in (("clan", clan), ("opponent", opponent)):
        side_tag = side.get("tag")
        if not side_tag:
            continue
        for member in side.get("members") or []:
            tag = member.get("tag")
            if tag:
                member_to_clan[str(tag)] = side_tag

    with conn.cursor() as cur:
        cur.execute("DELETE FROM war_attacks WHERE war_id = %s", (war_id,))

        for side in (clan, opponent):
            for member in side.get("members") or []:
                for idx, attack in enumerate(member.get("attacks") or [], start=1):
                    attacker_tag = attack.get("attackerTag")
                    defender_tag = attack.get("defenderTag")
                    attacker_clan_tag = member_to_clan.get(str(attacker_tag))
                    defender_clan_tag = member_to_clan.get(str(defender_tag))
                    attack_order = _safe_int(attack.get("order"), idx)

                    cur.execute(
                        """
                        INSERT INTO war_attacks (
                            war_id,
                            attack_order,
                            attacker_tag,
                            defender_tag,
                            attacker_clan_tag,
                            defender_clan_tag,
                            stars,
                            destruction_percentage,
                            duration_seconds,
                            is_our_clan,
                            raw_json
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (war_id, attacker_tag, defender_tag, attack_order)
                        DO UPDATE SET
                            attacker_clan_tag = EXCLUDED.attacker_clan_tag,
                            defender_clan_tag = EXCLUDED.defender_clan_tag,
                            stars = EXCLUDED.stars,
                            destruction_percentage = EXCLUDED.destruction_percentage,
                            duration_seconds = EXCLUDED.duration_seconds,
                            is_our_clan = EXCLUDED.is_our_clan,
                            raw_json = EXCLUDED.raw_json
                        """,
                        (
                            war_id,
                            attack_order,
                            attacker_tag,
                            defender_tag,
                            attacker_clan_tag,
                            defender_clan_tag,
                            attack.get("stars"),
                            attack.get("destructionPercentage"),
                            attack.get("duration"),
                            attacker_clan_tag == clan_tag,
                            Json(attack),
                        ),
                    )


def upsert_cwl_group(conn: psycopg.Connection, clan_tag: str, group: dict) -> str:
    season = group.get("season") or "unknown"
    group_id = f"{clan_tag}:{season}"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cwl_groups (
                group_id,
                clan_tag,
                season,
                state,
                raw_json,
                fetched_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (group_id)
            DO UPDATE SET
                state = EXCLUDED.state,
                raw_json = EXCLUDED.raw_json,
                fetched_at = NOW(),
                updated_at = NOW()
            """,
            (
                group_id,
                clan_tag,
                season,
                group.get("state"),
                Json(group),
            ),
        )

        clans = group.get("clans") or []
        for clan in clans:
            clan_members = clan.get("members") or []
            cur.execute(
                """
                INSERT INTO cwl_group_clans (
                    group_id,
                    clan_tag,
                    name,
                    clan_level,
                    member_count,
                    raw_json,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (group_id, clan_tag)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    clan_level = EXCLUDED.clan_level,
                    member_count = EXCLUDED.member_count,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    group_id,
                    clan.get("tag"),
                    clan.get("name"),
                    clan.get("clanLevel"),
                    len(clan_members),
                    Json(clan),
                ),
            )

            cur.execute(
                "DELETE FROM cwl_group_members WHERE group_id = %s AND clan_tag = %s",
                (group_id, clan.get("tag")),
            )

            for member in clan_members:
                cur.execute(
                    """
                    INSERT INTO cwl_group_members (
                        group_id,
                        clan_tag,
                        player_tag,
                        player_name,
                        town_hall_level,
                        raw_json,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (group_id, clan_tag, player_tag)
                    DO UPDATE SET
                        player_name = EXCLUDED.player_name,
                        town_hall_level = EXCLUDED.town_hall_level,
                        raw_json = EXCLUDED.raw_json,
                        updated_at = NOW()
                    """,
                    (
                        group_id,
                        clan.get("tag"),
                        member.get("tag"),
                        member.get("name"),
                        member.get("townHallLevel"),
                        Json(member),
                    ),
                )

    return group_id


def upsert_capital_raid_seasons(conn: psycopg.Connection, clan_tag: str, payload: dict | None) -> int:
    if not payload:
        return 0

    seasons = payload.get("items") or []
    stored = 0

    with conn.cursor() as cur:
        for season in seasons:
            season_start_time = parse_coc_time(season.get("startTime"))
            if not season_start_time:
                continue

            cur.execute(
                """
                INSERT INTO capital_raid_seasons (
                    clan_tag,
                    season_start_time,
                    season_end_time,
                    state,
                    capital_total_loot,
                    raids_completed,
                    total_attacks,
                    enemy_districts_destroyed,
                    offensive_reward,
                    defensive_reward,
                    raw_json,
                    fetched_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (clan_tag, season_start_time)
                DO UPDATE SET
                    season_end_time = EXCLUDED.season_end_time,
                    state = EXCLUDED.state,
                    capital_total_loot = EXCLUDED.capital_total_loot,
                    raids_completed = EXCLUDED.raids_completed,
                    total_attacks = EXCLUDED.total_attacks,
                    enemy_districts_destroyed = EXCLUDED.enemy_districts_destroyed,
                    offensive_reward = EXCLUDED.offensive_reward,
                    defensive_reward = EXCLUDED.defensive_reward,
                    raw_json = EXCLUDED.raw_json,
                    fetched_at = NOW(),
                    updated_at = NOW()
                """,
                (
                    clan_tag,
                    season_start_time,
                    parse_coc_time(season.get("endTime")),
                    season.get("state"),
                    season.get("capitalTotalLoot"),
                    season.get("raidsCompleted"),
                    season.get("totalAttacks"),
                    season.get("enemyDistrictsDestroyed"),
                    season.get("offensiveReward"),
                    season.get("defensiveReward"),
                    Json(season),
                ),
            )

            cur.execute(
                """
                DELETE FROM capital_raid_member_stats
                WHERE clan_tag = %s
                  AND season_start_time = %s
                """,
                (clan_tag, season_start_time),
            )

            for member in season.get("members") or []:
                cur.execute(
                    """
                    INSERT INTO capital_raid_member_stats (
                        clan_tag,
                        season_start_time,
                        player_tag,
                        player_name,
                        attacks,
                        attack_limit,
                        bonus_attack_limit,
                        capital_resources_looted,
                        raw_json,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (clan_tag, season_start_time, player_tag)
                    DO UPDATE SET
                        player_name = EXCLUDED.player_name,
                        attacks = EXCLUDED.attacks,
                        attack_limit = EXCLUDED.attack_limit,
                        bonus_attack_limit = EXCLUDED.bonus_attack_limit,
                        capital_resources_looted = EXCLUDED.capital_resources_looted,
                        raw_json = EXCLUDED.raw_json,
                        updated_at = NOW()
                    """,
                    (
                        clan_tag,
                        season_start_time,
                        member.get("tag"),
                        member.get("name"),
                        member.get("attacks"),
                        member.get("attackLimit"),
                        member.get("bonusAttackLimit"),
                        member.get("capitalResourcesLooted"),
                        Json(member),
                    ),
                )

            stored += 1

    return stored
