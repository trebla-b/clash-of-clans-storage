import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Bar } from "react-chartjs-2";

import WarParticipationTimeline from "../components/WarParticipationTimeline";
import { Metric, Panel, SectionHeader } from "../components/common";
import { buildWarOutcomesChart, chartOptions } from "../lib/charts";
import { WAR_FAMILY_LABEL } from "../lib/constants";
import { fmtDate, fmtInt, fmtPct } from "../lib/formatters";
import { buildWarParticipationTimeline, getWarFamilyKey } from "../lib/war";
import styles from "../styles";

function latestEndedWar(wars, family) {
  return (wars || []).find((war) => String(war?.state || "").toLowerCase() === "warended" && getWarFamilyKey(war?.war_type) === family) || null;
}

function formatWarResultValue(war) {
  if (!war) {
    return "-";
  }
  const outcome = String(war?.outcome || "").toLowerCase();
  const badge = outcome === "win" ? "V" : outcome === "loss" ? "D" : outcome === "draw" ? "N" : "?";
  return `${badge} ${fmtInt(war?.clan_stars)}-${fmtInt(war?.opponent_stars)}`;
}

function formatWarHint(war) {
  if (!war) {
    return "aucune guerre terminée";
  }
  return `${fmtDate(war?.start_time)} · ${war?.opponent_name || "adversaire inconnu"}`;
}

export default function ClanWarSection({ data }) {
  const wars = data?.wars || {};
  const warHistory = data?.histories?.wars || [];
  const warOutcomes = data?.charts?.war_outcomes || {};
  const [family, setFamily] = useState("overall");

  const warChart = useMemo(() => buildWarOutcomesChart(warOutcomes), [warOutcomes]);
  const warTimeline = useMemo(() => buildWarParticipationTimeline(warHistory, family), [warHistory, family]);
  const latestGdc = useMemo(() => latestEndedWar(warHistory, "gdc"), [warHistory]);
  const latestLdc = useMemo(() => latestEndedWar(warHistory, "ldc"), [warHistory]);

  return (
    <>
      <SectionHeader
        eyebrow="GDC / Ligue"
        title="Historique guerres du clan"
        subtitle="lecture dédiée des GDC et LDC avec résultat, étoiles adverses et niveau d'exécution guerre par guerre"
      />

      <View style={styles.metricsGrid}>
        <Metric label="Dernière GDC" value={formatWarResultValue(latestGdc)} hint={formatWarHint(latestGdc)} />
        <Metric label="Dernière Ligue" value={formatWarResultValue(latestLdc)} hint={formatWarHint(latestLdc)} />
        <Metric
          label="Participation GDC"
          value={`${fmtInt(wars?.gdc?.attacks_used)}/${fmtInt(wars?.gdc?.attack_capacity)}`}
          hint={`${fmtInt(wars?.gdc?.missed_attacks)} oubliées`}
          danger={Number(wars?.gdc?.missed_attacks || 0) > 0}
        />
        <Metric
          label="Participation Ligue"
          value={`${fmtInt(wars?.ldc?.attacks_used)}/${fmtInt(wars?.ldc?.attack_capacity)}`}
          hint={`${fmtInt(wars?.ldc?.missed_attacks)} oubliées`}
          danger={Number(wars?.ldc?.missed_attacks || 0) > 0}
        />
        <Metric label="WR GDC" value={fmtPct(wars?.gdc?.win_rate)} hint={`${fmtInt(wars?.gdc?.wins)}W / ${fmtInt(wars?.gdc?.losses)}L`} />
        <Metric label="WR Ligue" value={fmtPct(wars?.ldc?.win_rate)} hint={`${fmtInt(wars?.ldc?.wins)}W / ${fmtInt(wars?.ldc?.losses)}L`} />
      </View>

      <View style={styles.panelRow}>
        <Panel title="Résultats guerres GDC vs LDC" subtitle="comparaison des issues et de la cadence de victoires" wide>
          <View style={styles.chartWrap}>
            <Bar data={warChart} options={chartOptions({ stacked: true })} />
          </View>
        </Panel>
      </View>

      <Panel title="Historique guerres clan" subtitle="timeline par guerre, plus récent à gauche · badge V/D/N + étoiles adverses">
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
    </>
  );
}
