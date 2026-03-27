import { StyleSheet } from "react-native";

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
  sectionHeader: {
    marginTop: 6,
    paddingTop: 10,
    gap: 6,
  },
  sectionEyebrow: {
    color: "#8ed2eb",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    fontSize: 11,
    fontWeight: "700",
  },
  sectionTitle: {
    color: "#ecfbff",
    fontSize: 24,
    fontWeight: "800",
  },
  sectionSubtitle: {
    color: "#9fcddd",
    fontSize: 14,
    maxWidth: 820,
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
  warTimelineWrap: {
    gap: 12,
  },
  legendRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  legendSwatch: {
    width: 10,
    height: 10,
    borderRadius: 999,
  },
  legendLabel: {
    color: "#95bfd2",
    fontSize: 12,
  },
  warTimelineList: {
    gap: 12,
    paddingBottom: 4,
    paddingRight: 8,
  },
  warCard: {
    width: 220,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "rgba(139, 214, 239, 0.18)",
    backgroundColor: "rgba(10, 29, 52, 0.78)",
    padding: 14,
    gap: 12,
  },
  warCardHeader: {
    gap: 8,
  },
  warCardDate: {
    color: "#b8d9e9",
    fontSize: 12,
    fontWeight: "700",
  },
  warCardChipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  warChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  warChipType: {
    backgroundColor: "rgba(77, 215, 248, 0.14)",
    borderColor: "rgba(134, 231, 255, 0.28)",
  },
  warChipStatus: {
    backgroundColor: "rgba(114, 150, 174, 0.12)",
    borderColor: "rgba(140, 182, 205, 0.28)",
  },
  warChipStatusSuccess: {
    backgroundColor: "rgba(85, 230, 169, 0.14)",
    borderColor: "rgba(121, 243, 191, 0.34)",
  },
  warChipStatusWarning: {
    backgroundColor: "rgba(255, 195, 91, 0.12)",
    borderColor: "rgba(255, 210, 126, 0.34)",
  },
  warChipStatusDanger: {
    backgroundColor: "rgba(255, 118, 86, 0.14)",
    borderColor: "rgba(255, 159, 136, 0.34)",
  },
  warChipStatusInfo: {
    backgroundColor: "rgba(77, 215, 248, 0.14)",
    borderColor: "rgba(134, 231, 255, 0.34)",
  },
  warChipStatusNeutral: {
    backgroundColor: "rgba(128, 156, 176, 0.12)",
    borderColor: "rgba(157, 184, 203, 0.3)",
  },
  warChipText: {
    color: "#d8f1fb",
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  warChipTextSuccess: {
    color: "#78efbf",
  },
  warChipTextWarning: {
    color: "#ffd06e",
  },
  warChipTextDanger: {
    color: "#ff9f88",
  },
  warChipTextInfo: {
    color: "#93e8ff",
  },
  warChipTextNeutral: {
    color: "#c3d9e5",
  },
  warCardOpponent: {
    color: "#eefaff",
    fontSize: 16,
    fontWeight: "700",
  },
  warCardRate: {
    color: "#ecfbff",
    fontSize: 28,
    fontWeight: "800",
  },
  warCardTrack: {
    flexDirection: "row",
    height: 12,
    borderRadius: 999,
    overflow: "hidden",
    backgroundColor: "rgba(20, 50, 77, 0.92)",
  },
  warCardSegment: {
    height: "100%",
  },
  warCardSegmentUsed: {
    backgroundColor: "rgba(85, 230, 169, 0.92)",
  },
  warCardSegmentMissed: {
    backgroundColor: "rgba(255, 118, 86, 0.92)",
  },
  warCardSegmentRemaining: {
    backgroundColor: "rgba(77, 215, 248, 0.42)",
  },
  warCardMetaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  warCardMetaPrimary: {
    color: "#e6f8ff",
    fontSize: 13,
    fontWeight: "700",
  },
  warCardMetaSecondary: {
    color: "#8fb9cc",
    fontSize: 12,
  },
  warCardStars: {
    color: "#ffd06e",
    fontSize: 13,
    fontWeight: "800",
  },
  tableWrap: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(142, 222, 247, 0.2)",
    overflow: "hidden",
  },
  tableScrollContent: {
    paddingBottom: 4,
    paddingRight: 8,
  },
  tableWide: {
    minWidth: 980,
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

export default styles;
