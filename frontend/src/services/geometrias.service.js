import { apiFetch } from "./api";
import { enqueueMapRequest, normalizeBbox } from "./mapRequestQueue";

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

export function obtenerCapaTematicaViewport(capa, cveEnt, bbox, cvegeoOrOptions = "", options = {}) {
  if (!capa || !cveEnt || !bbox) {
    return Promise.resolve({ type: "FeatureCollection", features: [], metadata: null });
  }

  const cvegeo = typeof cvegeoOrOptions === "string" ? cvegeoOrOptions : "";
  const fetchOptions = typeof cvegeoOrOptions === "object" && cvegeoOrOptions !== null
    ? cvegeoOrOptions
    : options;
  const normalizedBbox = normalizeBbox(bbox);

  const search = new URLSearchParams({
    cve_ent: String(cveEnt),
    bbox: normalizedBbox,
  });
  if (cvegeo) search.set("cvegeo", String(cvegeo));

  const endpoint = `/api/geometrias/tematicas/${encodeURIComponent(capa)}/viewport?${search.toString()}`;
  const key = `tematica:${capa}:${cveEnt}:${cvegeo || "estado"}:${normalizedBbox}`;

  return enqueueMapRequest({
    key,
    channel: "geometrias",
    signal: fetchOptions.signal,
    request: () => apiFetch(endpoint),
  });
}
