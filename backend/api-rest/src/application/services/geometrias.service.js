const INEGI_GEO_BASE = "https://gaia.inegi.org.mx/wscatgeo/v2/geo";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const cache = new Map();

function getCached(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.createdAt > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCached(key, data) {
  cache.set(key, { data, createdAt: Date.now() });
  return data;
}

async function fetchGeoJson(url, cacheKey) {
  const cached = getCached(cacheKey);
  if (cached) return cached;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      headers: { Accept: "application/geo+json, application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`INEGI respondió ${response.status}`);
    }

    const data = await response.json();
    if (data?.type !== "FeatureCollection" || !Array.isArray(data?.features)) {
      throw new Error("INEGI devolvió una geometría con formato inesperado");
    }

    return setCached(cacheKey, data);
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function obtenerGeometriasEstados() {
  return fetchGeoJson(`${INEGI_GEO_BASE}/mgee/`, "estados");
}

export async function obtenerGeometriasMunicipios(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) {
    const error = new Error("cve_ent debe tener 2 dígitos");
    error.statusCode = 400;
    throw error;
  }

  return fetchGeoJson(`${INEGI_GEO_BASE}/mgem/${cveEnt}`, `municipios:${cveEnt}`);
}
