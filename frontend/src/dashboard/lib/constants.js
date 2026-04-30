export const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
export const REFRESH_MS = Number(import.meta.env.VITE_REFRESH_MS || 300000);
export const DEFAULT_SCALE = "30d";

export const WAR_FAMILY_LABEL = {
  overall: "Global",
  gdc: "GDC",
  ldc: "LDC",
};

export const PLAYER_SORT_DEFAULT = {
  key: "health_score",
  direction: "desc",
};

export const PLAYER_SORTS = {
  name: { label: "Joueur", defaultDirection: "asc", value: (player) => String(player?.name || "").toLowerCase() },
  town_hall: {
    label: "TH",
    defaultDirection: "desc",
    value: (player) => Number(player?.town_hall_level || 0),
  },
  donations: {
    label: "Dons",
    defaultDirection: "desc",
    value: (player) => Number(player?.donations || 0),
  },
  stars: {
    label: "Etoiles",
    defaultDirection: "desc",
    value: (player) => Number(player?.overall?.attack_stars || 0),
  },
  raid_loot: {
    label: "Raid cum.",
    defaultDirection: "desc",
    value: (player) => Number(player?.raid_loot_total || 0),
  },
  jdc: {
    label: "JDC cum.",
    defaultDirection: "desc",
    value: (player) => Number(player?.clan_games_total || 0),
  },
  gdc_missed: {
    label: "GDC miss",
    defaultDirection: "desc",
    value: (player) => Number(player?.gdc?.missed_attacks || 0),
  },
  ldc_missed: {
    label: "LDC miss",
    defaultDirection: "desc",
    value: (player) => Number(player?.ldc?.missed_attacks || 0),
  },
  last_activity: {
    label: "Dernière activité",
    defaultDirection: "desc",
    value: (player) => {
      const parsed = Date.parse(String(player?.estimated_last_activity_at || ""));
      return Number.isNaN(parsed) ? 0 : parsed;
    },
  },
  health_score: {
    label: "Score",
    defaultDirection: "desc",
    value: (player) => Number(player?.health_score || 0),
  },
};
