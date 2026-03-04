(function () {
  const data = window.DASH_DATA || {};

  const palette = {
    teal: "#0e8f8f",
    blue: "#2f7fcd",
    orange: "#dd8e2d",
    red: "#c43d3d",
    line: "rgba(17, 45, 53, 0.16)",
    text: "#23424c",
  };

  if (window.Chart) {
    Chart.defaults.color = palette.text;
    Chart.defaults.font.family = '"Manrope", "Segoe UI", sans-serif';
    Chart.defaults.borderColor = palette.line;
  }

  function drawEmpty(canvasId, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#4b6470";
    ctx.font = "14px Manrope";
    ctx.fillText(label, 16, 28);
  }

  function overviewCharts() {
    const points = Array.isArray(data.clan_points) ? data.clan_points : [];
    const wars = Array.isArray(data.war_outcomes) ? data.war_outcomes : [];
    const health = Array.isArray(data.health_components) ? data.health_components : [];

    const clanCanvas = document.getElementById("chart-clan-points");
    if (clanCanvas) {
      if (!points.length) {
        drawEmpty("chart-clan-points", "Pas assez de points pour tracer la courbe.");
      } else {
        new Chart(clanCanvas, {
          type: "line",
          data: {
            labels: points.map((p) => p.label),
            datasets: [
              {
                label: "Points clan",
                data: points.map((p) => p.clan_points),
                borderColor: palette.teal,
                backgroundColor: "rgba(14, 143, 143, 0.18)",
                fill: true,
                tension: 0.34,
                yAxisID: "y",
              },
              {
                label: "Membres",
                data: points.map((p) => p.members),
                borderColor: palette.blue,
                backgroundColor: "rgba(47, 127, 205, 0.12)",
                tension: 0.3,
                fill: false,
                yAxisID: "y1",
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
              y: {
                position: "left",
                ticks: { precision: 0 },
              },
              y1: {
                position: "right",
                grid: { drawOnChartArea: false },
                ticks: { precision: 0 },
              },
            },
            plugins: {
              legend: { position: "bottom" },
            },
          },
        });
      }
    }

    const warsCanvas = document.getElementById("chart-wars");
    if (warsCanvas) {
      if (!wars.length) {
        drawEmpty("chart-wars", "Pas assez de guerres pour tracer le graphe.");
      } else {
        new Chart(warsCanvas, {
          type: "bar",
          data: {
            labels: wars.map((w) => w.label),
            datasets: [
              {
                label: "Victoires",
                data: wars.map((w) => w.wins),
                backgroundColor: "rgba(14, 143, 143, 0.82)",
                borderRadius: 8,
              },
              {
                label: "Défaites",
                data: wars.map((w) => w.losses),
                backgroundColor: "rgba(196, 61, 61, 0.8)",
                borderRadius: 8,
              },
              {
                label: "Nuls",
                data: wars.map((w) => w.draws),
                backgroundColor: "rgba(221, 142, 45, 0.8)",
                borderRadius: 8,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            scales: {
              x: { stacked: true },
              y: { stacked: true, ticks: { precision: 0 } },
            },
            plugins: { legend: { position: "bottom" } },
          },
        });
      }
    }

    const healthCanvas = document.getElementById("chart-health");
    if (healthCanvas) {
      if (!health.length) {
        drawEmpty("chart-health", "Pas assez de données santé.");
      } else {
        new Chart(healthCanvas, {
          type: "radar",
          data: {
            labels: health.map((h) => h.label),
            datasets: [
              {
                label: "Score",
                data: health.map((h) => h.value),
                borderColor: palette.orange,
                backgroundColor: "rgba(221, 142, 45, 0.26)",
                pointBackgroundColor: palette.orange,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            scales: {
              r: {
                beginAtZero: true,
                max: 100,
                ticks: { stepSize: 20 },
              },
            },
            plugins: { legend: { display: false } },
          },
        });
      }
    }
  }

  function playerCharts() {
    const snapshots = Array.isArray(data.snapshots) ? data.snapshots : [];
    const warHistory = Array.isArray(data.war_history) ? data.war_history : [];
    const capitalHistory = Array.isArray(data.capital_history) ? data.capital_history : [];

    const trophiesCanvas = document.getElementById("chart-player-trophies");
    if (trophiesCanvas) {
      if (!snapshots.length) {
        drawEmpty("chart-player-trophies", "Pas assez de snapshots joueur.");
      } else {
        new Chart(trophiesCanvas, {
          type: "line",
          data: {
            labels: snapshots.map((s) => s.label),
            datasets: [
              {
                label: "Trophées",
                data: snapshots.map((s) => s.trophies),
                borderColor: palette.blue,
                backgroundColor: "rgba(47, 127, 205, 0.2)",
                fill: true,
                tension: 0.34,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            plugins: { legend: { position: "bottom" } },
          },
        });
      }
    }

    const deltaCanvas = document.getElementById("chart-player-deltas");
    if (deltaCanvas) {
      if (!snapshots.length) {
        drawEmpty("chart-player-deltas", "Pas assez de données delta.");
      } else {
        new Chart(deltaCanvas, {
          type: "bar",
          data: {
            labels: snapshots.map((s) => s.label),
            datasets: [
              {
                label: "Delta dons",
                data: snapshots.map((s) => s.donations_delta),
                backgroundColor: "rgba(14, 143, 143, 0.82)",
                borderRadius: 7,
              },
              {
                label: "Delta clan games",
                data: snapshots.map((s) => s.clan_games_delta),
                backgroundColor: "rgba(221, 142, 45, 0.8)",
                borderRadius: 7,
              },
              {
                label: "Delta capitale",
                data: snapshots.map((s) => s.capital_delta),
                backgroundColor: "rgba(47, 127, 205, 0.8)",
                borderRadius: 7,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            scales: {
              x: { stacked: true },
              y: { stacked: true, ticks: { precision: 0 } },
            },
            plugins: { legend: { position: "bottom" } },
          },
        });
      }
    }

    const warsCanvas = document.getElementById("chart-player-wars");
    if (warsCanvas) {
      if (!warHistory.length) {
        drawEmpty("chart-player-wars", "Pas assez de guerres pour ce joueur.");
      } else {
        new Chart(warsCanvas, {
          type: "bar",
          data: {
            labels: warHistory.map((w) => w.label),
            datasets: [
              {
                label: "Attaques utilisées",
                data: warHistory.map((w) => w.used),
                backgroundColor: "rgba(14, 143, 143, 0.8)",
                borderRadius: 7,
                stack: "attacks",
              },
              {
                label: "Attaques manquées",
                data: warHistory.map((w) => w.missed),
                backgroundColor: "rgba(196, 61, 61, 0.82)",
                borderRadius: 7,
                stack: "attacks",
              },
              {
                label: "Etoiles",
                data: warHistory.map((w) => w.stars),
                type: "line",
                borderColor: palette.orange,
                pointBackgroundColor: palette.orange,
                yAxisID: "y1",
                tension: 0.3,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            scales: {
              y: { stacked: true, ticks: { precision: 0 } },
              y1: {
                position: "right",
                grid: { drawOnChartArea: false },
                ticks: { precision: 0 },
              },
            },
            plugins: { legend: { position: "bottom" } },
          },
        });
      }
    }

    const capitalCanvas = document.getElementById("chart-player-capital");
    if (capitalCanvas) {
      if (!capitalHistory.length) {
        drawEmpty("chart-player-capital", "Pas assez de weekends capitale.");
      } else {
        new Chart(capitalCanvas, {
          type: "bar",
          data: {
            labels: capitalHistory.map((c) => c.label),
            datasets: [
              {
                label: "Loot",
                data: capitalHistory.map((c) => c.loot),
                backgroundColor: "rgba(47, 127, 205, 0.84)",
                borderRadius: 7,
                yAxisID: "y",
              },
              {
                label: "Attaques utilisées",
                data: capitalHistory.map((c) => c.attacks),
                type: "line",
                borderColor: palette.teal,
                pointBackgroundColor: palette.teal,
                yAxisID: "y1",
                tension: 0.28,
              },
              {
                label: "Capacité",
                data: capitalHistory.map((c) => c.capacity),
                type: "line",
                borderColor: palette.orange,
                borderDash: [5, 5],
                pointRadius: 0,
                yAxisID: "y1",
                tension: 0.2,
              },
            ],
          },
          options: {
            maintainAspectRatio: false,
            scales: {
              y: { position: "left", ticks: { precision: 0 } },
              y1: {
                position: "right",
                grid: { drawOnChartArea: false },
                ticks: { precision: 0 },
              },
            },
            plugins: { legend: { position: "bottom" } },
          },
        });
      }
    }
  }

  if (document.getElementById("chart-clan-points")) {
    overviewCharts();
  }

  if (document.getElementById("chart-player-trophies")) {
    playerCharts();
  }
})();
