export function parseRoute() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
  const parts = path.split("/").filter(Boolean);
  if (parts[0] === "players" && parts[1]) {
    return { view: "player", tag: decodeURIComponent(parts[1]) };
  }
  return { view: "overview" };
}

export function buildOverviewRoute() {
  return { view: "overview" };
}

export function buildPlayerRoute(tag) {
  const slug = String(tag || "").replace(/^#/, "");
  return { view: "player", tag: slug };
}

export function pushOverviewRoute() {
  window.history.pushState({}, "", "/");
  return buildOverviewRoute();
}

export function pushPlayerRoute(tag) {
  const route = buildPlayerRoute(tag);
  window.history.pushState({}, "", `/players/${encodeURIComponent(route.tag)}`);
  return route;
}
