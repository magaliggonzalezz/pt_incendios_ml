import { parquetReadObjects } from "hyparquet";
import { compressors } from "hyparquet-compressors";

import { crearAsyncBufferR2 } from "../../data/storage/r2.js";

const FIRMS_YEAR_MIN = 2001;
const FIRMS_YEAR_MAX = 2025;
const CONAFOR_KEY = "fuentes/conafor/conafor_incendios_eventos.parquet";
const ROW_CACHE_TTL_MS = 10 * 60 * 1000;
const MAX_PARQUET_CACHE_ENTRIES = 2;

const parquetRowsCache = new Map();
const parquetInFlight = new Map();

const FIRMS_COLUMNS = [
  "latitude", "longitude", "fecha", "acq_date", "acq_time", "satellite",
  "instrument", "confidence", "confidence_category", "version", "brightness",
  "scan", "track", "frp", "daynight", "type", "anio", "estado", "municipio",
  "cve_ent", "cve_mun", "cvegeo",
];

const CONAFOR_COLUMNS = [
  "clave_incendio", "anio", "fecha_inicio", "fecha_termino", "estado", "municipio",
  "cve_ent", "cve_mun", "cvegeo", "latitud", "longitud", "region", "predio",
  "causa", "causa_especifica", "tipo_incendio", "tipo_impacto", "tipo_vegetacion",
  "regimen_fuego", "superficie_total_ha", "superficie_categoria", "arbolado_adulto",
  "arbustivo", "herbaceo", "hojarasca", "renuevo", "duracion", "deteccion", "llegada",
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
  parquetRowsCache.delete(key);
  parquetRowsCache.set(key, cached);
  return cached.value;
}

function setParquetCache(key, value) {
  parquetRowsCache.delete(key);
  parquetRowsCache.set(key, { createdAt: Date.now(), value });
  while (parquetRowsCache.size > MAX_PARQUET_CACHE_ENTRIES) {
    const oldestKey = parquetRowsCache.keys().next().value;
    parquetRowsCache.delete(oldestKey);
  }
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
    setParquetCache(key, value);
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

function crearFirmsFeature(row, fecha, longitude, latitude) {
  return {
    type: "Feature",
    geometry: { type: "Point", coordinates: [longitude, latitude] },
    properties: {
      fecha,
      acq_time: valorJson(row.acq_time),
      estado: valorJson(row.estado),
      municipio: valorJson(row.municipio),
      cve_ent: normalizarCve(row.cve_ent, 2),
      cve_mun: normalizarCve(row.cve_mun, 3),
      cvegeo: normalizarCve(row.cvegeo, 5),
      confidence: valorJson(row.confidence),
      confidence_category: valorJson(row.confidence_category),
      frp: valorJson(row.frp),
      daynight: valorJson(row.daynight),
      satellite: valorJson(row.satellite),
      instrument: valorJson(row.instrument),
      brightness: valorJson(row.brightness),
      type: valorJson(row.type),
      scan: valorJson(row.scan),
      track: valorJson(row.track),
      version: valorJson(row.version),
    },
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
  const features = [];

  for (const row of rows) {
    const fecha = fechaIso(row.fecha ?? row.acq_date);
    if (!coincideTerritorio(row, cveEnt, cvegeo)) continue;
    if (!coincideFecha(fecha, fechaInicio, fechaFin, mes)) continue;
    if (!dentroBbox(row.longitude, row.latitude, bbox)) continue;

    const longitude = Number(row.longitude);
    const latitude = Number(row.latitude);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) continue;

    features.push(crearFirmsFeature(row, fecha, longitude, latitude));
  }

  return featureCollection(features, {
    fuente: "FIRMS",
    anio,
    mes,
    cve_ent: cveEnt,
    cvegeo,
    bbox,
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
    registros: features.length,
    representacion: "detecciones-originales",
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
        fecha_inicio: fecha,
        fecha_termino: fechaIso(row.fecha_termino),
        estado: valorJson(row.estado),
        municipio: valorJson(row.municipio),
        cve_ent: normalizarCve(row.cve_ent, 2),
        cve_mun: normalizarCve(row.cve_mun, 3),
        cvegeo: normalizarCve(row.cvegeo, 5),
        clave_incendio: valorJson(row.clave_incendio),
        superficie_total_ha: valorJson(row.superficie_total_ha),
        tipo_impacto: valorJson(row.tipo_impacto),
        tipo_incendio: valorJson(row.tipo_incendio),
        causa: valorJson(row.causa),
        causa_especifica: valorJson(row.causa_especifica),
        tipo_vegetacion: valorJson(row.tipo_vegetacion),
        regimen_fuego: valorJson(row.regimen_fuego),
        region: valorJson(row.region),
        predio: valorJson(row.predio),
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
