CREATE TABLE IF NOT EXISTS clans (
    tag TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    clan_level INTEGER,
    members INTEGER,
    clan_points INTEGER,
    war_wins INTEGER,
    war_losses INTEGER,
    war_ties INTEGER,
    war_win_streak INTEGER,
    is_war_log_public BOOLEAN,
    required_trophies INTEGER,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clan_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    clan_tag TEXT NOT NULL REFERENCES clans(tag) ON DELETE CASCADE,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    members INTEGER,
    clan_points INTEGER,
    war_wins INTEGER,
    war_losses INTEGER,
    war_ties INTEGER,
    raw_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clan_snapshots_tag_time
    ON clan_snapshots (clan_tag, fetched_at DESC);

CREATE TABLE IF NOT EXISTS players (
    tag TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    clan_tag TEXT REFERENCES clans(tag) ON DELETE SET NULL,
    role TEXT,
    exp_level INTEGER,
    town_hall_level INTEGER,
    town_hall_weapon_level INTEGER,
    builder_hall_level INTEGER,
    trophies INTEGER,
    best_trophies INTEGER,
    builder_base_trophies INTEGER,
    best_builder_base_trophies INTEGER,
    war_stars INTEGER,
    attack_wins INTEGER,
    defense_wins INTEGER,
    donations INTEGER,
    donations_received INTEGER,
    clan_capital_contributions INTEGER,
    league_tier_id INTEGER,
    league_tier_name TEXT,
    builder_base_league_id INTEGER,
    builder_base_league_name TEXT,
    current_league_group_tag TEXT,
    current_league_season_id BIGINT,
    previous_league_group_tag TEXT,
    previous_league_season_id BIGINT,
    clan_games_points_total INTEGER,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE players ADD COLUMN IF NOT EXISTS league_tier_id INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS league_tier_name TEXT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS builder_base_league_id INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS builder_base_league_name TEXT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS current_league_group_tag TEXT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS current_league_season_id BIGINT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS previous_league_group_tag TEXT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS previous_league_season_id BIGINT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS clan_games_points_total INTEGER;

CREATE TABLE IF NOT EXISTS player_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    player_tag TEXT NOT NULL REFERENCES players(tag) ON DELETE CASCADE,
    clan_tag TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trophies INTEGER,
    town_hall_level INTEGER,
    war_stars INTEGER,
    donations INTEGER,
    donations_received INTEGER,
    clan_capital_contributions INTEGER,
    league_tier_name TEXT,
    builder_base_league_name TEXT,
    clan_games_points_total INTEGER,
    raw_json JSONB NOT NULL
);

ALTER TABLE player_snapshots ADD COLUMN IF NOT EXISTS league_tier_name TEXT;
ALTER TABLE player_snapshots ADD COLUMN IF NOT EXISTS builder_base_league_name TEXT;
ALTER TABLE player_snapshots ADD COLUMN IF NOT EXISTS clan_games_points_total INTEGER;

CREATE INDEX IF NOT EXISTS idx_player_snapshots_tag_time
    ON player_snapshots (player_tag, fetched_at DESC);

CREATE TABLE IF NOT EXISTS clan_memberships (
    clan_tag TEXT NOT NULL REFERENCES clans(tag) ON DELETE CASCADE,
    player_tag TEXT NOT NULL REFERENCES players(tag) ON DELETE CASCADE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (clan_tag, player_tag)
);

CREATE INDEX IF NOT EXISTS idx_clan_memberships_active
    ON clan_memberships (clan_tag, is_active);

CREATE TABLE IF NOT EXISTS clan_wars (
    war_id TEXT PRIMARY KEY,
    war_tag TEXT,
    war_type TEXT NOT NULL,
    league_group_season TEXT,
    league_group_state TEXT,
    state TEXT,
    team_size INTEGER,
    attacks_per_member INTEGER,
    battle_modifier TEXT,
    preparation_start_time TIMESTAMPTZ,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    clan_tag TEXT,
    clan_name TEXT,
    clan_stars INTEGER,
    clan_destruction_percentage NUMERIC(6,3),
    clan_attacks INTEGER,
    opponent_tag TEXT,
    opponent_name TEXT,
    opponent_stars INTEGER,
    opponent_destruction_percentage NUMERIC(6,3),
    opponent_attacks INTEGER,
    outcome TEXT,
    raw_json JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clan_wars_clan_time
    ON clan_wars (clan_tag, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_clan_wars_type
    ON clan_wars (war_type, state);

CREATE TABLE IF NOT EXISTS war_member_performances (
    war_id TEXT NOT NULL REFERENCES clan_wars(war_id) ON DELETE CASCADE,
    clan_tag TEXT NOT NULL,
    player_tag TEXT NOT NULL,
    player_name TEXT NOT NULL,
    town_hall_level INTEGER,
    map_position INTEGER,
    attacks_used INTEGER,
    attack_capacity INTEGER,
    total_attack_stars INTEGER,
    total_attack_destruction NUMERIC(6,3),
    opponent_attacks INTEGER,
    best_opponent_stars INTEGER,
    best_opponent_destruction NUMERIC(6,3),
    missed_attacks INTEGER,
    is_our_clan BOOLEAN NOT NULL,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (war_id, clan_tag, player_tag)
);

CREATE INDEX IF NOT EXISTS idx_war_member_performances_player
    ON war_member_performances (player_tag, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_war_member_performances_our
    ON war_member_performances (is_our_clan, clan_tag);

CREATE TABLE IF NOT EXISTS war_attacks (
    war_id TEXT NOT NULL REFERENCES clan_wars(war_id) ON DELETE CASCADE,
    attack_order INTEGER NOT NULL,
    attacker_tag TEXT NOT NULL,
    defender_tag TEXT NOT NULL,
    attacker_clan_tag TEXT,
    defender_clan_tag TEXT,
    stars INTEGER,
    destruction_percentage NUMERIC(6,3),
    duration_seconds INTEGER,
    is_our_clan BOOLEAN NOT NULL,
    raw_json JSONB NOT NULL,
    PRIMARY KEY (war_id, attacker_tag, defender_tag, attack_order)
);

CREATE INDEX IF NOT EXISTS idx_war_attacks_attacker
    ON war_attacks (attacker_tag, war_id);

CREATE TABLE IF NOT EXISTS cwl_groups (
    group_id TEXT PRIMARY KEY,
    clan_tag TEXT NOT NULL,
    season TEXT,
    state TEXT,
    raw_json JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cwl_group_clans (
    group_id TEXT NOT NULL REFERENCES cwl_groups(group_id) ON DELETE CASCADE,
    clan_tag TEXT NOT NULL,
    name TEXT,
    clan_level INTEGER,
    member_count INTEGER,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, clan_tag)
);

CREATE TABLE IF NOT EXISTS cwl_group_members (
    group_id TEXT NOT NULL REFERENCES cwl_groups(group_id) ON DELETE CASCADE,
    clan_tag TEXT NOT NULL,
    player_tag TEXT NOT NULL,
    player_name TEXT,
    town_hall_level INTEGER,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, clan_tag, player_tag)
);

CREATE INDEX IF NOT EXISTS idx_cwl_group_members_player
    ON cwl_group_members (player_tag, group_id);

CREATE TABLE IF NOT EXISTS capital_raid_seasons (
    clan_tag TEXT NOT NULL,
    season_start_time TIMESTAMPTZ NOT NULL,
    season_end_time TIMESTAMPTZ,
    state TEXT,
    capital_total_loot INTEGER,
    raids_completed INTEGER,
    total_attacks INTEGER,
    enemy_districts_destroyed INTEGER,
    offensive_reward INTEGER,
    defensive_reward INTEGER,
    raw_json JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (clan_tag, season_start_time)
);

CREATE INDEX IF NOT EXISTS idx_capital_raid_seasons_clan_time
    ON capital_raid_seasons (clan_tag, season_start_time DESC);

CREATE TABLE IF NOT EXISTS capital_raid_member_stats (
    clan_tag TEXT NOT NULL,
    season_start_time TIMESTAMPTZ NOT NULL,
    player_tag TEXT NOT NULL,
    player_name TEXT,
    attacks INTEGER,
    attack_limit INTEGER,
    bonus_attack_limit INTEGER,
    capital_resources_looted INTEGER,
    raw_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (clan_tag, season_start_time, player_tag),
    CONSTRAINT fk_capital_raid_member_season
        FOREIGN KEY (clan_tag, season_start_time)
        REFERENCES capital_raid_seasons(clan_tag, season_start_time)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_capital_raid_member_stats_player
    ON capital_raid_member_stats (player_tag, season_start_time DESC);

CREATE OR REPLACE VIEW v_current_clan_members AS
SELECT
    cm.clan_tag,
    cm.player_tag,
    p.name,
    p.trophies,
    p.town_hall_level,
    p.league_tier_name,
    p.builder_base_league_name,
    p.donations,
    p.donations_received,
    p.clan_games_points_total,
    p.clan_capital_contributions,
    cm.last_seen_at
FROM clan_memberships cm
JOIN players p ON p.tag = cm.player_tag
WHERE cm.is_active = TRUE;

CREATE OR REPLACE VIEW v_war_participation_30d AS
SELECT
    w.clan_tag,
    wmp.player_tag,
    MAX(wmp.player_name) AS player_name,
    COUNT(*) FILTER (WHERE w.state = 'warEnded') AS wars_ended,
    SUM(COALESCE(wmp.attack_capacity, 0)) AS attack_capacity,
    SUM(COALESCE(wmp.attacks_used, 0)) AS attacks_used,
    SUM(COALESCE(wmp.missed_attacks, 0)) AS missed_attacks,
    SUM(COALESCE(wmp.total_attack_stars, 0)) AS attack_stars,
    ROUND(AVG(COALESCE(wmp.total_attack_destruction, 0)), 2) AS avg_attack_destruction
FROM war_member_performances wmp
JOIN clan_wars w ON w.war_id = wmp.war_id
WHERE
    wmp.is_our_clan = TRUE
    AND w.start_time >= NOW() - INTERVAL '30 days'
GROUP BY w.clan_tag, wmp.player_tag;

CREATE OR REPLACE VIEW v_latest_capital_raid_member_stats AS
SELECT
    s.clan_tag,
    s.season_start_time,
    m.player_tag,
    m.player_name,
    m.attacks,
    m.attack_limit,
    m.bonus_attack_limit,
    m.capital_resources_looted
FROM capital_raid_member_stats m
JOIN (
    SELECT clan_tag, MAX(season_start_time) AS season_start_time
    FROM capital_raid_seasons
    GROUP BY clan_tag
) s
    ON s.clan_tag = m.clan_tag
   AND s.season_start_time = m.season_start_time;
