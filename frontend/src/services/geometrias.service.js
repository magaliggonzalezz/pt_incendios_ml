import { apiFetch } from "./api";

export function obtenerGeometriasEstados() {
  return apiFetch("/api/geometrias/estados");
}

export function obtenerGeometriasMunicipios(cveEnt) {
  if (!cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(`/api/geometrias/municipios?cve_ent=${encodeURIComponent(cveEnt)}`);
}
