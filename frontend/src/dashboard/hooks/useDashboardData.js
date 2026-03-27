import { useCallback, useEffect, useState } from "react";

import { apiGet } from "../lib/api";
import { REFRESH_MS } from "../lib/constants";

export function useDashboardData(route, scale) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overviewData, setOverviewData] = useState(null);
  const [playerData, setPlayerData] = useState(null);

  const loadOverview = useCallback(async () => {
    const payload = await apiGet(`/overview?scale=${encodeURIComponent(scale)}`);
    setOverviewData(payload);
    setError("");
  }, [scale]);

  const loadPlayer = useCallback(
    async (tag) => {
      const payload = await apiGet(`/player/${encodeURIComponent(tag)}?scale=${encodeURIComponent(scale)}`);
      setPlayerData(payload);
      setError("");
    },
    [scale],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      if (route.view === "player") {
        await loadPlayer(route.tag);
      } else {
        await loadOverview();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, [loadOverview, loadPlayer, route.tag, route.view]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    const interval = setInterval(reload, REFRESH_MS);
    return () => clearInterval(interval);
  }, [reload]);

  return {
    error,
    loading,
    overviewData,
    playerData,
    reload,
  };
}
