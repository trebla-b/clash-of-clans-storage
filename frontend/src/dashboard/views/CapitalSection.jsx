import { useMemo } from "react";
import { ScrollView, Text, View } from "react-native";
import { Bar } from "react-chartjs-2";

import { buildCapitalExecutionChart, buildCapitalTrendChart, chartOptions } from "../lib/charts";
import { fmtInt, fmtPct, fmtRaidWindow, fmtSignedFloat, fmtSignedInt } from "../lib/formatters";
import { Metric, Panel, SectionHeader } from "../components/common";
import styles from "../styles";

export default function CapitalSection({ data }) {
  const clan = data?.clan || {};
  const capital = data?.capital || {};
  const summary = capital?.summary || {};
  const latest = capital?.latest || {};
  const latestCompleted = summary?.latest_completed || {};
  const bestWeekend = summary?.best_weekend || {};
  const raidHistory = capital?.history || [];
  const latestRaid = raidHistory[0] || latest;
  const raidSeries = data?.charts?.capital_weekends || [];

  const capitalTrendChart = useMemo(() => buildCapitalTrendChart(raidSeries), [raidSeries]);
  const capitalExecutionChart = useMemo(() => buildCapitalExecutionChart(raidSeries), [raidSeries]);

  const lootTrend = Number(summary?.recent_completed_avg_loot || 0) - Number(summary?.previous_completed_avg_loot || 0);
  const participationTrend =
    Number(summary?.recent_completed_avg_participation || 0) - Number(summary?.previous_completed_avg_participation || 0);
  const hasTrendComparison = Number(summary?.completed_weekends || 0) >= 2;
  const latestStateLabel = latestRaid?.is_completed ? "Terminé" : "En cours";

  return (
    <>
      <SectionHeader
        eyebrow="Raids capitales"
        title="Vue cumulée weekend par weekend"
        subtitle={`${clan.name || "Clan"} ${clan.tag || "-"} · lecture séparée du raid en cours et des raids terminés pour suivre la tendance sans effet remise à zéro`}
      />

      <View style={styles.metricsGrid}>
        <Metric
          label="Raid courant"
          value={fmtInt(latestRaid?.capital_total_loot)}
          hint={`${latestStateLabel} · ${fmtRaidWindow(latestRaid?.season_start_time, latestRaid?.season_end_time)}`}
        />
        <Metric
          label="Dernier raid terminé"
          value={fmtInt(latestCompleted?.capital_total_loot)}
          hint={fmtRaidWindow(latestCompleted?.season_start_time, latestCompleted?.season_end_time)}
        />
        <Metric
          label="Exécution dernier terminé"
          value={fmtPct(latestCompleted?.participation_rate)}
          hint={`${fmtInt(latestCompleted?.active_raiders)}/${fmtInt(latestCompleted?.clan_members)} joueurs`}
        />
        <Metric
          label="Meilleur weekend"
          value={fmtInt(bestWeekend?.capital_total_loot)}
          hint={fmtRaidWindow(bestWeekend?.season_start_time, bestWeekend?.season_end_time)}
        />
        <Metric
          label="Moyenne loot"
          value={fmtInt(summary?.average_loot)}
          hint={`${fmtInt(summary?.completed_weekends)} weekends terminés`}
        />
        <Metric label="Moyenne exécution" value={fmtPct(summary?.average_participation)} hint="sur raids terminés" />
      </View>

      <View style={styles.metricsGrid}>
        <Metric
          label="Tendance loot"
          value={hasTrendComparison ? fmtSignedInt(lootTrend) : "-"}
          hint="moyenne 3 derniers raids vs précédents"
          danger={hasTrendComparison && lootTrend < 0}
        />
        <Metric
          label="Tendance exécution"
          value={hasTrendComparison ? fmtSignedFloat(participationTrend, " pts") : "-"}
          hint="moyenne 3 derniers raids vs précédents"
          danger={hasTrendComparison && participationTrend < 0}
        />
      </View>

      <View style={styles.panelRow}>
        <Panel title="Tendance loot" subtitle="volume cumulé par weekend raid" wide>
          <View style={styles.chartWrap}>
            <Bar data={capitalTrendChart} options={chartOptions({ dualAxis: true })} />
          </View>
        </Panel>
        <Panel title="Exécution raids" subtitle="joueurs participants, effectif clan et participation">
          <View style={styles.chartWrap}>
            <Bar data={capitalExecutionChart} options={chartOptions({ dualAxis: true, y1Max: 100, y1TickSuffix: "%" })} />
          </View>
        </Panel>
      </View>

      <Panel title="Historique cumulé par raid" subtitle="une ligne par weekend pour suivre la tendance réelle">
        {raidHistory.length === 0 ? (
          <Text style={styles.emptyText}>Aucun weekend raid trouvé sur cette période.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tableScrollContent}>
            <View style={[styles.tableWrap, styles.tableWide]}>
              <View style={[styles.tableRow, styles.tableHeaderRow]}>
                <Text style={[styles.tableCell, styles.cellName]}>Weekend</Text>
                <Text style={styles.tableCell}>Etat</Text>
                <Text style={styles.tableCell}>Loot</Text>
                <Text style={styles.tableCell}>Δ loot</Text>
                <Text style={styles.tableCell}>Participants</Text>
                <Text style={styles.tableCell}>Attaques</Text>
                <Text style={styles.tableCell}>Exécution</Text>
                <Text style={styles.tableCell}>Districts</Text>
                <Text style={styles.tableCell}>Loot/atk</Text>
              </View>
              {raidHistory.map((raid) => (
                <View key={raid.season_start_time || `${raid.season_end_time || "raid"}`} style={styles.tableRow}>
                  <Text style={[styles.tableCell, styles.cellName]} numberOfLines={1}>
                    {fmtRaidWindow(raid.season_start_time, raid.season_end_time)}
                  </Text>
                  <Text style={styles.tableCell}>{raid.is_completed ? "Terminé" : "En cours"}</Text>
                  <Text style={styles.tableCell}>{fmtInt(raid.capital_total_loot)}</Text>
                  <Text style={styles.tableCell}>{fmtSignedInt(raid.capital_total_loot_delta)}</Text>
                  <Text style={styles.tableCell}>
                    {fmtInt(raid.active_raiders)}/{fmtInt(raid.clan_members)}
                  </Text>
                  <Text style={styles.tableCell}>
                    {fmtInt(raid.used_attacks)}/{fmtInt(raid.capacity_attacks)}
                  </Text>
                  <Text style={styles.tableCell}>{fmtPct(raid.participation_rate)}</Text>
                  <Text style={styles.tableCell}>{fmtInt(raid.enemy_districts_destroyed)}</Text>
                  <Text style={styles.tableCell}>{fmtInt(raid.loot_per_attack)}</Text>
                </View>
              ))}
            </View>
          </ScrollView>
        )}
      </Panel>
    </>
  );
}
