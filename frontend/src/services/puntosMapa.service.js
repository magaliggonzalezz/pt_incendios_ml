import { apiFetch } from "./api";
import { enqueueMapRequest, normalizeBbox } from "./mapRequestQueue";

let periodScope = {};

export function setPuntosMapaPeriodo(scope = {}) {
  periodScope = {
    tipoPeriodo: scope?.tipoPeriodo || "",
    anio: scope?.anio || "",
    mes: scope?.mes || "",
    fechaInicio: scope?.fechaInicio || "",
    fechaFin: scope?.fechaFin || "",
  };
}

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
  return `${params.cve_ent || "mx"}:${params.cvegeo || "all"}:${params.anio || "sin-anio"}:${params.mes || "all"}:${params.fecha_inicio || "sin-inicio"}:${params.fecha_fin || "sin-fin"}`;
}

function expandPeriodParams(params = {}) {
  const base = normalizePointParams(params);

  if (periodScope.tipoPeriodo === "fecha" && periodScope.fechaInicio) {
    return [{
      ...base,
      anio: periodScope.fechaInicio.slice(0, 4),
      mes: undefined,
      fecha_inicio: periodScope.fechaInicio,
      fecha_fin: periodScope.fechaInicio,
    }];
  }

  if (periodScope.tipoPeriodo === "rango_fechas" && periodScope.fechaInicio && periodScope.fechaFin) {
    const startYear = Number(periodScope.fechaInicio.slice(0, 4));
    const endYear = Number(periodScope.fechaFin.slice(0, 4));
    if (!Number.isInteger(startYear) || !Number.isInteger(endYear) || endYear < startYear) return [base];

    return Array.from({ length: endYear - startYear + 1 }, (_, index) => {
      const year = startYear + index;
      return {
        ...base,
        anio: String(year),
        mes: undefined,
        fecha_inicio: year === startYear ? periodScope.fechaInicio : `${year}-01-01`,
        fecha_fin: year === endYear ? periodScope.fechaFin : `${year}-12-31`,
      };
    });
  }

  return [base];
}

function mergeCollections(collections = []) {
  if (collections.length === 1) return collections[0];
  const features = collections.flatMap((collection) => collection?.features || []);
  return {
    type: "FeatureCollection",
    features,
    metadata: {
      registros: features.length,
      periodos: collections.map((collection) => collection?.metadata).filter(Boolean),
    },
  };
}

async function obtenerPuntos(endpointBase, queuePrefix, params = {}, options = {}) {
  const requests = expandPeriodParams(params);
  const collections = await Promise.all(requests.map((normalized) => {
    const query = buildQuery(normalized);
    const endpoint = `${endpointBase}${query ? `?${query}` : ""}`;
    const territory = territoryKey(normalized);
    return enqueueMapRequest({
      key: `${queuePrefix}:${query}`,
      channel: "map-heavy",
      latestKey: `${queuePrefix}:${territory}`,
      settleMs: 500,
      signal: options.signal,
      request: () => apiFetch(endpoint),
    });
  }));
  return mergeCollections(collections);
}

export function obtenerPuntosFirms(params = {}, options = {}) {
  return obtenerPuntos("/api/puntos-mapa/firms", "firms", params, options);
}

export function obtenerIncendiosConafor(params = {}, options = {}) {
  return obtenerPuntos("/api/puntos-mapa/conafor", "conafor", params, options);
}
