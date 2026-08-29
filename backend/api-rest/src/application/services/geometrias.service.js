import * as turf from "@turf/turf";
import { descargarObjetoR2 } from "../../data/storage/r2.js";

const ESTADOS_KEY = "capas_web/inegi/inegi_entidades.geojson";
const SMN_KEY = "capas_web/smn/smn_estaciones.geojson";
const CACHE_TTL_MS = 10 * 60 * 1000;
const STATE_SIMPLIFY_TOLERANCE = 0.005;
const THEMATIC_SIMPLIFY_TOLERANCE = {
  fisiografia: 0.0015,
  hidrografia: 0.00075,
  edafologia: 0.001,
  uso_suelo_vegetacion: 0.001,
};
const CAPAS_TEMATICAS = new Set([
  "fisiografia",
  "edafologia",
  "hidrografia",
  "uso_suelo_vegetacion",
]);
const CAPAS_TILED = new Set(["edafologia", "uso_suelo_vegetacion"]);

const bufferCache = new Map();
const geojsonCache = new Map();
const responseCache = new Map();
const municipioClipCache = new Map();

function validarCveEnt(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) {
    const error = new Error("cve_ent debe tener 2 dígitos");
    error.statusCode = 400;
    throw error;
  }
}

function validarCvegeo(cvegeo) {
  if (cvegeo === undefined || cvegeo === null || cvegeo === "") return null;
  const value = String(cvegeo).trim();
  if (!/^\d{5}$/.test(value)) {
    const error = new Error("cvegeo debe tener 5 dígitos");
    error.statusCode = 400;
    throw error;
  }
  return value;
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

function cacheGet(map, key) {
  const cached = map.get(key);
  if (!cached) return null;
  if (Date.now() - cached.creadoEn >= CACHE_TTL_MS) {
    map.delete(key);
    return null;
  }
  return cached.value;
}

function cacheSet(map, key, value) {
  map.set(key, { creadoEn: Date.now(), value });
  return value;
}

async function obtenerBufferR2Cache(key) {
  const cached = cacheGet(bufferCache, key);
  if (cached) return cached;

  try {
    const buffer = await descargarObjetoR2(key);
    return cacheSet(bufferCache, key, buffer);
  } catch (error) {
    if (error.statusCode) throw error;
    const wrapped = new Error(`No fue posible obtener ${key} desde R2: ${error.message}`);
    wrapped.statusCode = 502;
    throw wrapped;
  }
}

async function obtenerGeoJsonR2(key) {
  const cached = cacheGet(geojsonCache, key);
  if (cached) return cached;
  const data = parseGeoJson(await obtenerBufferR2Cache(key), key);
  return cacheSet(geojsonCache, key, data);
}

function parseBbox(value) {
  const partes = String(value || "").split(",").map(Number);
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

function bboxIntersection(a, b) {
  if (!bboxIntersects(a, b)) return null;
  return [
    Math.max(a[0], b[0]),
    Math.max(a[1], b[1]),
    Math.min(a[2], b[2]),
    Math.min(a[3], b[3]),
  ];
}

function expandCoordinateBbox(coord, bbox) {
  if (!Array.isArray(coord)) return;
  if (coord.length >= 2 && typeof coord[0] === "number" && typeof coord[1] === "number") {
    const [x, y] = coord;
    if (x < bbox[0]) bbox[0] = x;
    if (y < bbox[1]) bbox[1] = y;
    if (x > bbox[2]) bbox[2] = x;
    if (y > bbox[3]) bbox[3] = y;
    return;
  }
  coord.forEach((child) => expandCoordinateBbox(child, bbox));
}

function geometryBbox(geometry) {
  if (!geometry?.coordinates) return null;
  const bbox = [Infinity, Infinity, -Infinity, -Infinity];
  expandCoordinateBbox(geometry.coordinates, bbox);
  return bbox.every(Number.isFinite) ? bbox : null;
}

function featureIntersectsBbox(feature, bbox) {
  const featureBbox = geometryBbox(feature?.geometry);
  return featureBbox ? bboxIntersects(featureBbox, bbox) : false;
}

function squaredSegmentDistance(point, start, end) {
  let x = start[0];
  let y = start[1];
  let dx = end[0] - x;
  let dy = end[1] - y;

  if (dx !== 0 || dy !== 0) {
    const t = ((point[0] - x) * dx + (point[1] - y) * dy) / (dx * dx + dy * dy);
    if (t > 1) {
      x = end[0];
      y = end[1];
    } else if (t > 0) {
      x += dx * t;
      y += dy * t;
    }
  }

  dx = point[0] - x;
  dy = point[1] - y;
  return dx * dx + dy * dy;
}

function simplifyLine(points, tolerance) {
  if (!Array.isArray(points) || points.length <= 3) return points;
  const sqTolerance = tolerance * tolerance;
  const first = points[0];
  const last = points[points.length - 1];
  let maxSqDistance = sqTolerance;
  let index = -1;

  for (let i = 1; i < points.length - 1; i += 1) {
    const sqDistance = squaredSegmentDistance(points[i], first, last);
    if (sqDistance > maxSqDistance) {
      index = i;
      maxSqDistance = sqDistance;
    }
  }

  if (index === -1) return [first, last];
  const left = simplifyLine(points.slice(0, index + 1), tolerance);
  const right = simplifyLine(points.slice(index), tolerance);
  return left.slice(0, -1).concat(right);
}

function simplifyRing(ring, tolerance) {
  if (!Array.isArray(ring) || ring.length <= 5) return ring;
  const closed = ring[0]?.[0] === ring[ring.length - 1]?.[0] && ring[0]?.[1] === ring[ring.length - 1]?.[1];
  const body = closed ? ring.slice(0, -1) : ring;
  const simplified = simplifyLine(body, tolerance);
  if (simplified.length < 3) return ring;
  return closed ? [...simplified, simplified[0]] : simplified;
}

function simplifyGeometry(geometry, tolerance) {
  if (!geometry?.coordinates) return geometry;
  const { type, coordinates } = geometry;

  if (type === "LineString") {
    return { ...geometry, coordinates: simplifyLine(coordinates, tolerance) };
  }
  if (type === "MultiLineString") {
    return { ...geometry, coordinates: coordinates.map((line) => simplifyLine(line, tolerance)) };
  }
  if (type === "Polygon") {
    return { ...geometry, coordinates: coordinates.map((ring) => simplifyRing(ring, tolerance)) };
  }
  if (type === "MultiPolygon") {
    return {
      ...geometry,
      coordinates: coordinates.map((polygon) => polygon.map((ring) => simplifyRing(ring, tolerance))),
    };
  }
  return geometry;
}

function simplifyFeatureCollection(data, tolerance) {
  return {
    ...data,
    features: data.features.map((feature) => ({
      ...feature,
      geometry: simplifyGeometry(feature.geometry, tolerance),
    })),
  };
}

function simplifyFeatures(features, tolerance) {
  if (!tolerance) return features;
  return features.map((feature) => ({
    ...feature,
    geometry: simplifyGeometry(feature.geometry, tolerance),
  }));
}

function getCvegeo(feature) {
  const props = feature?.properties || {};
  const value = props.cvegeo ?? props.CVEGEO ?? props.cve_geo ?? props.CVE_GEO;
  if (value === undefined || value === null) return "";
  return String(value).trim().padStart(5, "0");
}

async function obtenerMunicipioFeature(cveEnt, cvegeo) {
  if (!cvegeo) return null;
  const municipios = await obtenerGeoJsonR2(municipiosKey(cveEnt));
  return municipios.features.find((item) => getCvegeo(item) === cvegeo) || null;
}

function bboxCacheKey(bbox) {
  return bbox.map((value) => Number(value).toFixed(4)).join(",");
}

function thematicTolerance(capa, bbox) {
  const base = THEMATIC_SIMPLIFY_TOLERANCE[capa] || 0;
  if (!base || !bbox) return base;

  const width = Math.abs(bbox[2] - bbox[0]);
  const height = Math.abs(bbox[3] - bbox[1]);
  const span = Math.max(width, height);

  let factor = 0.75;
  if (span >= 4) factor = 3;
  else if (span >= 2) factor = 2.25;
  else if (span >= 1) factor = 1.5;
  else if (span >= 0.5) factor = 1.15;

  return Number((base * factor).toFixed(6));
}

function limpiarFeature(feature) {
  try {
    return turf.rewind(turf.cleanCoords(feature), { reverse: false });
  } catch {
    return feature;
  }
}

function repararPoligono(feature) {
  const limpio = limpiarFeature(feature);
  try {
    const reparado = turf.buffer(limpio, 0, { units: "meters" });
    return reparado || limpio;
  } catch {
    return limpio;
  }
}

function obtenerFronterasMascara(mascara) {
  const fronteras = [];
  try {
    const boundary = turf.polygonToLine(mascara);
    turf.flattenEach(boundary, (feature) => {
      if (feature?.geometry?.type === "LineString") fronteras.push(feature);
    });
  } catch {
    return [];
  }
  return fronteras;
}

function recortarPoligono(feature, mascara) {
  const limpio = limpiarFeature(feature);

  try {
    if (turf.booleanWithin(limpio, mascara)) return limpio;
    if (turf.booleanDisjoint(limpio, mascara)) return null;
  } catch {
    // Se intenta la intersección aunque las pruebas topológicas fallen
  }

  const candidatos = [limpio, repararPoligono(limpio)];
  for (const candidato of candidatos) {
    try {
      const clipped = turf.intersect(turf.featureCollection([candidato, mascara]));
      if (!clipped) return null;
      return {
        ...clipped,
        properties: { ...(feature.properties || {}) },
      };
    } catch {
      // Se intenta con el siguiente candidato reparado
    }
  }

  return null;
}

function dividirLineaPorFronteras(line, fronteras) {
  let segmentos = [line];

  fronteras.forEach((frontera) => {
    const siguientes = [];
    segmentos.forEach((segmento) => {
      try {
        const partes = turf.lineSplit(segmento, frontera)?.features || [];
        if (partes.length) siguientes.push(...partes);
        else siguientes.push(segmento);
      } catch {
        siguientes.push(segmento);
      }
    });
    segmentos = siguientes;
  });

  return segmentos;
}

function segmentoDentroMascara(segmento, mascara) {
  try {
    const longitudKm = turf.length(segmento, { units: "kilometers" });
    if (!Number.isFinite(longitudKm) || longitudKm <= 0) return false;
    const midpoint = turf.along(segmento, longitudKm / 2, { units: "kilometers" });
    return turf.booleanPointInPolygon(midpoint, mascara, { ignoreBoundary: false });
  } catch {
    return false;
  }
}

function recortarLinea(feature, mascara, fronteras) {
  const geometry = feature?.geometry;
  if (!geometry) return null;

  const lineas = geometry.type === "LineString"
    ? [geometry.coordinates]
    : geometry.type === "MultiLineString"
      ? geometry.coordinates
      : [];

  const segmentos = lineas.flatMap((coordinates) => {
    if (!Array.isArray(coordinates) || coordinates.length < 2) return [];
    const line = turf.lineString(coordinates, { ...(feature.properties || {}) });
    return dividirLineaPorFronteras(line, fronteras).filter((segmento) =>
      segmentoDentroMascara(segmento, mascara),
    );
  });

  if (!segmentos.length) return null;
  if (segmentos.length === 1) {
    return {
      ...segmentos[0],
      properties: { ...(feature.properties || {}) },
    };
  }

  return turf.multiLineString(
    segmentos.map((segmento) => segmento.geometry.coordinates),
    { ...(feature.properties || {}) },
  );
}

function recortarFeature(feature, mascara, fronteras) {
  const type = feature?.geometry?.type;
  if (type === "Polygon" || type === "MultiPolygon") {
    return recortarPoligono(feature, mascara);
  }
  if (type === "LineString" || type === "MultiLineString") {
    return recortarLinea(feature, mascara, fronteras);
  }
  if (type === "Point") {
    try {
      return turf.booleanPointInPolygon(feature, mascara, { ignoreBoundary: false }) ? feature : null;
    } catch {
      return null;
    }
  }
  return null;
}

async function cargarFeaturesMunicipio(capa, cveEnt, municipioBbox) {
  if (CAPAS_TILED.has(capa)) {
    const prefix = tiledPrefix(capa, cveEnt);
    const manifestKey = `${prefix}/manifest.json`;
    const manifest = parseJson(await obtenerBufferR2Cache(manifestKey), manifestKey);

    if (!Array.isArray(manifest?.tiles)) {
      const error = new Error("manifest de tiles inválido");
      error.statusCode = 502;
      throw error;
    }

    const tiles = manifest.tiles.filter((tile) =>
      Array.isArray(tile.bbox) && tile.bbox.length === 4 && bboxIntersects(tile.bbox, municipioBbox),
    );
    const geojsons = await Promise.all(
      tiles.map((tile) => obtenerGeoJsonR2(`${prefix}/${tile.archivo}`)),
    );

    return {
      features: geojsons
        .flatMap((data) => data.features)
        .filter((feature) => featureIntersectsBbox(feature, municipioBbox)),
      metadata: {
        tiles_usados: tiles.map((tile) => tile.id),
        cantidad_tiles: tiles.length,
        tolerancia_origen_m: manifest.tolerancia_m,
        tile_grados: manifest.tile_grados,
      },
    };
  }

  const data = await obtenerGeoJsonR2(tematicaKey(capa, cveEnt));
  return {
    features: data.features.filter((feature) => featureIntersectsBbox(feature, municipioBbox)),
    metadata: {},
  };
}

async function obtenerCapaMunicipioRecortada(capa, cveEnt, municipioFeature) {
  const cvegeo = getCvegeo(municipioFeature);
  const municipioBbox = geometryBbox(municipioFeature.geometry);
  if (!municipioBbox) {
    const error = new Error(`No fue posible determinar el límite del municipio ${cvegeo}`);
    error.statusCode = 502;
    throw error;
  }

  const tolerance = thematicTolerance(capa, municipioBbox);
  const cacheKey = `municipio-clip:${capa}:${cveEnt}:${cvegeo}:${tolerance}`;
  const cached = cacheGet(municipioClipCache, cacheKey);
  if (cached) return cached;

  const mascara = repararPoligono(municipioFeature);
  const fronteras = obtenerFronterasMascara(mascara);
  const source = await cargarFeaturesMunicipio(capa, cveEnt, municipioBbox);
  const simplificadas = simplifyFeatures(source.features, tolerance);
  const recortadas = simplificadas
    .map((feature) => recortarFeature(feature, mascara, fronteras))
    .filter(Boolean);

  return cacheSet(municipioClipCache, cacheKey, {
    type: "FeatureCollection",
    features: recortadas,
    metadata: {
      ...source.metadata,
      capa,
      cve_ent: cveEnt,
      cvegeo,
      bbox_municipio: municipioBbox,
      recorte: "municipio-exacto-cache",
      features_antes_recorte: source.features.length,
      features_recortadas: recortadas.length,
      tolerancia_web_grados: tolerance,
    },
  });
}

export async function obtenerGeometriasEstados({ completo = false } = {}) {
  const data = await obtenerGeoJsonR2(ESTADOS_KEY);
  if (completo) return data;

  const cacheKey = `estados:web:${STATE_SIMPLIFY_TOLERANCE}`;
  const cached = cacheGet(responseCache, cacheKey);
  if (cached) return cached;
  return cacheSet(responseCache, cacheKey, simplifyFeatureCollection(data, STATE_SIMPLIFY_TOLERANCE));
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

export async function obtenerCapaTematicaViewport(capa, cveEnt, bboxRaw, cvegeoRaw = null) {
  if (!CAPAS_TEMATICAS.has(capa)) {
    const error = new Error("capa temática no válida");
    error.statusCode = 400;
    throw error;
  }

  validarCveEnt(cveEnt);
  const cvegeo = validarCvegeo(cvegeoRaw);
  const viewportBbox = parseBbox(bboxRaw);

  if (cvegeo) {
    const municipioFeature = await obtenerMunicipioFeature(cveEnt, cvegeo);
    if (!municipioFeature) {
      const error = new Error(`No se encontró la geometría del municipio ${cvegeo}`);
      error.statusCode = 404;
      throw error;
    }

    const municipioBbox = geometryBbox(municipioFeature.geometry);
    const effectiveBbox = municipioBbox ? bboxIntersection(viewportBbox, municipioBbox) : null;
    if (!effectiveBbox) {
      return {
        type: "FeatureCollection",
        features: [],
        metadata: {
          capa,
          cve_ent: cveEnt,
          cvegeo,
          bbox: viewportBbox,
          bbox_efectivo: null,
          recorte: "municipio-exacto-cache",
        },
      };
    }

    const cacheKey = `viewport-municipio:${capa}:${cveEnt}:${cvegeo}:${bboxCacheKey(effectiveBbox)}`;
    const cached = cacheGet(responseCache, cacheKey);
    if (cached) return cached;

    const capaMunicipio = await obtenerCapaMunicipioRecortada(capa, cveEnt, municipioFeature);
    const features = capaMunicipio.features.filter((feature) =>
      featureIntersectsBbox(feature, effectiveBbox),
    );

    return cacheSet(responseCache, cacheKey, {
      type: "FeatureCollection",
      features,
      metadata: {
        ...capaMunicipio.metadata,
        bbox: viewportBbox,
        bbox_efectivo: effectiveBbox,
        features: features.length,
      },
    });
  }

  const effectiveBbox = viewportBbox;
  const tolerance = thematicTolerance(capa, effectiveBbox);
  const cacheKey = `viewport:${capa}:${cveEnt}:estado:${bboxCacheKey(effectiveBbox)}:${tolerance}`;
  const cached = cacheGet(responseCache, cacheKey);
  if (cached) return cached;

  let features = [];
  let metadata = {};

  if (CAPAS_TILED.has(capa)) {
    const prefix = tiledPrefix(capa, cveEnt);
    const manifestKey = `${prefix}/manifest.json`;
    const manifest = parseJson(await obtenerBufferR2Cache(manifestKey), manifestKey);

    if (!Array.isArray(manifest?.tiles)) {
      const error = new Error("manifest de tiles inválido");
      error.statusCode = 502;
      throw error;
    }

    const tiles = manifest.tiles.filter((tile) =>
      Array.isArray(tile.bbox) && tile.bbox.length === 4 && bboxIntersects(tile.bbox, effectiveBbox),
    );
    const geojsons = await Promise.all(
      tiles.map((tile) => obtenerGeoJsonR2(`${prefix}/${tile.archivo}`)),
    );
    features = geojsons
      .flatMap((data) => data.features)
      .filter((feature) => featureIntersectsBbox(feature, effectiveBbox));
    metadata = {
      tiles_usados: tiles.map((tile) => tile.id),
      cantidad_tiles: tiles.length,
      tolerancia_origen_m: manifest.tolerancia_m,
      tile_grados: manifest.tile_grados,
    };
  } else {
    const data = await obtenerGeoJsonR2(tematicaKey(capa, cveEnt));
    features = data.features.filter((feature) => featureIntersectsBbox(feature, effectiveBbox));
  }

  const simplifiedFeatures = simplifyFeatures(features, tolerance);

  return cacheSet(responseCache, cacheKey, {
    type: "FeatureCollection",
    features: simplifiedFeatures,
    metadata: {
      capa,
      cve_ent: cveEnt,
      cvegeo: null,
      bbox: viewportBbox,
      bbox_efectivo: effectiveBbox,
      features: simplifiedFeatures.length,
      tolerancia_web_grados: tolerance,
      ...metadata,
    },
  });
}
