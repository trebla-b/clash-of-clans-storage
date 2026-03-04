from __future__ import annotations

import os
import sys
from typing import Iterable

from app.coc_client import ClashOfClansClient
from app.config import load_config
from app import storage


def _extract_member_tags(clan_payload: dict) -> list[str]:
    members = clan_payload.get("memberList") or []
    tags: list[str] = []
    for member in members:
        tag = member.get("tag")
        if tag:
            tags.append(tag)
    return tags


def _build_player_fetch_list(member_tags: Iterable[str]) -> list[str]:
    return sorted({tag for tag in member_tags if tag})


def _extract_cwl_war_tags(group_payload: dict | None) -> list[str]:
    if not group_payload:
        return []

    tags: set[str] = set()
    for round_payload in group_payload.get("rounds") or []:
        for war_tag in round_payload.get("warTags") or []:
            if war_tag and war_tag != "#0":
                tags.add(str(war_tag))
    return sorted(tags)


def _safe_fetch(name: str, fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to fetch {name}: {exc}", file=sys.stderr)
        return None


def main() -> int:
    config = load_config()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY environment variable")

    client = ClashOfClansClient(
        base_url=config.api_base_url,
        api_key=api_key,
        timeout_seconds=config.request_timeout_seconds,
    )

    clan = client.get_clan(config.clan_id)
    clan_tag = str(clan.get("tag") or config.clan_id)

    member_tags = _extract_member_tags(clan)
    player_tags = _build_player_fetch_list(member_tags)

    players_payload: list[dict] = []
    for player_tag in player_tags:
        player = _safe_fetch(f"player {player_tag}", lambda t=player_tag: client.get_player(t))
        if player:
            players_payload.append(player)

    current_war = _safe_fetch("current war", lambda: client.get_current_war(clan_tag))
    cwl_group = _safe_fetch("current league group", lambda: client.get_current_league_group(clan_tag))
    capital_raid_payload = _safe_fetch(
        "capital raid seasons",
        lambda: client.get_capital_raid_seasons(clan_tag, limit=6),
    )

    cwl_war_tags = _extract_cwl_war_tags(cwl_group)
    finalized_cwl_war_ids: set[str] = set()
    if cwl_war_tags:
        try:
            with storage.connect(config.db_url) as conn:
                finalized_cwl_war_ids = storage.get_finalized_war_ids(conn, cwl_war_tags)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to read finalized CWL wars: {exc}", file=sys.stderr)

    cwl_wars: list[dict] = []
    for war_tag in cwl_war_tags:
        if war_tag in finalized_cwl_war_ids:
            continue
        war = _safe_fetch(f"CWL war {war_tag}", lambda t=war_tag: client.get_cwl_war(t))
        if war:
            war["warTag"] = war_tag
            cwl_wars.append(war)

    current_war_id = None
    cwl_group_id = None
    cwl_wars_stored = 0
    capital_raid_seasons_stored = 0

    with storage.connect(config.db_url) as conn:
        with conn.transaction():
            storage.upsert_clan(conn, clan)
            storage.insert_clan_snapshot(conn, clan)

            for player in players_payload:
                storage.upsert_player(conn, player)
                storage.insert_player_snapshot(conn, player)

            storage.sync_memberships(conn, clan_tag, member_tags)

            if current_war:
                current_war_id = storage.upsert_war(
                    conn,
                    current_war,
                    war_type="regular",
                    clan_tag=clan_tag,
                )
                storage.upsert_war_members(
                    conn,
                    current_war_id,
                    current_war,
                    clan_tag=clan_tag,
                    war_type="regular",
                )
                storage.upsert_war_attacks(conn, current_war_id, current_war, clan_tag=clan_tag)

            if cwl_group:
                cwl_group_id = storage.upsert_cwl_group(conn, clan_tag, cwl_group)
                season = cwl_group.get("season")
                state = cwl_group.get("state")
                for cwl_war in cwl_wars:
                    war_id = storage.upsert_war(
                        conn,
                        cwl_war,
                        war_type="cwl",
                        clan_tag=clan_tag,
                        league_group_season=season,
                        league_group_state=state,
                    )
                    storage.upsert_war_members(
                        conn,
                        war_id,
                        cwl_war,
                        clan_tag=clan_tag,
                        war_type="cwl",
                    )
                    storage.upsert_war_attacks(conn, war_id, cwl_war, clan_tag=clan_tag)
                    cwl_wars_stored += 1

            capital_raid_seasons_stored = storage.upsert_capital_raid_seasons(
                conn,
                clan_tag=clan_tag,
                payload=capital_raid_payload,
            )

    print(
        (
            "[ok] stored clan=%s members=%d players=%d current_war=%s "
            "cwl_group=%s cwl_wars=%d cwl_wars_skipped=%d capital_raid_seasons=%d"
        )
        % (
            clan_tag,
            len(member_tags),
            len(players_payload),
            current_war_id or "none",
            cwl_group_id or "none",
            cwl_wars_stored,
            len(finalized_cwl_war_ids),
            capital_raid_seasons_stored,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        raise
