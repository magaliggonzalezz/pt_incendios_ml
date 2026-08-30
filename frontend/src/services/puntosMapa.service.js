import { apiFetch } from "./api";
import { enqueueMapRequest, normalizeBbox } from "./mapRequestQueue";

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  return search.toString();
}

function normalizePointParams(params = {}) {
  return {
    ...params,
    bbox: params.bbox ? normalizeBbox(params.bbox) : undefined,
  };
}

function territoryKey(params = {}) {
  return `${params.cve_ent || "mx"}:${params.cvegeo || "all"}:${params.anio || "sin-anio"}:${params.mes || "all"}`;
}

export function obtenerPuntosFirms(params = {}, options = {}) {
  const normalized = normalizePointParams(params);
  const query = buildQuery(normalized);
  const endpoint = `/api/puntos-mapa/firms${query ? `?${query}` : ""}`;
  const territory = territoryKey(normalized);
  return enqueueMapRequest({
    key: `firms:${query}`,
    channel: "puntos",
    latestKey: `firms:${territory}`,
    settleMs: 550,
    signal: options.signal,
    request: () => apiFetch(endpoint),
  });
}

export function obtenerIncendiosConafor(params = {}, options = {}) {
  const normalized = normalizePointParams(params);
  const query = buildQuery(normalized);
  const endpoint = `/api/puntos-mapa/conafor${query ? `?${query}` : ""}`;
  const territory = territoryKey(normalized);
  return enqueueMapRequest({
    key: `conafor:${query}`,
    channel: "puntos",
    latestKey: `conafor:${territory}`,
    settleMs: 550,
    signal: options.signal,
    request: () => apiFetch(endpoint),
  });
}
