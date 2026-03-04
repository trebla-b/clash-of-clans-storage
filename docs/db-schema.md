# Schéma DB - Clash Clan Analytics

Ce document décrit la structure de la base PostgreSQL utilisée par `cron` pour historiser l'API Clash of Clans et par `dashboard-api` pour calculer les stats.

## Vue d'ensemble

- `clans`: état courant du clan.
- `players`: état courant des joueurs connus.
- `clan_snapshots` et `player_snapshots`: historique temporel (source de toutes les vues 7d/30d/90d/365d/all).
- `clan_wars`, `war_member_performances`, `war_attacks`: historique guerres + participation.
- `cwl_groups`, `cwl_group_clans`, `cwl_group_members`: structure et roster LDC (CWL).
- `capital_raid_seasons`, `capital_raid_member_stats`: stats capitale de clan (weekend raid).
- `clan_memberships`: historique d'appartenance au clan (actif/inactif).

## Relations clés

- `clan_snapshots.clan_tag -> clans.tag`
- `players.clan_tag -> clans.tag`
- `player_snapshots.player_tag -> players.tag`
- `clan_memberships.(clan_tag, player_tag) -> clans/players`
- `war_member_performances.war_id -> clan_wars.war_id`
- `war_attacks.war_id -> clan_wars.war_id`
- `capital_raid_member_stats.(clan_tag, season_start_time) -> capital_raid_seasons.(clan_tag, season_start_time)`
- `cwl_group_clans.group_id -> cwl_groups.group_id`
- `cwl_group_members.group_id -> cwl_groups.group_id`

## Tables détaillées

## 1) Référentiel courant

### `clans`
- PK: `tag`
- Colonnes métier: `name`, `clan_level`, `members`, `clan_points`, `war_wins`, `war_losses`, `war_ties`
- Technique: `raw_json`, `updated_at`

### `players`
- PK: `tag`
- FK: `clan_tag` (nullable)
- Colonnes métier: rôle, TH, trophées, dons, ligue, capitale, `clan_games_points_total`
- Technique: `raw_json`, `updated_at`

### `clan_memberships`
- PK: `(clan_tag, player_tag)`
- Colonnes métier: `first_seen_at`, `last_seen_at`, `is_active`
- Sert à conserver l'historique quand un joueur quitte/revient.

## 2) Historique snapshots

### `clan_snapshots`
- PK: `snapshot_id`
- FK: `clan_tag`
- Timestamp: `fetched_at`
- Mesures: `members`, `clan_points`, `war_wins/losses/ties`

### `player_snapshots`
- PK: `snapshot_id`
- FK: `player_tag`
- Timestamp: `fetched_at`
- Mesures: `trophies`, `donations`, `donations_received`, `clan_games_points_total`, `clan_capital_contributions`

## 3) Guerres (GDC + LDC)

### `clan_wars`
- PK: `war_id`
- Mesures globales guerre: état, tailles, étoiles, destruction, outcome
- Distinction type guerre: `war_type`
  - `regular` = GDC
  - `cwl` = LDC

### `war_member_performances`
- PK: `(war_id, clan_tag, player_tag)`
- Mesures joueur: `attacks_used`, `attack_capacity`, `missed_attacks`, `total_attack_stars`, `total_attack_destruction`
- Règle métier: `missed_attacks` n'est compté que si la guerre est terminée (`warEnded`), sinon `0`.
- Règle LDC: en guerre `war_type='cwl'`, la capacité d'attaque effective est `1`.

### `war_attacks`
- PK: `(war_id, attacker_tag, defender_tag, attack_order)`
- Détail attaque: étoiles, destruction, durée, sens (notre clan ou non)

## 4) LDC (CWL) structure

### `cwl_groups`
- PK: `group_id` (`<clan_tag>:<season>`)
- Métadonnées saison: `season`, `state`

### `cwl_group_clans`
- PK: `(group_id, clan_tag)`
- Infos clans présents dans le groupe

### `cwl_group_members`
- PK: `(group_id, clan_tag, player_tag)`
- Roster des joueurs déclarés pour le groupe

## 5) Capitale de clan

### `capital_raid_seasons`
- PK: `(clan_tag, season_start_time)`
- Mesures weekend: loot total, attaques totales, districts détruits, rewards

### `capital_raid_member_stats`
- PK: `(clan_tag, season_start_time, player_tag)`
- Mesures joueur weekend: `attacks`, `attack_limit`, `bonus_attack_limit`, `capital_resources_looted`

## Vues SQL fournies

- `v_current_clan_members`: membres actifs + infos utiles pilotage.
- `v_war_participation_30d`: agrégat 30 jours de participation guerre.
- `v_latest_capital_raid_member_stats`: dernier weekend capitale par joueur.

## Flux de données (runtime)

1. Le service `cron` lit `config/config.yml`.
2. Il appelle l'API COC, puis stocke l'état courant et les snapshots.
3. Les tables s'enrichissent à chaque exécution horaire (`fetch_cron`).
4. `dashboard-api` lit uniquement PostgreSQL.
5. Le front React Native Web (`dashboard`) appelle `dashboard-api` (`/api/overview`, `/api/player/<tag>`).

## Colonnes clés pour décisions de chef

- Dons: `players.donations`, `players.donations_received`, historique `player_snapshots`.
- Participation GDC/LDC: `clan_wars.war_type` + `war_member_performances`.
- Ligue joueur: `players.league_tier_name`.
- Clan Games (cumulé): `players.clan_games_points_total`.
- Clan Games (pilotage): delta mensuel calculé depuis `player_snapshots` (max mensuel puis différence mois N vs N-1).
- Capitale: `capital_raid_seasons` + `capital_raid_member_stats` + cumul `players.clan_capital_contributions`.
