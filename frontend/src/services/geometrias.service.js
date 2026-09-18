import { apiFetch } from "./api";
import { enqueueMapRequest, normalizeBbox } from "./mapRequestQueue";

export function obtenerGeometriasEstados(options = {}) {
  return apiFetch("/api/geometrias/estados", options);
}

export function obtenerGeometriasMunicipios(cveEnt, options = {}) {
  if (!cveEnt) return Promise.resolve({ type: "FeatureCollection", features: [] });
  return apiFetch(`/api/geometrias/municipios?cve_ent=${encodeURIComponent(cveEnt)}`, options);
}

export function obtenerGeometriasMunicipiosViewport(bbox, cveEnt = "", options = {}) {
  if (!bbox) return Promise.resolve({ type: "FeatureCollection", features: [], metadata: null });
  const normalizedBbox = normalizeBbox(bbox);
  const search = new URLSearchParams({ bbox: normalizedBbox });
  if (cveEnt) search.set("cve_ent", String(cveEnt));

  const territory = cveEnt || "mx";
  const endpoint = `/api/geometrias/municipios/viewport?${search.toString()}`;
  const key = `municipios:${territory}:${normalizedBbox}`;

  return enqueueMapRequest({
    key,
    channel: "map-heavy",
    latestKey: `municipios:${territory}`,
    settleMs: 350,
    signal: options.signal,
    request: () => apiFetch(endpoint),
  });
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
  if (!capa || !bbox) {
    return Promise.resolve({ type: "FeatureCollection", features: [], metadata: null });
  }

  const cvegeo = typeof cvegeoOrOptions === "string" ? cvegeoOrOptions : "";
  const fetchOptions = typeof cvegeoOrOptions === "object" && cvegeoOrOptions !== null
    ? cvegeoOrOptions
    : options;
  const normalizedBbox = normalizeBbox(bbox);

  const search = new URLSearchParams({ bbox: normalizedBbox });
  if (cveEnt) search.set("cve_ent", String(cveEnt));
  if (cvegeo) search.set("cvegeo", String(cvegeo));

  const endpoint = `/api/geometrias/tematicas/${encodeURIComponent(capa)}/viewport?${search.toString()}`;
  const territory = `${cveEnt || "mx"}:${cvegeo || (cveEnt ? "estado" : "nacional")}`;
  const key = `tematica:${capa}:${territory}:${normalizedBbox}`;

  return enqueueMapRequest({
    key,
    channel: "map-heavy",
    latestKey: `tematica:${capa}:${territory}`,
    settleMs: 500,
    signal: fetchOptions.signal,
    request: () => apiFetch(endpoint),
  });
}
