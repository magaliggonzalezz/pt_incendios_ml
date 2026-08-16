import { mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const INEGI_GEO_BASE = "https://gaia.inegi.org.mx/wscatgeo/v2/geo";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const DEFAULT_TIMEOUT_MS = 30000;
const ESTADOS_TIMEOUT_MS = 60000;
const MAX_ATTEMPTS = 2;
const DISK_CACHE_DIR = path.join(os.tmpdir(), "pt_incendios_ml", "geometrias");
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

function validateFeatureCollection(data) {
  return data?.type === "FeatureCollection" && Array.isArray(data?.features);
}

function cacheFileName(cacheKey) {
  return `${cacheKey.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
}

function cacheFilePath(cacheKey) {
  return path.join(DISK_CACHE_DIR, cacheFileName(cacheKey));
}

async function readDiskCache(cacheKey, { allowStale = false } = {}) {
  try {
    const raw = await readFile(cacheFilePath(cacheKey), "utf8");
    const entry = JSON.parse(raw);
    if (!validateFeatureCollection(entry?.data)) return null;

    const age = Date.now() - Number(entry.createdAt || 0);
    if (!allowStale && age > CACHE_TTL_MS) return null;

    setCached(cacheKey, entry.data);
    return entry.data;
  } catch {
    return null;
  }
}

async function writeDiskCache(cacheKey, data) {
  try {
    await mkdir(DISK_CACHE_DIR, { recursive: true });
    await writeFile(
      cacheFilePath(cacheKey),
      JSON.stringify({ createdAt: Date.now(), data }),
      "utf8"
    );
  } catch (error) {
    console.warn(`No se pudo escribir caché de geometría ${cacheKey}: ${error.message}`);
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchOnce(url, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      headers: { Accept: "application/geo+json, application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`INEGI respondió ${response.status}`);
    }

    const data = await response.json();
    if (!validateFeatureCollection(data)) {
      throw new Error("INEGI devolvió una geometría con formato inesperado");
    }

    return data;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchGeoJson(url, cacheKey, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const memoryCached = getCached(cacheKey);
  if (memoryCached) return memoryCached;

  const diskCached = await readDiskCache(cacheKey);
  if (diskCached) return diskCached;

  let lastError = null;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const data = await fetchOnce(url, timeoutMs);
      setCached(cacheKey, data);
      await writeDiskCache(cacheKey, data);
      return data;
    } catch (error) {
      lastError = error;
      if (attempt < MAX_ATTEMPTS) {
        await wait(750 * attempt);
      }
    }
  }

  const staleCached = await readDiskCache(cacheKey, { allowStale: true });
  if (staleCached) {
    console.warn(`INEGI no respondió para ${cacheKey}; usando caché local previa.`);
    return staleCached;
  }

  const reason = lastError?.name === "AbortError"
    ? `INEGI excedió el tiempo de espera de ${Math.round(timeoutMs / 1000)} s`
    : lastError?.message || "error desconocido al consultar INEGI";

  const error = new Error(`No fue posible obtener la geometría de INEGI: ${reason}`);
  error.statusCode = 502;
  throw error;
}

export async function obtenerGeometriasEstados() {
  return fetchGeoJson(`${INEGI_GEO_BASE}/mgee/`, "estados", {
    timeoutMs: ESTADOS_TIMEOUT_MS,
  });
}

export async function obtenerGeometriasMunicipios(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) {
    const error = new Error("cve_ent debe tener 2 dígitos");
    error.statusCode = 400;
    throw error;
  }

  return fetchGeoJson(`${INEGI_GEO_BASE}/mgem/${cveEnt}`, `municipios:${cveEnt}`);
}
