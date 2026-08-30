import * as turf from "@turf/turf";
import polygonClipping from "polygon-clipping";
import { descargarObjetoR2 } from "../../data/storage/r2.js";

const CAPAS_TEMATICAS = new Set([
  "fisiografia",
  "edafologia",
  "hidrografia",
  "uso_suelo_vegetacion",
]);
const CAPAS_TILED = new Set(["edafologia", "uso_suelo_vegetacion"]);
const THEMATIC_SIMPLIFY_TOLERANCE = {
  fisiografia: 0.0015,
  hidrografia: 0.00075,
  edafologia: 0.001,
  uso_suelo_vegetacion: 0.001,
};
const SMALL_CACHE_TTL_MS = 10 * 60 * 1000;
const MAX_SMALL_CACHE_ENTRIES = 8;

const manifestCache = new Map();
const municipioCache = new Map();

function errorHttp(message, statusCode = 400) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

function validarCveEnt(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) throw errorHttp("cve_ent debe tener 2 dígitos");
  return cveEnt;
}

function validarCvegeo(cvegeo) {
  if (cvegeo === undefined || cvegeo === null || cvegeo === "") return null;
  const value = String(cvegeo).trim();
  if (!/^\d{5}$/.test(value)) throw errorHttp("cvegeo debe tener 5 dígitos");
  return value;
}

function parseBbox(value) {
  const parts = String(value || "").split(",").map(Number);
  if (parts.length !== 4 || parts.some((x) => !Number.isFinite(x))) {
    throw errorHttp("bbox debe tener formato minx,miny,maxx,maxy");
  }
  const [minx, miny, maxx, maxy] = parts;
  if (minx >= maxx || miny >= maxy) throw errorHttp("bbox inválido: min debe ser menor que max");
  return parts;
}

function parseGeoJson(buffer, key) {
  try {
    const data = JSON.parse(buffer.toString("utf8"));
    if (data?.type !== "FeatureCollection" || !Array.isArray(data.features)) {
      throw new Error("formato GeoJSON inválido");
    }
    return data;
  } catch (error) {
    throw errorHttp(`No fue posible leer la capa propia ${key}: ${error.message}`, 502);
  }
}

function parseJson(buffer, key) {
  try {
    return JSON.parse(buffer.toString("utf8"));
  } catch (error) {
    throw errorHttp(`No fue posible leer ${key}: ${error.message}`, 502);
  }
}

