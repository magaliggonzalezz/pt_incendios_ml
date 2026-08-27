import { descargarObjetoR2 } from "../../data/storage/r2.js";

const ESTADOS_KEY = "capas_web/inegi/inegi_entidades.geojson";

function municipiosKey(cveEnt) {
  return `capas_web/inegi/municipios/inegi_municipios_${cveEnt}.geojson`;
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

async function obtenerGeoJsonR2(key) {
  try {
    const buffer = await descargarObjetoR2(key);
    return parseGeoJson(buffer, key);
  } catch (error) {
    if (error.statusCode) throw error;

    const wrapped = new Error(`No fue posible obtener la capa propia ${key} desde R2: ${error.message}`);
    wrapped.statusCode = 502;
    throw wrapped;
  }
}

export async function obtenerGeometriasEstados() {
  return obtenerGeoJsonR2(ESTADOS_KEY);
}

export async function obtenerGeometriasMunicipios(cveEnt) {
  if (!/^\d{2}$/.test(cveEnt || "")) {
    const error = new Error("cve_ent debe tener 2 dígitos");
    error.statusCode = 400;
    throw error;
  }

  return obtenerGeoJsonR2(municipiosKey(cveEnt));
}
