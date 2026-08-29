import { apiFetch } from "./api";

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  return search.toString();
}

export function obtenerPuntosFirms(params = {}, options = {}) {
  const query = buildQuery(params);
  return apiFetch(`/api/puntos-mapa/firms${query ? `?${query}` : ""}`, options);
}

export function obtenerIncendiosConafor(params = {}, options = {}) {
  const query = buildQuery(params);
  return apiFetch(`/api/puntos-mapa/conafor${query ? `?${query}` : ""}`, options);
}
