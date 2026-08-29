import { apiFetch } from "./api";

export function obtenerGeometriasEstados(options = {}) {
  return apiFetch("/api/geometrias/estados", options);
}

export function obtenerGeometriasMunicipios(cveEnt, options = {}) {
  if (!cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(`/api/geometrias/municipios?cve_ent=${encodeURIComponent(cveEnt)}`, options);
}

export function obtenerEstacionesSmn(options = {}) {
  return apiFetch("/api/geometrias/smn", options);
}

export function obtenerCapaTematica(capa, cveEnt, options = {}) {
  if (!capa || !cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(
    `/api/geometrias/tematicas/${encodeURIComponent(capa)}?cve_ent=${encodeURIComponent(cveEnt)}`,
    options,
  );
}

export function obtenerCapaTematicaViewport(capa, cveEnt, bbox, options = {}) {
  if (!capa || !cveEnt || !bbox) {
    return Promise.resolve({ type: "FeatureCollection", features: [], metadata: null });
  }

  return apiFetch(
    `/api/geometrias/tematicas/${encodeURIComponent(capa)}/viewport?cve_ent=${encodeURIComponent(cveEnt)}&bbox=${encodeURIComponent(bbox)}`,
    options,
  );
}
