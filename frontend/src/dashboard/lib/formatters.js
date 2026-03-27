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

export function fmtInt(value) {
  return numberFmt.format(Number(value || 0));
}

export function fmtPct(value) {
  return `${Number(value || 0).toFixed(1)} %`;
}

export function fmtDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return shortDateFmt.format(date);
}

export function fmtDateOnly(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return longDateFmt.format(date);
}

export function fmtRaidWindow(start, end) {
  const startText = fmtDateOnly(start);
  const endText = fmtDateOnly(end);
  if (startText === "-" && endText === "-") {
    return "-";
  }
  if (endText === "-") {
    return startText;
  }
  return `${startText} -> ${endText}`;
}

export function fmtSignedInt(value) {
  const number = Math.round(Number(value || 0));
  return `${number > 0 ? "+" : ""}${fmtInt(number)}`;
}

export function fmtSignedFloat(value, suffix = "") {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)}${suffix}`;
}
