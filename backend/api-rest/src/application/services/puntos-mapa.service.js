import { parquetReadObjects } from "hyparquet";
import { compressors } from "hyparquet-compressors";

import { crearAsyncBufferR2 } from "../../data/storage/r2.js";

const FIRMS_YEAR_MIN = 2001;
const FIRMS_YEAR_MAX = 2025;
const CONAFOR_KEY = "fuentes/conafor/conafor_incendios_eventos.parquet";
const ROW_CACHE_TTL_MS = 10 * 60 * 1000;
const FIRMS_MAX_POINTS = 4000;

const parquetRowsCache = new Map();
const parquetInFlight = new Map();

const FIRMS_COLUMNS = [
  "latitude",
  "longitude",
  "fecha",
  "acq_date",
  "acq_time",
  "satellite",
  "instrument",
  "confidence",
  "confidence_category",
  "version",
  "brightness",
  "scan",
  "track",
  "frp",
  "daynight",
  "type",
  "anio",
  "estado",
  "municipio",
  "cve_ent",
  "cve_mun",
  "cvegeo",
];

const CONAFOR_COLUMNS = [
  "clave_incendio",
  "anio",
  "fecha_inicio",
  "fecha_termino",
  "estado",
  "municipio",
  "cve_ent",
  "cve_mun",
  "cvegeo",
  "latitud",
  "longitud",
  "region",
  "predio",
  "causa",
  "causa_especifica",
  "tipo_incendio",
  "tipo_impacto",
  "tipo_vegetacion",
  "regimen_fuego",
  "superficie_total_ha",
  "superficie_categoria",
  "arbolado_adulto",
  "arbustivo",
  "herbaceo",
  "hojarasca",
  "renuevo",
  "duracion",
  "deteccion",
  "llegada",
];

function firmsKey(anio) {
  return `capas_web/puntos/firms/firms_detecciones_${anio}.parquet`;
}

function error400(message) {
  const error = new Error(message);
  error.statusCode = 400;
  return error;
}

function validarAnio(value) {
  const anio = Number(value);
  if (!Number.isInteger(anio) || anio < FIRMS_YEAR_MIN || anio > FIRMS_YEAR_MAX) {
    throw error400(`anio debe estar entre ${FIRMS_YEAR_MIN} y ${FIRMS_YEAR_MAX}`);
  }
  return anio;
}

function normalizarCve(value, longitud) {
  if (value === undefined || value === null || value === "") return null;
  const text = String(value).trim();
  if (!/^\d+$/.test(text)) throw error400("clave geográfica inválida");
  return text.padStart(longitud, "0");
}

function valorJson(value) {
  if (typeof value !== "bigint") return value ?? null;
  const number = Number(value);
  return Number.isSafeInteger(number) ? number : value.toString();
}

function parseBbox(value) {
  if (!value) return null;
  const parts = String(value).split(",").map(Number);
  if (parts.length !== 4 || parts.some((x) => !Number.isFinite(x))) {
    throw error400("bbox debe tener formato minx,miny,maxx,maxy");
  }
  const [minx, miny, maxx, maxy] = parts;
  if (minx >= maxx || miny >= maxy) throw error400("bbox inválido");
  return parts;
}

function fechaIso(value) {
  if (value === undefined || value === null || value === "") return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  const text = String(value).trim();
  const match = text.match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : text.slice(0, 10);
}

function validarFecha(value, nombre) {
  if (!value) return null;
  const text = String(value).trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    throw error400(`${nombre} debe tener formato YYYY-MM-DD`);
  }
  return text;
}

function dentroBbox(longitud, latitud, bbox) {
  if (!bbox) return true;
  const lon = Number(longitud);
  const lat = Number(latitud);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return false;
  return lon >= bbox[0] && lon <= bbox[2] && lat >= bbox[1] && lat <= bbox[3];
}

function coincideTerritorio(row, cveEnt, cvegeo) {
  if (cvegeo && normalizarCve(row.cvegeo, 5) !== cvegeo) return false;
  if (cveEnt && normalizarCve(row.cve_ent, 2) !== cveEnt) return false;
  return true;
}

function coincideFecha(fecha, fechaInicio, fechaFin, mes) {
  if (!fecha) return false;
  if (fechaInicio && fecha < fechaInicio) return false;
  if (fechaFin && fecha > fechaFin) return false;
  if (mes && Number(fecha.slice(5, 7)) !== mes) return false;
  return true;
}

function parseMes(value) {
  if (value === undefined || value === null || value === "") return null;
  const mes = Number(value);
  if (!Number.isInteger(mes) || mes < 1 || mes > 12) {
    throw error400("mes debe estar entre 1 y 12");
  }
  return mes;
}

function getParquetCache(key) {
  const cached = parquetRowsCache.get(key);
  if (!cached) return null;
  if (Date.now() - cached.createdAt >= ROW_CACHE_TTL_MS) {
    parquetRowsCache.delete(key);
    return null;
  }
  return cached.value;
}

