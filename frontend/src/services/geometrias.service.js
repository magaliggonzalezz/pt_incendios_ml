import { apiFetch } from "./api";

export function obtenerGeometriasEstados() {
  return apiFetch("/api/geometrias/estados");
}

export function obtenerGeometriasMunicipios(cveEnt) {
  if (!cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(`/api/geometrias/municipios?cve_ent=${encodeURIComponent(cveEnt)}`);
}

export function obtenerEstacionesSmn() {
  return apiFetch("/api/geometrias/smn");
}

export function obtenerCapaTematica(capa, cveEnt) {
  if (!capa || !cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(
    `/api/geometrias/tematicas/${encodeURIComponent(capa)}?cve_ent=${encodeURIComponent(cveEnt)}`,
  );
}

export function obtenerCapaTematicaViewport(capa, cveEnt, bbox) {
  if (!capa || !cveEnt || !bbox) {
    return Promise.resolve({ type: "FeatureCollection", features: [], metadata: null });
  }

  return apiFetch(
    `/api/geometrias/tematicas/${encodeURIComponent(capa)}/viewport?cve_ent=${encodeURIComponent(cveEnt)}&bbox=${encodeURIComponent(bbox)}`,
  );
}
