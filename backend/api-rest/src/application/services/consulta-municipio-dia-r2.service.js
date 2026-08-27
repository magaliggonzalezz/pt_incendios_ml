import { parquetRead } from "hyparquet";
import { compressors } from "hyparquet-compressors";

import { crearAsyncBufferR2 } from "../../data/storage/r2.js";

const YEAR_MIN = 2001;
const YEAR_MAX = 2025;

function construirKey(anio) {
  return `resultados/municipio_dia/app_municipio_dia_resultados_${anio}.parquet`;
}

function normalizarValor(value) {
  if (typeof value === "bigint") return value.toString();
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return value;
}

function normalizarFila(fila) {
  return Object.fromEntries(
    Object.entries(fila || {}).map(([key, value]) => [key, normalizarValor(value)]),
  );
}

function normalizarCvegeo(value) {
  return String(value).trim().padStart(5, "0");
}

function normalizarFecha(value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value).slice(0, 10);
}

export async function consultarMunicipioDiaR2({ cvegeo, fecha }) {
  const anio = Number(String(fecha).slice(0, 4));
  if (!Number.isInteger(anio) || anio < YEAR_MIN || anio > YEAR_MAX) {
    const error = new Error(`fecha debe estar entre ${YEAR_MIN}-01-01 y ${YEAR_MAX}-12-31`);
    error.statusCode = 400;
    throw error;
  }

  const key = construirKey(anio);
  const inicio = performance.now();
  const { file, metadata, obtenerEstadisticas } = await crearAsyncBufferR2(key);
  const preparado = performance.now();

  let indiceFila = -1;

  await parquetRead({
    file,
    compressors,
    columns: ["cvegeo", "fecha"],
    rowFormat: "object",
    onComplete: (data) => {
      indiceFila = data.findIndex(
        (fila) =>
          normalizarCvegeo(fila.cvegeo) === cvegeo &&
          normalizarFecha(fila.fecha) === fecha,
      );
    },
  });

  const busquedaFin = performance.now();
  const transferenciaBusqueda = obtenerEstadisticas();

  if (indiceFila < 0) {
    return {
      ok: true,
      encontrado: false,
      consulta: { cvegeo, fecha, anio },
      objeto: metadata,
      transferencia: {
        busqueda: transferenciaBusqueda,
        total: transferenciaBusqueda,
      },
      tiemposMs: {
        preparacion: Math.round(preparado - inicio),
        busqueda: Math.round(busquedaFin - preparado),
        total: Math.round(busquedaFin - inicio),
      },
    };
  }

  let resultado = null;
  await parquetRead({
    file,
    compressors,
    rowStart: indiceFila,
    rowEnd: indiceFila + 1,
    rowFormat: "object",
    onComplete: (data) => {
      resultado = data?.[0] ? normalizarFila(data[0]) : null;
    },
  });

  const fin = performance.now();
  const transferenciaTotal = obtenerEstadisticas();
  const bytesObjeto = Number(metadata.bytes || 0);
  const porcentajeTransferido = bytesObjeto
    ? (transferenciaTotal.bytesTransferidos / bytesObjeto) * 100
    : null;

  return {
    ok: true,
    encontrado: Boolean(resultado),
    estrategia: "R2 + Parquet remoto por rangos HTTP",
    consulta: { cvegeo, fecha, anio },
    indiceFila,
    resultado,
    objeto: metadata,
    transferencia: {
      busqueda: transferenciaBusqueda,
      total: transferenciaTotal,
      bytesObjeto,
      porcentajeObjetoTransferido:
        porcentajeTransferido === null
          ? null
          : Number(porcentajeTransferido.toFixed(2)),
    },
    tiemposMs: {
      preparacion: Math.round(preparado - inicio),
      busqueda: Math.round(busquedaFin - preparado),
      lecturaResultado: Math.round(fin - busquedaFin),
      total: Math.round(fin - inicio),
    },
  };
}