async function leerParquetR2(key, columns) {
  const cached = getParquetCache(key);
  if (cached) return { ...cached, cache: true };

  const existing = parquetInFlight.get(key);
  if (existing) return existing;

  const promise = (async () => {
    const { file, metadata, obtenerEstadisticas } = await crearAsyncBufferR2(key);
    const rows = await parquetReadObjects({ file, columns, compressors });
    const value = { rows, metadata, estadisticas: obtenerEstadisticas(), cache: false };
    parquetRowsCache.set(key, { createdAt: Date.now(), value });
    return value;
  })();

  parquetInFlight.set(key, promise);
  try {
    return await promise;
  } finally {
    if (parquetInFlight.get(key) === promise) parquetInFlight.delete(key);
  }
}

function featureCollection(features, metadata) {
  return { type: "FeatureCollection", features, metadata };
}

function confidenceRank(value) {
  const category = String(value || "").toLowerCase();
  if (category === "high") return 3;
  if (category === "nominal") return 2;
  if (category === "low") return 1;
  return 0;
}

function aggregateFirms(features, bbox) {
  if (!bbox || features.length <= FIRMS_MAX_POINTS) {
    return { features, aggregated: false, originalCount: features.length };
  }

  const [minx, miny, maxx, maxy] = bbox;
  const width = Math.max(maxx - minx, 1e-9);
  const height = Math.max(maxy - miny, 1e-9);
  const aspect = width / height;
  const cols = Math.max(8, Math.ceil(Math.sqrt(FIRMS_MAX_POINTS * Math.max(aspect, 0.25))));
  const rows = Math.max(8, Math.ceil(FIRMS_MAX_POINTS / cols));
  const cellWidth = width / cols;
  const cellHeight = height / rows;
  const cells = new Map();

  features.forEach((feature) => {
    const [lon, lat] = feature.geometry.coordinates;
    const col = Math.min(cols - 1, Math.max(0, Math.floor((lon - minx) / cellWidth)));
    const row = Math.min(rows - 1, Math.max(0, Math.floor((lat - miny) / cellHeight)));
    const key = `${col}:${row}`;
    const props = feature.properties || {};
    const current = cells.get(key) || {
      count: 0,
      lonSum: 0,
      latSum: 0,
      frpTotal: 0,
      confidenceCategory: "low",
      confidenceRank: 0,
      estado: props.estado || null,
      municipio: props.municipio || null,
      cve_ent: props.cve_ent || null,
      cvegeo: props.cvegeo || null,
      day: 0,
      night: 0,
    };

    current.count += 1;
    current.lonSum += lon;
    current.latSum += lat;
    current.frpTotal += Number(props.frp) || 0;
    const rank = confidenceRank(props.confidence_category);
    if (rank > current.confidenceRank) {
      current.confidenceRank = rank;
      current.confidenceCategory = props.confidence_category || "nominal";
    }
    if (String(props.daynight || "").toUpperCase() === "N") current.night += 1;
    else current.day += 1;
    if (current.municipio !== props.municipio) current.municipio = "Varias ubicaciones";
    if (current.cvegeo !== props.cvegeo) current.cvegeo = null;
    cells.set(key, current);
  });

  const aggregatedFeatures = Array.from(cells.values()).map((cell) => ({
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [cell.lonSum / cell.count, cell.latSum / cell.count],
    },
    properties: {
      agregado: true,
      detecciones: cell.count,
      fecha: null,
      acq_time: null,
      confidence: null,
      confidence_category: cell.confidenceCategory,
      frp: Number(cell.frpTotal.toFixed(2)),
      frp_total: Number(cell.frpTotal.toFixed(2)),
      daynight: cell.night > cell.day ? "N" : "D",
      estado: cell.estado,
      municipio: cell.municipio,
      cve_ent: cell.cve_ent,
      cve_mun: null,
      cvegeo: cell.cvegeo,
    },
  }));

  return {
    features: aggregatedFeatures,
    aggregated: true,
    originalCount: features.length,
  };
}

