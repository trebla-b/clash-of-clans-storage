from __future__ import annotations

from urllib.parse import quote

import requests


class ClashOfClansClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def encode_tag(tag: str) -> str:
        return quote(tag.strip(), safe="")

    def _get(self, path: str, allow_not_found: bool = False) -> dict | None:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.ok:
            return response.json()
        if allow_not_found and response.status_code == 404:
            return None

        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text}

        raise RuntimeError(
            f"API error on {path}: status={response.status_code}, payload={payload}"
        )

    def get_clan(self, clan_tag: str) -> dict:
        encoded = self.encode_tag(clan_tag)
        return self._get(f"/clans/{encoded}")

    def get_player(self, player_tag: str) -> dict:
        encoded = self.encode_tag(player_tag)
        return self._get(f"/players/{encoded}")

    def get_current_war(self, clan_tag: str) -> dict | None:
        encoded = self.encode_tag(clan_tag)
        return self._get(f"/clans/{encoded}/currentwar", allow_not_found=True)

    def get_current_league_group(self, clan_tag: str) -> dict | None:
        encoded = self.encode_tag(clan_tag)
        return self._get(f"/clans/{encoded}/currentwar/leaguegroup", allow_not_found=True)

    def get_cwl_war(self, war_tag: str) -> dict | None:
        encoded = self.encode_tag(war_tag)
        return self._get(f"/clanwarleagues/wars/{encoded}", allow_not_found=True)

    def get_capital_raid_seasons(self, clan_tag: str, limit: int = 5) -> dict | None:
        encoded = self.encode_tag(clan_tag)
        return self._get(
            f"/clans/{encoded}/capitalraidseasons?limit={int(limit)}",
            allow_not_found=True,
        )
