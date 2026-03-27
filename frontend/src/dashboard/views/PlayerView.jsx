import { useEffect, useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Bar, Line } from "react-chartjs-2";

import PlayerCapitalSection from "../components/PlayerCapitalSection";
import WarParticipationTimeline from "../components/WarParticipationTimeline";
import { Metric, Panel, ScaleBar } from "../components/common";
import {
  buildPlayerCapitalChart,
  buildPlayerClanGamesMonthlyChart,
  buildPlayerDeltaChart,
  buildPlayerSnapshotChart,
  chartOptions,
} from "../lib/charts";
import { WAR_FAMILY_LABEL } from "../lib/constants";
import { fmtDate, fmtInt, fmtPct } from "../lib/formatters";
import { buildPlayerWarTimeline } from "../lib/war";
import styles from "../styles";

export default function PlayerView({ data, scale, onScaleChange, onBack }) {
  const [family, setFamily] = useState("overall");

  useEffect(() => {
    setFamily("overall");
  }, [data?.player?.tag, scale]);

  const player = data?.player || {};
  const summary = data?.summary || {};
  const charts = data?.charts || {};
  const summaryCapital = summary?.capital || {};

  const snapshotSeries = charts?.snapshots || [];
  const capitalSeries = charts?.capital_history || [];
  const clanGamesMonthlySeries = charts?.clan_games_monthly || [];
  const warTimeline = useMemo(() => buildPlayerWarTimeline(data?.histories?.wars || [], family), [data?.histories?.wars, family]);

  const snapshotChart = useMemo(() => buildPlayerSnapshotChart(snapshotSeries), [snapshotSeries]);
  const deltaChart = useMemo(() => buildPlayerDeltaChart(snapshotSeries), [snapshotSeries]);
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
        <Panel title="Progression" subtitle="dons (delta) entre snapshots">
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

      <Panel title="Participation guerre" subtitle="timeline par guerre, plus récent à gauche · oublis comptés seulement si guerre terminée">
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
        <WarParticipationTimeline wars={warTimeline} />
      </Panel>

      <PlayerCapitalSection capitalHistory={data?.histories?.capital || []} capitalChart={capitalChart} summaryCapital={summaryCapital} />

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