function cacheGet(cache, key) {
  const item = cache.get(key);
  if (!item) return null;
  if (Date.now() - item.createdAt >= SMALL_CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  cache.delete(key);
  cache.set(key, item);
  return item.value;
}

function cacheSet(cache, key, value) {
  cache.delete(key);
  cache.set(key, { createdAt: Date.now(), value });
  while (cache.size > MAX_SMALL_CACHE_ENTRIES) {
    cache.delete(cache.keys().next().value);
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

function getCvegeo(feature) {
  const props = feature?.properties || {};
  const value = props.cvegeo ?? props.CVEGEO ?? props.cve_geo ?? props.CVE_GEO;
  return value === undefined || value === null ? "" : String(value).trim().padStart(5, "0");
}

async function obtenerMunicipioFeature(cveEnt, cvegeo) {
  if (!cvegeo) return null;
  const key = `${cveEnt}:${cvegeo}`;
  const cached = cacheGet(municipioCache, key);
  if (cached) return cached;

  const objectKey = municipiosKey(cveEnt);
  const data = parseGeoJson(await descargarObjetoR2(objectKey), objectKey);
  const feature = data.features.find((item) => getCvegeo(item) === cvegeo) || null;
  if (!feature) throw errorHttp(`No se encontró la geometría del municipio ${cvegeo}`, 404);
  return cacheSet(municipioCache, key, feature);
}

async function obtenerManifest(capa, cveEnt) {
  const prefix = tiledPrefix(capa, cveEnt);
  const key = `${prefix}/manifest.json`;
  const cached = cacheGet(manifestCache, key);
  if (cached) return cached;
  const manifest = parseJson(await descargarObjetoR2(key), key);
  if (!Array.isArray(manifest?.tiles)) throw errorHttp("manifest de tiles inválido", 502);
  return cacheSet(manifestCache, key, manifest);
}

function bboxIntersects(a, b) {
  return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
}

function bboxIntersection(a, b) {
  if (!bboxIntersects(a, b)) return null;
  return [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.min(a[3], b[3])];
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
  const candidate = geometryBbox(feature?.geometry);
  return candidate ? bboxIntersects(candidate, bbox) : false;
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
    const distance = squaredSegmentDistance(points[i], first, last);
    if (distance > maxSqDistance) {
      index = i;
      maxSqDistance = distance;
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
  if (!geometry?.coordinates || !tolerance) return geometry;
  const { type, coordinates } = geometry;
  if (type === "LineString") return { ...geometry, coordinates: simplifyLine(coordinates, tolerance) };
  if (type === "MultiLineString") return { ...geometry, coordinates: coordinates.map((line) => simplifyLine(line, tolerance)) };
  if (type === "Polygon") return { ...geometry, coordinates: coordinates.map((ring) => simplifyRing(ring, tolerance)) };
  if (type === "MultiPolygon") {
    return { ...geometry, coordinates: coordinates.map((polygon) => polygon.map((ring) => simplifyRing(ring, tolerance))) };
  }
  return geometry;
}

function thematicTolerance(capa, bbox) {
  const base = THEMATIC_SIMPLIFY_TOLERANCE[capa] || 0;
  const span = Math.max(Math.abs(bbox[2] - bbox[0]), Math.abs(bbox[3] - bbox[1]));
  let factor = 0.75;
  if (span >= 4) factor = 3;
  else if (span >= 2) factor = 2.25;
  else if (span >= 1) factor = 1.5;
  else if (span >= 0.5) factor = 1.15;
  return Number((base * factor).toFixed(6));
}

function polygonInput(geometry) {
  if (!geometry?.coordinates) return null;
  if (geometry.type === "Polygon" || geometry.type === "MultiPolygon") return geometry.coordinates;
  return null;
}

function recortarPoligono(feature, mascara) {
  const subject = polygonInput(feature?.geometry);
  const clip = polygonInput(mascara?.geometry);
  if (!subject || !clip) return null;
  try {
    const result = polygonClipping.intersection(subject, clip);
    if (!Array.isArray(result) || result.length === 0) return null;
    return {
      type: "Feature",
      properties: { ...(feature.properties || {}) },
      geometry: result.length === 1
        ? { type: "Polygon", coordinates: result[0] }
        : { type: "MultiPolygon", coordinates: result },
    };
  } catch {
    return null;
  }
}

function midpointInsideSegment(a, b, mascara) {
  try {
    return turf.booleanPointInPolygon(
      turf.point([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]),
      mascara,
      { ignoreBoundary: false },
    );
  } catch {
    return false;
  }
}

function recortarLinea(feature, mascara) {
  const geometry = feature?.geometry;
  const lines = geometry?.type === "LineString"
    ? [geometry.coordinates]
    : geometry?.type === "MultiLineString" ? geometry.coordinates : [];
  const segments = [];
  for (const coords of lines) {
    let current = [];
    for (let i = 0; i < coords.length - 1; i += 1) {
      const a = coords[i];
      const b = coords[i + 1];
      if (midpointInsideSegment(a, b, mascara)) {
        if (!current.length) current.push(a);
        current.push(b);
      } else if (current.length >= 2) {
        segments.push(current);
        current = [];
      } else {
        current = [];
      }
    }
    if (current.length >= 2) segments.push(current);
  }
  if (!segments.length) return null;
  return segments.length === 1
    ? turf.lineString(segments[0], { ...(feature.properties || {}) })
    : turf.multiLineString(segments, { ...(feature.properties || {}) });
}

function recortarFeature(feature, mascara) {
  const type = feature?.geometry?.type;
  if (type === "Polygon" || type === "MultiPolygon") return recortarPoligono(feature, mascara);
  if (type === "LineString" || type === "MultiLineString") return recortarLinea(feature, mascara);
  if (type === "Point") {
    try {
      return turf.booleanPointInPolygon(feature, mascara, { ignoreBoundary: false }) ? feature : null;
    } catch {
      return null;
    }
  }
  return null;
}

function procesarFeature(feature, effectiveBbox, tolerance, municipioFeature) {
  if (!featureIntersectsBbox(feature, effectiveBbox)) return null;
  const simplified = {
    ...feature,
    geometry: simplifyGeometry(feature.geometry, tolerance),
  };
  return municipioFeature ? recortarFeature(simplified, municipioFeature) : simplified;
}

async function procesarObjetoGeoJson(key, effectiveBbox, tolerance, municipioFeature, output) {
  const data = parseGeoJson(await descargarObjetoR2(key), key);
  for (const feature of data.features) {
    const processed = procesarFeature(feature, effectiveBbox, tolerance, municipioFeature);
    if (processed) output.push(processed);
  }
}

export async function obtenerCapaTematicaViewportLigera(capa, cveEntRaw, bboxRaw, cvegeoRaw = null) {
  if (!CAPAS_TEMATICAS.has(capa)) throw errorHttp("capa temática no válida");
  const cveEnt = validarCveEnt(cveEntRaw);
  const cvegeo = validarCvegeo(cvegeoRaw);
  const viewportBbox = parseBbox(bboxRaw);
  const municipioFeature = cvegeo ? await obtenerMunicipioFeature(cveEnt, cvegeo) : null;
  const municipioBbox = municipioFeature ? geometryBbox(municipioFeature.geometry) : null;
  const effectiveBbox = municipioBbox ? bboxIntersection(viewportBbox, municipioBbox) : viewportBbox;

  if (!effectiveBbox) {
    return {
      type: "FeatureCollection",
      features: [],
      metadata: { capa, cve_ent: cveEnt, cvegeo, bbox: viewportBbox, bbox_efectivo: null, recorte: "municipio-exacto-viewport" },
    };
  }

  const tolerance = thematicTolerance(capa, effectiveBbox);
  const features = [];
  const metadata = {};

  if (CAPAS_TILED.has(capa)) {
    const prefix = tiledPrefix(capa, cveEnt);
    const manifest = await obtenerManifest(capa, cveEnt);
    const tiles = manifest.tiles.filter((tile) =>
      Array.isArray(tile.bbox) && tile.bbox.length === 4 && bboxIntersects(tile.bbox, effectiveBbox),
    );

    for (const tile of tiles) {
      await procesarObjetoGeoJson(`${prefix}/${tile.archivo}`, effectiveBbox, tolerance, municipioFeature, features);
    }

    metadata.tiles_usados = tiles.map((tile) => tile.id);
    metadata.cantidad_tiles = tiles.length;
    metadata.tolerancia_origen_m = manifest.tolerancia_m;
    metadata.tile_grados = manifest.tile_grados;
  } else {
    await procesarObjetoGeoJson(tematicaKey(capa, cveEnt), effectiveBbox, tolerance, municipioFeature, features);
  }

  return {
    type: "FeatureCollection",
    features,
    metadata: {
      ...metadata,
      capa,
      cve_ent: cveEnt,
      cvegeo,
      bbox: viewportBbox,
      bbox_efectivo: effectiveBbox,
      features: features.length,
      recorte: municipioFeature ? "municipio-exacto-viewport" : "viewport",
      tolerancia_web_grados: tolerance,
      estrategia_memoria: "stream-por-objeto-sin-cache-de-viewports",
    },
  };
}
