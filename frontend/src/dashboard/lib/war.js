import { WAR_FAMILY_LABEL } from "./constants";
import { fmtDate, fmtInt } from "./formatters";

const WAR_STATE_LABEL = {
  preparation: "Préparation",
  inwar: "Guerre en cours",
  warended: "Guerre terminée",
};

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function getWarFamilyKey(warType) {
  return String(warType || "").toLowerCase() === "cwl" ? "ldc" : "gdc";
}

export function getWarStateLabel(state) {
  return WAR_STATE_LABEL[String(state || "").toLowerCase()] || "État inconnu";
}

export function getWarParticipationStatus({ state, used, capacity }) {
  const stateKey = String(state || "").toLowerCase();
  if (stateKey !== "warended") {
    if (stateKey === "preparation") {
      return { label: "Prépa", tone: "neutral" };
    }
    if (used >= capacity && capacity > 0) {
      return { label: "Joué", tone: "success" };
    }
    if (used > 0) {
      return { label: "En cours", tone: "info" };
    }
    return { label: "A faire", tone: "info" };
  }
  if (used >= capacity && capacity > 0) {
    return { label: "Complet", tone: "success" };
  }
  if (used <= 0) {
    return { label: "Absent", tone: "danger" };
  }
  return { label: "Partiel", tone: "warning" };
}

export function formatWarCapacityNote({ ended, missed, remaining }) {
  if (ended) {
    if (missed <= 0) {
      return "aucun oubli";
    }
    return `${fmtInt(missed)} ${missed > 1 ? "oubliées" : "oubliée"}`;
  }
  if (remaining <= 0) {
    return "tout joué";
  }
  return `${fmtInt(remaining)} ${remaining > 1 ? "restantes" : "restante"}`;
}

export function buildWarParticipationTimeline(wars, family) {
  return (wars || [])
    .filter((war) => family === "overall" || getWarFamilyKey(war?.war_type) === family)
    .map((war) => {
      const capacity = Math.max(Number(war?.attack_capacity || 0), 1);
      const used = clamp(Number(war?.attacks_used || 0), 0, capacity);
      const ended = String(war?.state || "").toLowerCase() === "warended";
      const missed = ended ? clamp(Number(war?.missed_attacks || 0), 0, Math.max(capacity - used, 0)) : 0;
      const remaining = Math.max(capacity - used - missed, 0);
      const participationRate = (used / capacity) * 100;
      const familyKey = getWarFamilyKey(war?.war_type);
      const status = getWarParticipationStatus({ state: war?.state, used, capacity });
      const outcomeKey = String(war?.outcome || "").toLowerCase();
      const outcomeMeta =
        outcomeKey === "win"
          ? { code: "V", tone: "success" }
          : outcomeKey === "loss"
            ? { code: "D", tone: "danger" }
            : outcomeKey === "draw"
              ? { code: "N", tone: "warning" }
              : null;
      const clanStars = war?.clan_stars;
      const opponentStars = war?.opponent_stars;
      const hasWarScore = clanStars !== undefined && clanStars !== null && opponentStars !== undefined && opponentStars !== null;

      return {
        key: war?.war_id || `${war?.start_time || ""}-${war?.opponent_name || ""}`,
        familyLabel: WAR_FAMILY_LABEL[familyKey],
        dateLabel: fmtDate(war?.start_time),
        opponentLabel: war?.opponent_name || "Adversaire inconnu",
        stateLabel: getWarStateLabel(war?.state),
        statusLabel: status.label,
        statusTone: status.tone,
        participationRate,
        used,
        capacity,
        missed,
        remaining,
        usedPct: (used / capacity) * 100,
        missedPct: (missed / capacity) * 100,
        remainingPct: (remaining / capacity) * 100,
        capacityNote: formatWarCapacityNote({ ended, missed, remaining }),
        stars: Number(war?.total_attack_stars || 0),
        starsLabel: hasWarScore ? `${fmtInt(clanStars)}★ vs ${fmtInt(opponentStars)}★` : `${fmtInt(war?.total_attack_stars)}★`,
        outcomeCode: outcomeMeta?.code,
        outcomeTone: outcomeMeta?.tone,
      };
    });
}

export const buildPlayerWarTimeline = buildWarParticipationTimeline;
