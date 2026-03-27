import { Pressable, Text, View } from "react-native";

import styles from "../styles";

export function Panel({ title, subtitle, children, wide = false }) {
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

export function Metric({ label, value, hint, danger = false }) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      {hint ? <Text style={[styles.metricHint, danger && styles.metricHintDanger]}>{hint}</Text> : null}
    </View>
  );
}

export function ScaleBar({ scales, currentScale, onChange }) {
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

export function SectionHeader({ eyebrow, title, subtitle }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionEyebrow}>{eyebrow}</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}
