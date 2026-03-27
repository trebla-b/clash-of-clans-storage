import { API_BASE } from "./constants";

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Erreur API (${response.status}): ${body || response.statusText}`);
  }
  return response.json();
}
