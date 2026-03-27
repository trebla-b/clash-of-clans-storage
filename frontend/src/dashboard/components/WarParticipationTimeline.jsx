import { ScrollView, Text, View } from "react-native";

import { fmtInt, fmtPct } from "../lib/formatters";
import styles from "../styles";

function LegendItem({ color, label }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendSwatch, { backgroundColor: color }]} />
      <Text style={styles.legendLabel}>{label}</Text>
    </View>
  );
}

export default function WarParticipationTimeline({ wars }) {
  if (!wars.length) {
    return <Text style={styles.emptyText}>Aucune guerre disponible pour ce filtre.</Text>;
  }

  return (
    <View style={styles.warTimelineWrap}>
      <View style={styles.legendRow}>
        <LegendItem color="rgba(85, 230, 169, 0.9)" label="Utilisées" />
        <LegendItem color="rgba(255, 118, 86, 0.9)" label="Oubliées" />
        <LegendItem color="rgba(77, 215, 248, 0.42)" label="Restantes / non jouées" />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.warTimelineList}>
        {wars.map((war) => {
          const statusStyle = [
            styles.warChip,
            styles.warChipStatus,
            war.statusTone === "success" && styles.warChipStatusSuccess,
            war.statusTone === "warning" && styles.warChipStatusWarning,
            war.statusTone === "danger" && styles.warChipStatusDanger,
            war.statusTone === "info" && styles.warChipStatusInfo,
            war.statusTone === "neutral" && styles.warChipStatusNeutral,
          ];
          const statusTextStyle = [
            styles.warChipText,
            war.statusTone === "success" && styles.warChipTextSuccess,
            war.statusTone === "warning" && styles.warChipTextWarning,
            war.statusTone === "danger" && styles.warChipTextDanger,
            war.statusTone === "info" && styles.warChipTextInfo,
            war.statusTone === "neutral" && styles.warChipTextNeutral,
          ];
          const outcomeStyle = [
            styles.warChip,
            styles.warChipOutcome,
            war.outcomeTone === "success" && styles.warChipStatusSuccess,
            war.outcomeTone === "warning" && styles.warChipStatusWarning,
            war.outcomeTone === "danger" && styles.warChipStatusDanger,
          ];
          const outcomeTextStyle = [
            styles.warChipText,
            war.outcomeTone === "success" && styles.warChipTextSuccess,
            war.outcomeTone === "warning" && styles.warChipTextWarning,
            war.outcomeTone === "danger" && styles.warChipTextDanger,
          ];

          return (
            <View key={war.key} style={styles.warCard}>
              <View style={styles.warCardHeader}>
                <Text style={styles.warCardDate}>{war.dateLabel}</Text>
                <View style={styles.warCardChipRow}>
                  <View style={[styles.warChip, styles.warChipType]}>
                    <Text style={styles.warChipText}>{war.familyLabel}</Text>
                  </View>
                  <View style={statusStyle}>
                    <Text style={statusTextStyle}>{war.statusLabel}</Text>
                  </View>
                  {war.outcomeCode ? (
                    <View style={outcomeStyle}>
                      <Text style={outcomeTextStyle}>{war.outcomeCode}</Text>
                    </View>
                  ) : null}
                </View>
              </View>

              <Text style={styles.warCardOpponent} numberOfLines={1}>
                {war.opponentLabel}
              </Text>

              <Text style={styles.warCardRate}>{fmtPct(war.participationRate)}</Text>

              <View style={styles.warCardTrack}>
                {war.usedPct > 0 ? <View style={[styles.warCardSegment, styles.warCardSegmentUsed, { width: `${war.usedPct}%` }]} /> : null}
                {war.missedPct > 0 ? <View style={[styles.warCardSegment, styles.warCardSegmentMissed, { width: `${war.missedPct}%` }]} /> : null}
                {war.remainingPct > 0 ? (
                  <View style={[styles.warCardSegment, styles.warCardSegmentRemaining, { width: `${war.remainingPct}%` }]} />
                ) : null}
              </View>

              <View style={styles.warCardMetaRow}>
                <Text style={styles.warCardMetaPrimary}>
                  {fmtInt(war.used)}/{fmtInt(war.capacity)} attaques
                </Text>
                <Text style={styles.warCardMetaSecondary}>{war.capacityNote}</Text>
              </View>

              <View style={styles.warCardMetaRow}>
                <Text style={styles.warCardMetaSecondary}>{war.stateLabel}</Text>
                <Text style={styles.warCardStars}>{war.starsLabel || `${fmtInt(war.stars)}★`}</Text>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
}
