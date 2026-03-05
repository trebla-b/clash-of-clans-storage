import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import {
  Bar,
  Line,
  Radar,
} from "react-chartjs-2";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  RadialLinearScale,
  Tooltip,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
);

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const REFRESH_MS = Number(import.meta.env.VITE_REFRESH_MS || 300000);

const numberFmt = new Intl.NumberFormat("fr-FR");
const shortDateFmt = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});
const longDateFmt = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const WAR_FAMILY_LABEL = {
  overall: "Global",
  gdc: "GDC",
  ldc: "LDC",
};

const PLAYER_SORT_DEFAULT = {
  key: "health_score",
  direction: "desc",
};

const PLAYER_SORTS = {
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
    label: "Raid loot",
    defaultDirection: "desc",
    value: (player) => Number(player?.latest_raid_loot || 0),
  },
  jdc: {
    label: "JDC",
    defaultDirection: "desc",
    value: (player) => Number(player?.clan_games_monthly_delta || 0),
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

function parseRoute() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
  const parts = path.split("/").filter(Boolean);
  if (parts[0] === "players" && parts[1]) {
    return { view: "player", tag: decodeURIComponent(parts[1]) };
  }
  return { view: "overview" };
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Erreur API (${response.status}): ${body || response.statusText}`);
  }
  return response.json();
}

function fmtInt(value) {
  return numberFmt.format(Number(value || 0));
}

function fmtPct(value) {
  return `${Number(value || 0).toFixed(1)} %`;
}

function fmtDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return shortDateFmt.format(date);
}

function fmtDateOnly(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return longDateFmt.format(date);
}

function buildClanPointsChart(points) {
  const clanPoints = points.map((item) => Number(item?.clan_points || 0));
  const clanPointDeltas = clanPoints.map((value, index) => (index === 0 ? 0 : value - clanPoints[index - 1]));

  return {
    labels: points.map((item) => item.label),
    datasets: [
      {
        label: "Delta points clan",
        data: clanPointDeltas,
        borderColor: "#09a7b6",
        backgroundColor: "rgba(9, 167, 182, 0.18)",
        fill: true,
        tension: 0.35,
      },
      {
        label: "Membres",
        data: points.map((item) => item.members),
        borderColor: "#37cf90",
        backgroundColor: "rgba(55, 207, 144, 0.1)",
        tension: 0.3,
        yAxisID: "y1",
      },
    ],
  };
}

function buildWarOutcomesChart(outcomes) {
  const overall = outcomes?.overall || [];
  const gdcMap = new Map((outcomes?.gdc || []).map((row) => [row.label, row]));
  const ldcMap = new Map((outcomes?.ldc || []).map((row) => [row.label, row]));
  const labels = overall.map((row) => row.label);

  return {
    labels,
    datasets: [
      {
        label: "GDC win",
        data: labels.map((label) => gdcMap.get(label)?.wins || 0),
        backgroundColor: "rgba(55, 207, 144, 0.85)",
        stack: "wins",
      },
      {
        label: "LDC win",
        data: labels.map((label) => ldcMap.get(label)?.wins || 0),
        backgroundColor: "rgba(9, 167, 182, 0.85)",
        stack: "wins",
      },
      {
        label: "GDC loss",
        data: labels.map((label) => gdcMap.get(label)?.losses || 0),
        backgroundColor: "rgba(255, 118, 86, 0.85)",
        stack: "losses",
      },
      {
        label: "LDC loss",
        data: labels.map((label) => ldcMap.get(label)?.losses || 0),
        backgroundColor: "rgba(255, 179, 71, 0.85)",
        stack: "losses",
      },
    ],
  };
}

function buildHealthChart(components) {
  return {
    labels: components.map((item) => item.label),
    datasets: [
      {
        label: "Score",
        data: components.map((item) => item.value),
        borderColor: "#3bd2f0",
        backgroundColor: "rgba(59, 210, 240, 0.2)",
        pointBackgroundColor: "#3bd2f0",
      },
    ],
  };
}

function buildClanGamesChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Delta mensuel Clan Games",
        data: series.map((item) => item.monthly_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
    ],
  };
}

function buildPlayerSnapshotChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Trophées",
        data: series.map((item) => item.trophies),
        borderColor: "#4dd7f8",
        backgroundColor: "rgba(77, 215, 248, 0.18)",
        fill: true,
        tension: 0.3,
      },
    ],
  };
}

function buildPlayerDeltaChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Dons",
        data: series.map((item) => item.donations_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
      {
        label: "Capitale",
        data: series.map((item) => item.capital_delta),
        backgroundColor: "rgba(77, 215, 248, 0.84)",
      },
    ],
  };
}

function buildPlayerClanGamesMonthlyChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Delta mensuel",
        data: series.map((item) => item.monthly_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
    ],
  };
}

function buildPlayerWarChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Attaques utilisées",
        data: series.map((item) => item.used),
        backgroundColor: "rgba(85, 230, 169, 0.85)",
        stack: "attacks",
      },
      {
        label: "Attaques oubliées",
        data: series.map((item) => item.missed),
        backgroundColor: "rgba(255, 118, 86, 0.9)",
        stack: "attacks",
      },
      {
        label: "Etoiles",
        data: series.map((item) => item.stars),
        type: "line",
        borderColor: "#4dd7f8",
        yAxisID: "y1",
        tension: 0.25,
      },
    ],
  };
}

function buildPlayerCapitalChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Loot",
        data: series.map((item) => item.loot),
        backgroundColor: "rgba(77, 215, 248, 0.8)",
        yAxisID: "y",
      },
      {
        label: "Attaques",
        data: series.map((item) => item.attacks),
        type: "line",
        borderColor: "#55e6a9",
        yAxisID: "y1",
        tension: 0.3,
      },
      {
        label: "Capacité",
        data: series.map((item) => item.capacity),
        type: "line",
        borderColor: "#ffc35b",
        borderDash: [6, 4],
        pointRadius: 0,
        yAxisID: "y1",
      },
    ],
  };
}

function chartOptions({ stacked = false, dualAxis = false, radar = false } = {}) {
  if (radar) {
    return {
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#e8f8ff" },
        },
      },
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: { backdropColor: "transparent", color: "#b4d9e6" },
          grid: { color: "rgba(180, 217, 230, 0.2)" },
          pointLabels: { color: "#d9f1ff" },
        },
      },
    };
  }

  return {
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: { color: "#e8f8ff" },
      },
    },
    scales: {
      x: {
        stacked,
        ticks: { color: "#b4d9e6" },
        grid: { color: "rgba(180, 217, 230, 0.12)" },
      },
      y: {
        stacked,
        ticks: { color: "#b4d9e6", precision: 0 },
        grid: { color: "rgba(180, 217, 230, 0.12)" },
      },
      ...(dualAxis
        ? {
            y1: {
              position: "right",
              ticks: { color: "#b4d9e6", precision: 0 },
              grid: { drawOnChartArea: false },
            },
          }
        : {}),
    },
  };
}

function Panel({ title, subtitle, children, wide = false }) {
  return (
    <View style={[styles.panel, wide && styles.panelWide]}>
      <View style={styles.panelHeader}>
        <Text style={styles.panelTitle}>{title}</Text>
        {subtitle ? <Text style={styles.panelSubtitle}>{subtitle}</Text> : null}
      </View>
      {children}
    </View>
  );
}

function Metric({ label, value, hint, danger = false }) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      {hint ? <Text style={[styles.metricHint, danger && styles.metricHintDanger]}>{hint}</Text> : null}
    </View>
  );
}

function ScaleBar({ scales, currentScale, onChange }) {
  return (
    <View style={styles.scaleRow}>
      {(scales || []).map((scale) => {
        const active = scale.key === currentScale;
        return (
          <Pressable
            key={scale.key}
            onPress={() => onChange(scale.key)}
            style={[styles.scaleChip, active && styles.scaleChipActive]}
          >
            <Text style={[styles.scaleChipText, active && styles.scaleChipTextActive]}>{scale.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function OverviewView({ data, scale, onScaleChange, onOpenPlayer }) {
  const clan = data?.clan || {};
  const kpis = data?.kpis || {};
  const wars = data?.wars || {};
  const health = data?.health || {};
  const charts = data?.charts || {};
  const players = data?.players || [];
  const [playerSort, setPlayerSort] = useState(PLAYER_SORT_DEFAULT);

  const pointsChart = useMemo(() => buildClanPointsChart(charts.clan_points || []), [charts.clan_points]);
  const warChart = useMemo(() => buildWarOutcomesChart(charts.war_outcomes || {}), [charts.war_outcomes]);
  const healthChart = useMemo(() => buildHealthChart(charts.health_components || []), [charts.health_components]);
  const clanGamesChart = useMemo(() => buildClanGamesChart(charts.clan_games || []), [charts.clan_games]);
  const sortedPlayers = useMemo(() => {
    const conf = PLAYER_SORTS[playerSort.key] || PLAYER_SORTS.health_score;
    const direction = playerSort.direction === "asc" ? 1 : -1;
    const items = [...players];
    items.sort((a, b) => {
      const av = conf.value(a);
      const bv = conf.value(b);
      if (typeof av === "string" || typeof bv === "string") {
        return String(av).localeCompare(String(bv), "fr") * direction;
      }
      return (Number(av || 0) - Number(bv || 0)) * direction;
    });
    return items;
  }, [players, playerSort]);

  const onSortPlayers = useCallback((key) => {
    setPlayerSort((current) => {
      if (current.key === key) {
        return {
          key,
          direction: current.direction === "asc" ? "desc" : "asc",
        };
      }
      return {
        key,
        direction: PLAYER_SORTS[key]?.defaultDirection || "desc",
      };
    });
  }, []);

  return (
    <>
      <View style={styles.hero}>
        <Text style={styles.heroEyebrow}>Site inauguré le {fmtDateOnly(data?.freshness?.first_snapshot)}</Text>
        <Text style={styles.heroTitle}>{clan.name || "Clan"}</Text>
        <Text style={styles.heroSubtitle}>
          {clan.tag || "-"} · Niveau {fmtInt(clan.clan_level)} · {fmtInt(kpis.active_members)} membres actifs
        </Text>
        <ScaleBar scales={data?.meta?.scales} currentScale={scale} onChange={onScaleChange} />
      </View>

      <View style={styles.metricsGrid}>
        <Metric label="Santé globale" value={`${Number(health.score || 0).toFixed(1)} / 100`} hint={`Grade ${health.grade || "D"}`} />
        <Metric label="Points clan" value={fmtInt(clan.clan_points)} hint={`${fmtInt(kpis.clan_points_delta)} sur période`} />
        <Metric label="Dons envoyés" value={fmtInt(kpis.donations_sent)} hint={`reçus ${fmtInt(kpis.donations_received)}`} />
        <Metric
          label="Clan Games Δ mois"
          value={fmtInt(kpis.clan_games_current_month_delta)}
          hint={`mois précédent ${fmtInt(kpis.clan_games_previous_month_delta)}`}
        />
        <Metric
          label="Capitale (cumul)"
          value={fmtInt(kpis.capital_contributions)}
          hint="weekend raids (ven-lun)"
        />
        <Metric label="Win rate global" value={fmtPct(wars?.overall?.win_rate)} hint={`${fmtInt(wars?.overall?.wins)}W / ${fmtInt(wars?.overall?.losses)}L`} />
      </View>

      <View style={styles.metricsGrid}>
        <Metric
          label="GDC participation"
          value={`${fmtInt(wars?.gdc?.attacks_used)}/${fmtInt(wars?.gdc?.attack_capacity)}`}
          hint={`${fmtInt(wars?.gdc?.missed_attacks)} oubliées (finies)`}
          danger={Number(wars?.gdc?.missed_attacks || 0) > 0}
        />
        <Metric
          label="LDC participation"
          value={`${fmtInt(wars?.ldc?.attacks_used)}/${fmtInt(wars?.ldc?.attack_capacity)}`}
          hint={`${fmtInt(wars?.ldc?.missed_attacks)} oubliées (finies)`}
          danger={Number(wars?.ldc?.missed_attacks || 0) > 0}
        />
        <Metric label="GDC war ended" value={fmtInt(wars?.gdc?.wars_ended)} hint={`WR ${fmtPct(wars?.gdc?.win_rate)}`} />
        <Metric label="LDC war ended" value={fmtInt(wars?.ldc?.wars_ended)} hint={`WR ${fmtPct(wars?.ldc?.win_rate)}`} />
      </View>

      <View style={styles.panelRow}>
        <Panel title="Evolution points clan" subtitle="delta entre snapshots" wide>
          <View style={styles.chartWrap}>
            <Line data={pointsChart} options={chartOptions({ dualAxis: true })} />
          </View>
        </Panel>
        <Panel title="Santé pondérée" subtitle="discipline, capitale, dons, fraîcheur">
          <View style={styles.chartWrap}>
            <Radar data={healthChart} options={chartOptions({ radar: true })} />
          </View>
        </Panel>
      </View>

      <View style={styles.panelRow}>
        <Panel title="Résultats guerres GDC vs LDC" subtitle="comparaison des issues" wide>
          <View style={styles.chartWrap}>
            <Bar data={warChart} options={chartOptions({ stacked: true })} />
          </View>
        </Panel>
        <Panel title="Clan Games (delta mensuel)" subtitle="événement mensuel, comparaison mois par mois">
          <View style={styles.chartWrap}>
            <Bar data={clanGamesChart} options={chartOptions({ dualAxis: true })} />
          </View>
        </Panel>
      </View>

      <Panel title="Détail participation joueurs">
        {players.length === 0 ? (
          <Text style={styles.emptyText}>Aucun membre actif trouvé.</Text>
        ) : (
          <View style={styles.tableWrap}>
            <View style={[styles.tableRow, styles.tableHeaderRow]}>
              {Object.entries(PLAYER_SORTS).map(([key, conf]) => {
                const isActive = playerSort.key === key;
                const arrow = isActive ? (playerSort.direction === "asc" ? " ▲" : " ▼") : "";
                return (
                  <Pressable
                    key={key}
                    onPress={() => onSortPlayers(key)}
                    style={[styles.headerSortCell, key === "name" ? styles.cellName : null]}
                  >
                    <Text style={[styles.tableCell, key === "name" ? styles.cellName : null]}>
                      {conf.label}
                      {arrow}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
            {sortedPlayers.map((player) => (
              <Pressable
                key={player.player_tag}
                onPress={() => onOpenPlayer(player.player_slug || player.player_tag)}
                style={styles.tableRow}
              >
                <Text style={[styles.tableCell, styles.cellName]} numberOfLines={1}>
                  {player.name}
                </Text>
                <Text style={styles.tableCell}>{fmtInt(player.town_hall_level)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.donations)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.overall?.attack_stars)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.latest_raid_loot)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.clan_games_monthly_delta)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.gdc?.missed_attacks)} miss</Text>
                <Text style={styles.tableCell}>{fmtInt(player.ldc?.missed_attacks)} miss</Text>
                <Text style={styles.tableCell}>{fmtDate(player.estimated_last_activity_at)}</Text>
                <Text style={styles.tableCell}>{fmtInt(player.health_score)}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </Panel>

      <Panel title="Fraîcheur DB">
        <View style={styles.metricsGrid}>
          <Metric label="Dernier fetch" value={fmtDate(data?.freshness?.latest_snapshot)} />
        </View>
      </Panel>
    </>
  );
}

function PlayerView({ data, scale, onScaleChange, onBack }) {
  const [family, setFamily] = useState("overall");

  useEffect(() => {
    setFamily("overall");
  }, [data?.player?.tag, scale]);

  const player = data?.player || {};
  const summary = data?.summary || {};
  const charts = data?.charts || {};

  const snapshotSeries = charts?.snapshots || [];
  const warSeries = charts?.war_history?.[family] || [];
  const capitalSeries = charts?.capital_history || [];
  const clanGamesMonthlySeries = charts?.clan_games_monthly || [];

  const snapshotChart = useMemo(() => buildPlayerSnapshotChart(snapshotSeries), [snapshotSeries]);
  const deltaChart = useMemo(() => buildPlayerDeltaChart(snapshotSeries), [snapshotSeries]);
  const warChart = useMemo(() => buildPlayerWarChart(warSeries), [warSeries]);
  const capitalChart = useMemo(() => buildPlayerCapitalChart(capitalSeries), [capitalSeries]);
  const clanGamesMonthlyChart = useMemo(
    () => buildPlayerClanGamesMonthlyChart(clanGamesMonthlySeries),
    [clanGamesMonthlySeries],
  );
  const lastActivityHint =
    Number(summary?.last_activity_hours || 0) >= 9999
      ? undefined
      : `${Number(summary?.last_activity_hours || 0).toFixed(1)} h`;

  return (
    <>
      <View style={styles.hero}>
        <Text style={styles.heroEyebrow}>Drill-down joueur</Text>
        <Text style={styles.heroTitle}>{player.name || "Joueur"}</Text>
        <Text style={styles.heroSubtitle}>
          {player.tag || "-"} · TH {fmtInt(player.town_hall_level)} · {player.league_tier_name || "Sans ligue"}
        </Text>
        <View style={styles.heroActionRow}>
          <Pressable onPress={onBack} style={styles.backButton}>
            <Text style={styles.backButtonText}>Retour clan</Text>
          </Pressable>
          <ScaleBar scales={data?.meta?.scales} currentScale={scale} onChange={onScaleChange} />
        </View>
      </View>

      <View style={styles.metricsGrid}>
        <Metric label="Score joueur" value={fmtInt(summary.player_health)} hint={`fraîcheur ${fmtInt(summary.freshness_hours)} h`} />
        <Metric label="Dernière activité estimée" value={fmtDate(summary.last_activity_at)} hint={lastActivityHint} />
        <Metric label="Trophées" value={fmtInt(player.trophies)} hint={`best ${fmtInt(player.best_trophies)}`} />
        <Metric label="Dons" value={fmtInt(player.donations)} hint={`reçus ${fmtInt(player.donations_received)}`} />
        <Metric
          label="Clan Games Δ mois"
          value={fmtInt(summary.clan_games_current_month_delta)}
          hint={`mois précédent ${fmtInt(summary.clan_games_previous_month_delta)}`}
        />
        <Metric label="Capitale cumulée" value={fmtInt(player.clan_capital_contributions)} />
      </View>

      <View style={styles.metricsGrid}>
        <Metric
          label="Global wars"
          value={`${fmtInt(summary?.overall?.attacks_used)}/${fmtInt(summary?.overall?.attack_capacity)}`}
          hint={`${fmtInt(summary?.overall?.missed_attacks)} oubliées`}
          danger={Number(summary?.overall?.missed_attacks || 0) > 0}
        />
        <Metric
          label="GDC"
          value={`${fmtInt(summary?.gdc?.attacks_used)}/${fmtInt(summary?.gdc?.attack_capacity)}`}
          hint={`${fmtInt(summary?.gdc?.missed_attacks)} oubliées`}
          danger={Number(summary?.gdc?.missed_attacks || 0) > 0}
        />
        <Metric
          label="LDC"
          value={`${fmtInt(summary?.ldc?.attacks_used)}/${fmtInt(summary?.ldc?.attack_capacity)}`}
          hint={`${fmtInt(summary?.ldc?.missed_attacks)} oubliées`}
          danger={Number(summary?.ldc?.missed_attacks || 0) > 0}
        />
        <Metric label="Participation globale" value={fmtPct(summary?.overall?.participation_rate)} />
        <Metric label="Participation GDC" value={fmtPct(summary?.gdc?.participation_rate)} />
        <Metric label="Participation LDC" value={fmtPct(summary?.ldc?.participation_rate)} />
      </View>

      <View style={styles.panelRow}>
        <Panel title="Timeline trophées" subtitle="historique des snapshots" wide>
          <View style={styles.chartWrap}>
            <Line data={snapshotChart} options={chartOptions()} />
          </View>
        </Panel>
        <Panel title="Progression (delta)" subtitle="dons + capitale (snapshots)">
          <View style={styles.chartWrap}>
            <Bar data={deltaChart} options={chartOptions({ stacked: true })} />
          </View>
        </Panel>
      </View>

      <Panel title="Clan Games (delta mensuel)" subtitle="suivi mois par mois uniquement">
        <View style={styles.chartWrap}>
          <Bar data={clanGamesMonthlyChart} options={chartOptions({ dualAxis: true })} />
        </View>
      </Panel>

      <Panel title="Participation guerre" subtitle="attaques oubliées comptées seulement si guerre terminée">
        <View style={styles.scaleRow}>
          {Object.keys(WAR_FAMILY_LABEL).map((key) => {
            const active = family === key;
            return (
              <Pressable
                key={key}
                onPress={() => setFamily(key)}
                style={[styles.scaleChip, active && styles.scaleChipActive]}
              >
                <Text style={[styles.scaleChipText, active && styles.scaleChipTextActive]}>{WAR_FAMILY_LABEL[key]}</Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.chartWrap}>
          <Bar data={warChart} options={chartOptions({ stacked: true, dualAxis: true })} />
        </View>
      </Panel>

      <Panel title="Capitale" subtitle="loot et exécution par weekend (ven-lun)">
        <View style={styles.chartWrap}>
          <Bar data={capitalChart} options={chartOptions({ dualAxis: true })} />
        </View>
      </Panel>

      <Panel title="Historique guerre" subtitle="GDC/LDC différenciés">
        <View style={styles.tableWrap}>
          <View style={[styles.tableRow, styles.tableHeaderRow]}>
            <Text style={[styles.tableCell, styles.cellName]}>Date</Text>
            <Text style={styles.tableCell}>Type</Text>
            <Text style={styles.tableCell}>Etat</Text>
            <Text style={styles.tableCell}>Adversaire</Text>
            <Text style={styles.tableCell}>Attaques</Text>
            <Text style={styles.tableCell}>Oubliées</Text>
          </View>
          {(data?.histories?.wars || []).map((war) => (
            <View key={war.war_id} style={styles.tableRow}>
              <Text style={[styles.tableCell, styles.cellName]}>{fmtDate(war.start_time)}</Text>
              <Text style={styles.tableCell}>{war.war_type === "cwl" ? "LDC" : "GDC"}</Text>
              <Text style={styles.tableCell}>{war.state || "-"}</Text>
              <Text style={styles.tableCell} numberOfLines={1}>
                {war.opponent_name || "-"}
              </Text>
              <Text style={styles.tableCell}>
                {fmtInt(war.attacks_used)}/{fmtInt(war.attack_capacity)}
              </Text>
              <Text style={styles.tableCell}>{fmtInt(war.missed_attacks)}</Text>
            </View>
          ))}
        </View>
      </Panel>
    </>
  );
}

export default function App() {
  const [route, setRoute] = useState(parseRoute());
  const [scale, setScale] = useState("30d");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overviewData, setOverviewData] = useState(null);
  const [playerData, setPlayerData] = useState(null);

  const navigateOverview = useCallback(() => {
    window.history.pushState({}, "", "/");
    setRoute({ view: "overview" });
  }, []);

  const navigatePlayer = useCallback((tag) => {
    const slug = String(tag || "").replace(/^#/, "");
    window.history.pushState({}, "", `/players/${encodeURIComponent(slug)}`);
    setRoute({ view: "player", tag: slug });
  }, []);

  useEffect(() => {
    const onPopState = () => setRoute(parseRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const loadOverview = useCallback(async () => {
    const payload = await apiGet(`/overview?scale=${encodeURIComponent(scale)}`);
    setOverviewData(payload);
    setError("");
  }, [scale]);

  const loadPlayer = useCallback(
    async (tag) => {
      const payload = await apiGet(`/player/${encodeURIComponent(tag)}?scale=${encodeURIComponent(scale)}`);
      setPlayerData(payload);
      setError("");
    },
    [scale],
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      if (route.view === "player") {
        await loadPlayer(route.tag);
      } else {
        await loadOverview();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, [loadOverview, loadPlayer, route.tag, route.view]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const interval = setInterval(loadData, REFRESH_MS);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <View style={styles.root}>
      <View style={[styles.blob, styles.blobA]} />
      <View style={[styles.blob, styles.blobB]} />
      <View style={[styles.blob, styles.blobC]} />

      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.shell}>
          {loading ? (
            <View style={styles.stateBox}>
              <ActivityIndicator size="large" color="#6ee9f8" />
              <Text style={styles.stateText}>Chargement des stats depuis la DB...</Text>
            </View>
          ) : null}

          {!loading && error ? (
            <View style={styles.stateBox}>
              <Text style={styles.errorTitle}>Erreur dashboard</Text>
              <Text style={styles.stateText}>{error}</Text>
              <Pressable onPress={loadData} style={styles.retryButton}>
                <Text style={styles.retryButtonText}>Réessayer</Text>
              </Pressable>
            </View>
          ) : null}

          {!loading && !error && route.view === "overview" && overviewData ? (
            <OverviewView
              data={overviewData}
              scale={scale}
              onScaleChange={setScale}
              onOpenPlayer={navigatePlayer}
            />
          ) : null}

          {!loading && !error && route.view === "player" && playerData ? (
            <PlayerView
              data={playerData}
              scale={scale}
              onScaleChange={setScale}
              onBack={navigateOverview}
            />
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#070f1f",
    minHeight: "100vh",
  },
  blob: {
    position: "fixed",
    borderRadius: 999,
    opacity: 0.45,
    pointerEvents: "none",
  },
  blobA: {
    width: 480,
    height: 480,
    top: -120,
    left: -120,
    backgroundColor: "#0f6ea9",
    filter: "blur(56px)",
  },
  blobB: {
    width: 420,
    height: 420,
    top: 120,
    right: -80,
    backgroundColor: "#1fb881",
    filter: "blur(60px)",
  },
  blobC: {
    width: 460,
    height: 460,
    bottom: -170,
    left: "26%",
    backgroundColor: "#2fa9f2",
    filter: "blur(64px)",
  },
  page: {
    paddingVertical: 30,
    paddingHorizontal: 16,
    minHeight: "100vh",
  },
  shell: {
    width: "100%",
    maxWidth: 1220,
    marginHorizontal: "auto",
    gap: 16,
  },
  hero: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(149, 220, 244, 0.22)",
    backgroundColor: "rgba(9, 22, 43, 0.66)",
    padding: 22,
    gap: 10,
  },
  heroEyebrow: {
    color: "#8ed2eb",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    fontSize: 11,
    fontWeight: "700",
  },
  heroTitle: {
    color: "#ecfbff",
    fontSize: 34,
    fontWeight: "800",
  },
  heroSubtitle: {
    color: "#b9dced",
    fontSize: 14,
  },
  heroActionRow: {
    gap: 12,
  },
  backButton: {
    alignSelf: "flex-start",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: "rgba(109, 209, 237, 0.2)",
    borderWidth: 1,
    borderColor: "rgba(143, 231, 255, 0.4)",
  },
  backButtonText: {
    color: "#dcf8ff",
    fontWeight: "700",
  },
  scaleRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  scaleChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(147, 224, 247, 0.24)",
    backgroundColor: "rgba(11, 35, 60, 0.76)",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  scaleChipActive: {
    backgroundColor: "rgba(77, 215, 248, 0.2)",
    borderColor: "rgba(134, 231, 255, 0.8)",
  },
  scaleChipText: {
    color: "#9cc8dc",
    fontSize: 12,
    fontWeight: "600",
  },
  scaleChipTextActive: {
    color: "#ecfbff",
  },
  metricsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  metricCard: {
    minWidth: 180,
    flexGrow: 1,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "rgba(144, 220, 243, 0.2)",
    backgroundColor: "rgba(9, 23, 45, 0.67)",
    padding: 14,
    gap: 6,
  },
  metricLabel: {
    color: "#96bed1",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  metricValue: {
    color: "#eefaff",
    fontSize: 22,
    fontWeight: "800",
  },
  metricHint: {
    color: "#8eb8ca",
    fontSize: 12,
  },
  metricHintDanger: {
    color: "#ff9a7f",
  },
  panelRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  panel: {
    flex: 1,
    minWidth: 320,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "rgba(140, 211, 236, 0.2)",
    backgroundColor: "rgba(8, 21, 40, 0.7)",
    padding: 16,
    gap: 10,
  },
  panelWide: {
    flexGrow: 2,
  },
  panelHeader: {
    gap: 4,
  },
  panelTitle: {
    color: "#effbff",
    fontSize: 18,
    fontWeight: "700",
  },
  panelSubtitle: {
    color: "#91b9cc",
    fontSize: 12,
  },
  chartWrap: {
    height: 300,
  },
  listWrap: {
    gap: 10,
  },
  listRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(133, 213, 240, 0.16)",
    backgroundColor: "rgba(10, 29, 52, 0.72)",
    paddingVertical: 10,
    paddingHorizontal: 12,
    gap: 10,
  },
  rowTitle: {
    color: "#e7f8ff",
    fontWeight: "700",
    fontSize: 14,
  },
  rowHint: {
    color: "#8fb9cc",
    fontSize: 12,
  },
  rowRight: {
    alignItems: "flex-end",
    gap: 2,
  },
  rowDanger: {
    color: "#ff9c83",
    fontWeight: "700",
    fontSize: 12,
  },
  tableWrap: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(142, 222, 247, 0.2)",
    overflow: "hidden",
  },
  tableRow: {
    flexDirection: "row",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(134, 213, 239, 0.12)",
    backgroundColor: "rgba(9, 26, 47, 0.72)",
    minHeight: 44,
  },
  tableHeaderRow: {
    backgroundColor: "rgba(16, 46, 77, 0.72)",
  },
  headerSortCell: {
    flex: 1,
    justifyContent: "center",
  },
  tableCell: {
    flex: 1,
    color: "#d5edf8",
    fontSize: 12,
    paddingHorizontal: 8,
    paddingVertical: 8,
  },
  cellName: {
    flex: 2,
    fontWeight: "700",
  },
  emptyText: {
    color: "#8fb9cc",
    fontSize: 13,
  },
  stateBox: {
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 24,
    paddingVertical: 42,
    borderWidth: 1,
    borderColor: "rgba(134, 213, 239, 0.2)",
    backgroundColor: "rgba(10, 30, 52, 0.8)",
    gap: 10,
  },
  stateText: {
    color: "#b8d9e9",
    fontSize: 14,
    textAlign: "center",
  },
  errorTitle: {
    color: "#ffd7ca",
    fontSize: 18,
    fontWeight: "700",
  },
  retryButton: {
    borderRadius: 999,
    backgroundColor: "rgba(255, 141, 109, 0.22)",
    borderWidth: 1,
    borderColor: "rgba(255, 171, 145, 0.8)",
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  retryButtonText: {
    color: "#ffe1d8",
    fontWeight: "700",
  },
});
