import { useCallback, useEffect, useState } from "react";

import { parseRoute, pushOverviewRoute, pushPlayerRoute } from "../lib/router";

export function useRouteState() {
  const [route, setRoute] = useState(parseRoute());

  const navigateOverview = useCallback(() => {
    setRoute(pushOverviewRoute());
  }, []);

  const navigatePlayer = useCallback((tag) => {
    setRoute(pushPlayerRoute(tag));
  }, []);

  useEffect(() => {
    const onPopState = () => setRoute(parseRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return {
    navigateOverview,
    navigatePlayer,
    route,
  };
}
