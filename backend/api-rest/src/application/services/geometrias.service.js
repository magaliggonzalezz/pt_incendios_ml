import { descargarObjetoR2 } from "../../data/storage/r2.js";

const ESTADOS_KEY = "capas_web/inegi/inegi_entidades.geojson";
const SMN_KEY = "capas_web/smn/smn_estaciones.geojson";
const CACHE_TTL_MS = 10 * 60 * 1000;
const CAPAS_TEMATICAS = new Set([
  "fisiografia",
  "edafologia",
  "hidrografia",
  "uso_suelo_vegetacion",
]);
const CAPAS_TILED = new Set(["edafologia", "uso_suelo_vegetacion"]);

const cache = new Map();

function validarCveEnt(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) {
    const error = new Error("cve_ent debe tener 2 dígitos");
    error.statusCode = 400;
    throw error;
  }
}

function municipiosKey(cveEnt) {
  return `capas_web/inegi/municipios/inegi_municipios_${cveEnt}.geojson`;
}

function tematicaKey(capa, cveEnt) {
  return `capas_web/inegi/tematicas/${capa}/${capa}_${cveEnt}.geojson`;
}

function tiledPrefix(capa, cveEnt) {
  return `capas_web/inegi/tiles/${capa}/${cveEnt}`;
}

function parseGeoJson(buffer, key) {
  try {
    const data = JSON.parse(buffer.toString("utf8"));
    if (data?.type !== "FeatureCollection" || !Array.isArray(data?.features)) {
      throw new Error("formato GeoJSON inválido");
    }
    return data;
  } catch (error) {
    const wrapped = new Error(`No fue posible leer la capa propia ${key}: ${error.message}`);
    wrapped.statusCode = 502;
    throw wrapped;
  }
}

function parseJson(buffer, key) {
  try {
    return JSON.parse(buffer.toString("utf8"));
  } catch (error) {
    const wrapped = new Error(`No fue posible leer ${key}: ${error.message}`);
    wrapped.statusCode = 502;
    throw wrapped;
  }
}

async function obtenerBufferR2Cache(key) {
  const ahora = Date.now();
  const cacheado = cache.get(key);
  if (cacheado && ahora - cacheado.creadoEn < CACHE_TTL_MS) {
    return cacheado.buffer;
  }

  try {
    const buffer = await descargarObjetoR2(key);
    cache.set(key, { creadoEn: ahora, buffer });
    return buffer;
  } catch (error) {
    if (error.statusCode) throw error;
    const wrapped = new Error(`No fue posible obtener ${key} desde R2: ${error.message}`);
    wrapped.statusCode = 502;
    throw wrapped;
  }
}

async function obtenerGeoJsonR2(key) {
  return parseGeoJson(await obtenerBufferR2Cache(key), key);
}

function parseBbox(value) {
  const partes = String(value || "")
    .split(",")
    .map(Number);
  if (partes.length !== 4 || partes.some((x) => !Number.isFinite(x))) {
    const error = new Error("bbox debe tener formato minx,miny,maxx,maxy");
    error.statusCode = 400;
    throw error;
  }

  const [minx, miny, maxx, maxy] = partes;
  if (minx >= maxx || miny >= maxy) {
    const error = new Error("bbox inválido: min debe ser menor que max");
    error.statusCode = 400;
    throw error;
  }
  return [minx, miny, maxx, maxy];
}

function bboxIntersects(a, b) {
  return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
}

export async function obtenerGeometriasEstados() {
  return obtenerGeoJsonR2(ESTADOS_KEY);
}

export async function obtenerGeometriasMunicipios(cveEnt) {
  validarCveEnt(cveEnt);
  return obtenerGeoJsonR2(municipiosKey(cveEnt));
}

export async function obtenerEstacionesSmn() {
  return obtenerGeoJsonR2(SMN_KEY);
}

export async function obtenerCapaTematica(capa, cveEnt) {
  if (!CAPAS_TEMATICAS.has(capa)) {
    const error = new Error("capa temática no válida");
    error.statusCode = 400;
    throw error;
  }

  validarCveEnt(cveEnt);
  return obtenerGeoJsonR2(tematicaKey(capa, cveEnt));
}

export async function obtenerCapaTematicaViewport(capa, cveEnt, bboxRaw) {
  if (!CAPAS_TILED.has(capa)) {
    const error = new Error("la capa no está configurada para consulta por viewport");
    error.statusCode = 400;
    throw error;
  }

  validarCveEnt(cveEnt);
  const bbox = parseBbox(bboxRaw);
  const prefix = tiledPrefix(capa, cveEnt);
  const manifestKey = `${prefix}/manifest.json`;
  const manifest = parseJson(await obtenerBufferR2Cache(manifestKey), manifestKey);

  if (!Array.isArray(manifest?.tiles)) {
    const error = new Error("manifest de tiles inválido");
    error.statusCode = 502;
    throw error;
  }

  const tiles = manifest.tiles.filter((tile) =>
    Array.isArray(tile.bbox) && tile.bbox.length === 4 && bboxIntersects(tile.bbox, bbox),
  );

  const geojsons = await Promise.all(
    tiles.map((tile) => obtenerGeoJsonR2(`${prefix}/${tile.archivo}`)),
  );

  return {
    type: "FeatureCollection",
    features: geojsons.flatMap((data) => data.features),
    metadata: {
      capa,
      cve_ent: cveEnt,
      bbox,
      tiles_usados: tiles.map((tile) => tile.id),
      cantidad_tiles: tiles.length,
      tolerancia_m: manifest.tolerancia_m,
      tile_grados: manifest.tile_grados,
    },
  };
}
