import { ScrollView, Text, View } from "react-native";
import { Bar } from "react-chartjs-2";

import { Metric, Panel } from "./common";
import { chartOptions } from "../lib/charts";
import { fmtInt, fmtPct, fmtRaidWindow, fmtSignedInt } from "../lib/formatters";
import styles from "../styles";

function metricValueOrDash(value, formatter = fmtInt) {
  return value === undefined || value === null ? "-" : formatter(value);
}

export default function PlayerCapitalSection({ capitalHistory, capitalChart, summaryCapital }) {
  const currentRaid = summaryCapital?.current || {};
  const latestCompleted = summaryCapital?.latest_completed || {};
  const bestWeekend = summaryCapital?.best_weekend || {};
  const hasCompletedWeekends = Number(summaryCapital?.completed_weekends || 0) > 0;
  const currentStateLabel = currentRaid?.is_completed ? "Terminé" : "En cours";

  return (
    <>
      <Panel title="Raids capitales (cumulé)" subtitle="lecture par weekend, raid courant séparé du dernier raid terminé">
        {capitalHistory.length === 0 ? (
          <Text style={styles.emptyText}>Aucun weekend raid historisé pour ce joueur.</Text>
        ) : (
          <View style={styles.metricsGrid}>
            <Metric
              label="Raid courant"
              value={metricValueOrDash(currentRaid?.capital_resources_looted)}
              hint={`${currentStateLabel} · ${fmtRaidWindow(currentRaid?.season_start_time, currentRaid?.season_end_time)}`}
            />
            <Metric
              label="Exécution courante"
              value={metricValueOrDash(
                currentRaid?.participation_rate,
                fmtPct,
              )}
              hint={`${fmtInt(currentRaid?.used_attacks)}/${fmtInt(currentRaid?.capacity_attacks)} attaques`}
            />
            <Metric
              label="Dernier raid terminé"
              value={hasCompletedWeekends ? fmtInt(latestCompleted?.capital_resources_looted) : "-"}
              hint={hasCompletedWeekends ? fmtRaidWindow(latestCompleted?.season_start_time, latestCompleted?.season_end_time) : "pas encore historisé"}
            />
            <Metric
              label="Meilleur weekend"
              value={hasCompletedWeekends ? fmtInt(bestWeekend?.capital_resources_looted) : "-"}
              hint={hasCompletedWeekends ? fmtRaidWindow(bestWeekend?.season_start_time, bestWeekend?.season_end_time) : "pas encore historisé"}
            />
            <Metric
              label="Moyenne loot"
              value={hasCompletedWeekends ? fmtInt(summaryCapital?.average_loot) : "-"}
              hint={`${fmtInt(summaryCapital?.completed_weekends)} raids terminés`}
            />
            <Metric
              label="Moyenne exécution"
              value={hasCompletedWeekends ? fmtPct(summaryCapital?.average_participation) : "-"}
              hint="sur raids terminés"
            />
          </View>
        )}
      </Panel>

      <Panel title="Capitale" subtitle="loot et exécution par weekend (ven-lun)">
        {capitalHistory.length === 0 ? (
          <Text style={styles.emptyText}>Aucun historique individuel disponible.</Text>
        ) : (
          <View style={styles.chartWrap}>
            <Bar data={capitalChart} options={chartOptions({ dualAxis: true })} />
          </View>
        )}
      </Panel>

      <Panel title="Historique raids" subtitle="une ligne par weekend pour suivre la tendance individuelle">
        {capitalHistory.length === 0 ? (
          <Text style={styles.emptyText}>Aucun weekend raid historisé pour ce joueur.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tableScrollContent}>
            <View style={[styles.tableWrap, styles.tableWide]}>
              <View style={[styles.tableRow, styles.tableHeaderRow]}>
                <Text style={[styles.tableCell, styles.cellName]}>Weekend</Text>
                <Text style={styles.tableCell}>Etat</Text>
                <Text style={styles.tableCell}>Loot</Text>
                <Text style={styles.tableCell}>Δ loot</Text>
                <Text style={styles.tableCell}>Attaques</Text>
                <Text style={styles.tableCell}>Exécution</Text>
                <Text style={styles.tableCell}>Loot/atk</Text>
              </View>
              {capitalHistory.map((raid) => (
                <View key={raid.season_start_time || `${raid.season_end_time || "raid"}`} style={styles.tableRow}>
                  <Text style={[styles.tableCell, styles.cellName]} numberOfLines={1}>
                    {fmtRaidWindow(raid.season_start_time, raid.season_end_time)}
                  </Text>
                  <Text style={styles.tableCell}>{raid.is_completed ? "Terminé" : "En cours"}</Text>
                  <Text style={styles.tableCell}>{fmtInt(raid.capital_resources_looted)}</Text>
                  <Text style={styles.tableCell}>{fmtSignedInt(raid.capital_total_loot_delta)}</Text>
                  <Text style={styles.tableCell}>
                    {fmtInt(raid.used_attacks)}/{fmtInt(raid.capacity_attacks)}
                  </Text>
                  <Text style={styles.tableCell}>{fmtPct(raid.participation_rate)}</Text>
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
