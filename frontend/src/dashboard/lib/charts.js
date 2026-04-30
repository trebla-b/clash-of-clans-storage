import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  RadialLinearScale,
  Tooltip,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
);

export function buildClanPointsChart(points) {
  const clanPoints = points.map((item) => Number(item?.clan_points || 0));
  const clanPointDeltas = clanPoints.map((value, index) => (index === 0 ? 0 : value - clanPoints[index - 1]));

  return {
    labels: points.map((item) => item.label),
    datasets: [
      {
        label: "Delta points clan",
        data: clanPointDeltas,
        borderColor: "#09a7b6",
        backgroundColor: "rgba(9, 167, 182, 0.18)",
        fill: true,
        tension: 0.35,
      },
      {
        label: "Membres",
        data: points.map((item) => item.members),
        borderColor: "#37cf90",
        backgroundColor: "rgba(55, 207, 144, 0.1)",
        tension: 0.3,
        yAxisID: "y1",
      },
    ],
  };
}

export function buildWarOutcomesChart(outcomes) {
  const overall = outcomes?.overall || [];
  const gdcMap = new Map((outcomes?.gdc || []).map((row) => [row.label, row]));
  const ldcMap = new Map((outcomes?.ldc || []).map((row) => [row.label, row]));
  const labels = overall.map((row) => row.label);

  return {
    labels,
    datasets: [
      {
        label: "GDC win",
        data: labels.map((label) => gdcMap.get(label)?.wins || 0),
        backgroundColor: "rgba(55, 207, 144, 0.85)",
        stack: "wins",
      },
      {
        label: "LDC win",
        data: labels.map((label) => ldcMap.get(label)?.wins || 0),
        backgroundColor: "rgba(9, 167, 182, 0.85)",
        stack: "wins",
      },
      {
        label: "GDC loss",
        data: labels.map((label) => gdcMap.get(label)?.losses || 0),
        backgroundColor: "rgba(255, 118, 86, 0.85)",
        stack: "losses",
      },
      {
        label: "LDC loss",
        data: labels.map((label) => ldcMap.get(label)?.losses || 0),
        backgroundColor: "rgba(255, 179, 71, 0.85)",
        stack: "losses",
      },
    ],
  };
}

export function buildHealthChart(components) {
  return {
    labels: components.map((item) => item.label),
    datasets: [
      {
        label: "Score",
        data: components.map((item) => item.value),
        borderColor: "#3bd2f0",
        backgroundColor: "rgba(59, 210, 240, 0.2)",
        pointBackgroundColor: "#3bd2f0",
      },
    ],
  };
}

export function buildClanGamesChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Delta mensuel Clan Games",
        data: series.map((item) => item.monthly_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
    ],
  };
}

export function buildPlayerSnapshotChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Trophées",
        data: series.map((item) => item.trophies),
        borderColor: "#4dd7f8",
        backgroundColor: "rgba(77, 215, 248, 0.18)",
        fill: true,
        tension: 0.3,
      },
    ],
  };
}

export function buildPlayerDeltaChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Dons",
        data: series.map((item) => item.donations_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
    ],
  };
}

export function buildPlayerClanGamesMonthlyChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Delta mensuel",
        data: series.map((item) => item.monthly_delta),
        backgroundColor: "rgba(85, 230, 169, 0.84)",
      },
    ],
  };
}

export function buildPlayerCapitalChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Loot",
        data: series.map((item) => item.loot),
        backgroundColor: "rgba(77, 215, 248, 0.8)",
        yAxisID: "y",
      },
      {
        label: "Attaques",
        data: series.map((item) => item.attacks),
        type: "line",
        borderColor: "#55e6a9",
        yAxisID: "y1",
        tension: 0.3,
      },
      {
        label: "Capacité",
        data: series.map((item) => item.capacity),
        type: "line",
        borderColor: "#ffc35b",
        borderDash: [6, 4],
        pointRadius: 0,
        yAxisID: "y1",
      },
    ],
  };
}

export function buildCapitalTrendChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Loot total",
        data: series.map((item) => item.loot),
        backgroundColor: "rgba(77, 215, 248, 0.82)",
      },
      {
        label: "Districts détruits",
        data: series.map((item) => item.districts),
        type: "line",
        borderColor: "#ffc35b",
        yAxisID: "y1",
        tension: 0.3,
      },
    ],
  };
}

export function buildCapitalExecutionChart(series) {
  return {
    labels: series.map((item) => item.label),
    datasets: [
      {
        label: "Participants",
        data: series.map((item) => item.active_raiders),
        backgroundColor: "rgba(85, 230, 169, 0.82)",
      },
      {
        label: "Effectif clan",
        data: series.map((item) => item.clan_members),
        type: "line",
        borderColor: "#4dd7f8",
        tension: 0.25,
      },
      {
        label: "Participation %",
        data: series.map((item) => item.participation_rate),
        type: "line",
        borderColor: "#ffc35b",
        yAxisID: "y1",
        tension: 0.25,
      },
    ],
  };
}

export function chartOptions({ stacked = false, dualAxis = false, radar = false, y1Max, y1TickSuffix = "" } = {}) {
  if (radar) {
    return {
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#e8f8ff" },
        },
      },
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: { backdropColor: "transparent", color: "#b4d9e6" },
          grid: { color: "rgba(180, 217, 230, 0.2)" },
          pointLabels: { color: "#d9f1ff" },
        },
      },
    };
  }

  return {
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: { color: "#e8f8ff" },
      },
    },
    scales: {
      x: {
        stacked,
        ticks: { color: "#b4d9e6" },
        grid: { color: "rgba(180, 217, 230, 0.12)" },
      },
      y: {
        stacked,
        ticks: { color: "#b4d9e6", precision: 0 },
        grid: { color: "rgba(180, 217, 230, 0.12)" },
      },
      ...(dualAxis
        ? {
            y1: {
              position: "right",
              ticks: {
                color: "#b4d9e6",
                precision: 0,
                ...(y1TickSuffix
                  ? {
                      callback(value) {
                        return `${value}${y1TickSuffix}`;
                      },
                    }
                  : {}),
              },
              ...(typeof y1Max === "number" ? { max: y1Max } : {}),
              grid: { drawOnChartArea: false },
            },
          }
        : {}),
    },
  };
}
