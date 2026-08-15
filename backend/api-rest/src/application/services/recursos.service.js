import { env } from "../../config/env.js";

const YEAR_MIN = 2001;
const YEAR_MAX = 2025;

function normalizeBaseUrl(url) {
  return String(url || "").trim().replace(/\/+$/, "");
}

function buildAssetUrl(relativePath) {
  const baseUrl = normalizeBaseUrl(env.assetsBaseUrl);
  return baseUrl ? `${baseUrl}/${relativePath}` : null;
}

function parseYear(value) {
  const year = Number(value);
  if (!Number.isInteger(year) || year < YEAR_MIN || year > YEAR_MAX) {
    const error = new Error(`anio debe ser un entero entre ${YEAR_MIN} y ${YEAR_MAX}`);
    error.statusCode = 400;
    throw error;
  }
  return year;
}

export function obtenerExportacionesPorAnio(anio) {
  const year = parseYear(anio);

  const municipioDiaPath = `ml/csv/municipio_dia/app_municipio_dia_resultados_${year}.csv`;
  const detallePath = `ml/csv/exportacion/app_municipio_dia_detalle_exportacion_${year}.csv`;

  return {
    anio: year,
    almacenamientoConfigurado: Boolean(normalizeBaseUrl(env.assetsBaseUrl)),
    recursos: [
      {
        id: "municipio_dia",
        nombre: `Resultados ML municipio-día ${year}`,
        descripcion: "Dataset municipio-día preparado para consumo y análisis.",
        formato: "csv",
        ruta: municipioDiaPath,
        url: buildAssetUrl(municipioDiaPath),
      },
      {
        id: "detalle_exportacion",
        nombre: `Detalle de exportación ML ${year}`,
        descripcion: "Dataset detallado de exportación preparado por eval05.",
        formato: "csv",
        ruta: detallePath,
        url: buildAssetUrl(detallePath),
      },
    ],
  };
}

export function obtenerConfiguracionRecursos() {
  return {
    almacenamientoConfigurado: Boolean(normalizeBaseUrl(env.assetsBaseUrl)),
    periodo: { desde: YEAR_MIN, hasta: YEAR_MAX },
    baseUrlPublica: normalizeBaseUrl(env.assetsBaseUrl) || null,
  };
}
