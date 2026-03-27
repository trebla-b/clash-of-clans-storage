import { useCallback, useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Bar, Line, Radar } from "react-chartjs-2";

import CapitalSection from "./CapitalSection";
import WarParticipationTimeline from "../components/WarParticipationTimeline";
import { buildClanGamesChart, buildClanPointsChart, buildHealthChart, buildWarOutcomesChart, chartOptions } from "../lib/charts";
import { PLAYER_SORT_DEFAULT, PLAYER_SORTS, WAR_FAMILY_LABEL } from "../lib/constants";
import { fmtDate, fmtDateOnly, fmtInt, fmtPct } from "../lib/formatters";
import { buildWarParticipationTimeline } from "../lib/war";
import { Metric, Panel, ScaleBar } from "../components/common";
import styles from "../styles";

function sortPlayers(players, playerSort) {
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
}

export default function OverviewView({ data, scale, onScaleChange, onOpenPlayer }) {
  const clan = data?.clan || {};
  const kpis = data?.kpis || {};
  const wars = data?.wars || {};
  const health = data?.health || {};
  const charts = data?.charts || {};
  const players = data?.players || [];
  const [playerSort, setPlayerSort] = useState(PLAYER_SORT_DEFAULT);
  const [warFamily, setWarFamily] = useState("overall");

  const pointsChart = useMemo(() => buildClanPointsChart(charts.clan_points || []), [charts.clan_points]);
  const warChart = useMemo(() => buildWarOutcomesChart(charts.war_outcomes || {}), [charts.war_outcomes]);
  const healthChart = useMemo(() => buildHealthChart(charts.health_components || []), [charts.health_components]);
  const clanGamesChart = useMemo(() => buildClanGamesChart(charts.clan_games || []), [charts.clan_games]);
  const sortedPlayers = useMemo(() => sortPlayers(players, playerSort), [players, playerSort]);
  const warTimeline = useMemo(
    () => buildWarParticipationTimeline(data?.histories?.wars || [], warFamily),
    [data?.histories?.wars, warFamily],
  );

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
        <Text style={styles.heroEyebrow}>
          Site inauguré le {fmtDateOnly(data?.freshness?.first_snapshot)} · v{data?.meta?.app_version || "0.0.0"}
        </Text>
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
        <Metric label="Capitale (cumul)" value={fmtInt(kpis.capital_contributions)} hint="weekend raids (ven-lun)" />
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

      <Panel title="Historique guerres clan" subtitle="timeline par guerre, plus récent à gauche · oublis comptés seulement si guerre terminée">
        <View style={styles.scaleRow}>
          {Object.keys(WAR_FAMILY_LABEL).map((key) => {
            const active = warFamily === key;
            return (
              <Pressable
                key={key}
                onPress={() => setWarFamily(key)}
                style={[styles.scaleChip, active && styles.scaleChipActive]}
              >
                <Text style={[styles.scaleChipText, active && styles.scaleChipTextActive]}>{WAR_FAMILY_LABEL[key]}</Text>
              </Pressable>
            );
          })}
        </View>
        <WarParticipationTimeline wars={warTimeline} />
      </Panel>

      <CapitalSection data={data} />

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