export async function obtenerFirmsMapa(params = {}) {
  const anio = validarAnio(params.anio);
  const mes = parseMes(params.mes);
  const cveEnt = normalizarCve(params.cve_ent, 2);
  const cvegeo = normalizarCve(params.cvegeo, 5);
  const bbox = parseBbox(params.bbox);
  const fechaInicio = validarFecha(params.fecha_inicio, "fecha_inicio");
  const fechaFin = validarFecha(params.fecha_fin, "fecha_fin");

  if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
    throw error400("fecha_inicio no puede ser posterior a fecha_fin");
  }

  const key = firmsKey(anio);
  const { rows, metadata, estadisticas, cache } = await leerParquetR2(key, FIRMS_COLUMNS);

  const rawFeatures = [];
  for (const row of rows) {
    const fecha = fechaIso(row.fecha ?? row.acq_date);
    if (!coincideTerritorio(row, cveEnt, cvegeo)) continue;
    if (!coincideFecha(fecha, fechaInicio, fechaFin, mes)) continue;
    if (!dentroBbox(row.longitude, row.latitude, bbox)) continue;

    const longitude = Number(row.longitude);
    const latitude = Number(row.latitude);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) continue;

    rawFeatures.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [longitude, latitude] },
      properties: {
        fecha,
        acq_time: valorJson(row.acq_time),
        satellite: valorJson(row.satellite),
        instrument: valorJson(row.instrument),
        confidence: valorJson(row.confidence),
        confidence_category: valorJson(row.confidence_category),
        version: valorJson(row.version),
        brightness: valorJson(row.brightness),
        scan: valorJson(row.scan),
        track: valorJson(row.track),
        frp: valorJson(row.frp),
        daynight: valorJson(row.daynight),
        type: valorJson(row.type),
        estado: valorJson(row.estado),
        municipio: valorJson(row.municipio),
        cve_ent: normalizarCve(row.cve_ent, 2),
        cve_mun: normalizarCve(row.cve_mun, 3),
        cvegeo: normalizarCve(row.cvegeo, 5),
      },
    });
  }

  const aggregated = aggregateFirms(rawFeatures, bbox);

  return featureCollection(aggregated.features, {
    fuente: "FIRMS",
    anio,
    mes,
    cve_ent: cveEnt,
    cvegeo,
    bbox,
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
    registros: aggregated.features.length,
    registros_originales: aggregated.originalCount,
    agregado_espacial: aggregated.aggregated,
    limite_visualizacion: FIRMS_MAX_POINTS,
    cache_parquet: cache,
    r2: {
      key,
      bytes_objeto: valorJson(metadata.bytes),
      solicitudes_range: valorJson(estadisticas.solicitudesRange),
      bytes_transferidos: valorJson(estadisticas.bytesTransferidos),
    },
  });
}

export async function obtenerConaforMapa(params = {}) {
  const anio = validarAnio(params.anio);
  const mes = parseMes(params.mes);
  const cveEnt = normalizarCve(params.cve_ent, 2);
  const cvegeo = normalizarCve(params.cvegeo, 5);
  const bbox = parseBbox(params.bbox);
  const fechaInicio = validarFecha(params.fecha_inicio, "fecha_inicio");
  const fechaFin = validarFecha(params.fecha_fin, "fecha_fin");

  if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
    throw error400("fecha_inicio no puede ser posterior a fecha_fin");
  }

  const { rows, metadata, estadisticas, cache } = await leerParquetR2(CONAFOR_KEY, CONAFOR_COLUMNS);
  const features = [];

  for (const row of rows) {
    if (Number(row.anio) !== anio) continue;
    const fecha = fechaIso(row.fecha_inicio);
    if (!coincideTerritorio(row, cveEnt, cvegeo)) continue;
    if (!coincideFecha(fecha, fechaInicio, fechaFin, mes)) continue;
    if (!dentroBbox(row.longitud, row.latitud, bbox)) continue;

    const longitude = Number(row.longitud);
    const latitude = Number(row.latitud);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) continue;

    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [longitude, latitude] },
      properties: {
        clave_incendio: valorJson(row.clave_incendio),
        fecha_inicio: fecha,
        fecha_termino: fechaIso(row.fecha_termino),
        estado: valorJson(row.estado),
        municipio: valorJson(row.municipio),
        cve_ent: normalizarCve(row.cve_ent, 2),
        cve_mun: normalizarCve(row.cve_mun, 3),
        cvegeo: normalizarCve(row.cvegeo, 5),
        region: valorJson(row.region),
        predio: valorJson(row.predio),
        causa: valorJson(row.causa),
        causa_especifica: valorJson(row.causa_especifica),
        tipo_incendio: valorJson(row.tipo_incendio),
        tipo_impacto: valorJson(row.tipo_impacto),
        tipo_vegetacion: valorJson(row.tipo_vegetacion),
        regimen_fuego: valorJson(row.regimen_fuego),
        superficie_total_ha: valorJson(row.superficie_total_ha),
        superficie_categoria: valorJson(row.superficie_categoria),
        arbolado_adulto: valorJson(row.arbolado_adulto),
        arbustivo: valorJson(row.arbustivo),
        herbaceo: valorJson(row.herbaceo),
        hojarasca: valorJson(row.hojarasca),
        renuevo: valorJson(row.renuevo),
        duracion: valorJson(row.duracion),
        deteccion: valorJson(row.deteccion),
        llegada: valorJson(row.llegada),
      },
    });
  }

  return featureCollection(features, {
    fuente: "CONAFOR",
    anio,
    mes,
    cve_ent: cveEnt,
    cvegeo,
    bbox,
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
    registros: features.length,
    cache_parquet: cache,
    r2: {
      key: CONAFOR_KEY,
      bytes_objeto: valorJson(metadata.bytes),
      solicitudes_range: valorJson(estadisticas.solicitudesRange),
      bytes_transferidos: valorJson(estadisticas.bytesTransferidos),
    },
  });
}
