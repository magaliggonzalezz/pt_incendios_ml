import { parquetRead } from "hyparquet";
import { compressors } from "hyparquet-compressors";

import { crearAsyncBufferR2 } from "../../data/storage/r2.js";

const MUNICIPIO_DIA_2025_KEY =
  "resultados/municipio_dia/app_municipio_dia_resultados_2025.parquet";

function normalizarValor(value) {
  return typeof value === "bigint" ? value.toString() : value;
}

export async function inspeccionarMunicipioDia2025() {
  const inicio = performance.now();
  const { file, metadata, obtenerEstadisticas } = await crearAsyncBufferR2(
    MUNICIPIO_DIA_2025_KEY,
  );
  const preparacionFin = performance.now();

  let columnas = [];
  let primeraFila = null;

  await parquetRead({
    file,
    compressors,
    rowStart: 0,
    rowEnd: 1,
    onComplete: (data) => {
      if (!data?.length) {
        return;
      }

      const fila = data[0];
      if (Array.isArray(fila)) {
        columnas = fila.map((_, index) => `col_${index}`);
        primeraFila = Object.fromEntries(
          fila.map((value, index) => [`col_${index}`, normalizarValor(value)]),
        );
      } else {
        columnas = Object.keys(fila);
        primeraFila = Object.fromEntries(
          Object.entries(fila).map(([key, value]) => [key, normalizarValor(value)]),
        );
      }
    },
  });

  const fin = performance.now();
  const estadisticas = obtenerEstadisticas();
  const bytesObjeto = Number(metadata.bytes || 0);
  const porcentajeTransferido = bytesObjeto
    ? (estadisticas.bytesTransferidos / bytesObjeto) * 100
    : null;

  return {
    ok: true,
    estrategia: "lectura remota por rangos HTTP desde R2",
    objeto: metadata,
    parquet: {
      columnas,
      numeroColumnas: columnas.length,
      primeraFila,
    },
    transferencia: {
      solicitudesRange: estadisticas.solicitudesRange,
      bytesTransferidos: estadisticas.bytesTransferidos,
      bytesObjeto,
      porcentajeObjetoTransferido:
        porcentajeTransferido === null
          ? null
          : Number(porcentajeTransferido.toFixed(2)),
    },
    tiemposMs: {
      preparacion: Math.round(preparacionFin - inicio),
      lectura: Math.round(fin - preparacionFin),
      total: Math.round(fin - inicio),
    },
  };
}
