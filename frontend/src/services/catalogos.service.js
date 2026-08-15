import { apiFetch } from "./api";

export function obtenerClusters() {
  return apiFetch("/api/catalogos/clusters");
}

export function obtenerEstados() {
  return apiFetch("/api/catalogos/estados");
}

export function obtenerMunicipios(cveEnt) {
  const query = cveEnt ? `?cve_ent=${encodeURIComponent(cveEnt)}` : "";
  return apiFetch(`/api/catalogos/municipios${query}`);
}
