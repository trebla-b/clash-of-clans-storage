# Clash of Clans Storage (Clan + Joueurs)

Stack Docker avec:
- `db`: PostgreSQL
- `cron`: job périodique qui fetch l'API Clash of Clans et stocke clan/joueurs/guerres/capitale
- `dashboard`: interface web **liquid design** pour piloter la santé globale du clan et le détail joueur

Le schéma SQL est défini dans `db/init.sql`.

## Configuration

1. Copier `.env.example` vers `.env` puis renseigner `API_KEY`.
2. Adapter `config/config.yml`:
   - `clan_id` (obligatoire, aucune valeur par défaut)
   - `fetch_cron` (par défaut: `0 * * * *`, soit 1 fois par heure)
   - `db_url` (par défaut vers la DB Docker)

Exemple:
- Clan: `#2PVYQ00R` (Team Barbare)

## Lancement

```bash
docker compose up --build -d
```

## Logs

```bash
docker compose logs -f cron
docker compose logs -f dashboard
```

## Dashboard

- URL: `http://localhost:8120`
- Design: liquid UI (desktop + mobile)
- Echelles d'analyse: `7d`, `30d`, `90d`, `365d`, `all`
- Drill-down joueur: clic sur un joueur depuis la table principale

## Important: comment on a de l'historique si l'API est temps réel

L'API Clash of Clans expose surtout l'état courant.
L'historique est reconstruit par le `cron` qui prend des snapshots réguliers en DB (`clan_snapshots`, `player_snapshots`, `clan_wars`, `capital_raid_seasons`, etc.).
Toutes les stats multi-périodes du dashboard sont calculées **uniquement depuis la DB**.

## Données stockées pour le pilotage de clan

- `Dons`: `players.donations`, `players.donations_received` + historique `player_snapshots`
- `GDC / CWL`:
  - guerres: `clan_wars`
  - perf membres: `war_member_performances`
  - détails attaques: `war_attacks`
  - groupe CWL + roster: `cwl_groups`, `cwl_group_clans`, `cwl_group_members`
- `Ligue joueur`: `players.league_tier_name`, `players.builder_base_league_name`
- `Jeux de clans (cumulé)`: `players.clan_games_points_total` (achievement `Games Champion`)
- `Capitale`:
  - weekends: `capital_raid_seasons`
  - perf joueurs weekend: `capital_raid_member_stats`
  - cumul joueur global: `players.clan_capital_contributions`

## Vues utiles

- `v_current_clan_members`
- `v_war_participation_30d`
- `v_latest_capital_raid_member_stats`

## Notes migration

Si ta DB existait déjà avec l'ancien schéma, recrée le volume pour rejouer le SQL complet:

```bash
docker compose down -v
docker compose up --build -d
```
