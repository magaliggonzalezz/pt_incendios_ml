import { parquetRead } from "hyparquet";

import { descargarObjetoR2, obtenerMetadataObjetoR2 } from "../../data/storage/r2.js";

const MUNICIPIO_DIA_2025_KEY =
  "resultados/municipio_dia/app_municipio_dia_resultados_2025.parquet";

function normalizarValor(value) {
  return typeof value === "bigint" ? value.toString() : value;
}

export async function inspeccionarMunicipioDia2025() {
  const inicio = performance.now();
  const metadata = await obtenerMetadataObjetoR2(MUNICIPIO_DIA_2025_KEY);
  const buffer = await descargarObjetoR2(MUNICIPIO_DIA_2025_KEY);
  const descargaFin = performance.now();

  let columnas = [];
  let primeraFila = null;

  await parquetRead({
    file: buffer,
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

  return {
    ok: true,
    advertencia:
      "Prueba piloto: este endpoint todavía descarga el Parquet completo en memoria. No es la estrategia final para archivos grandes.",
    objeto: metadata,
    parquet: {
      columnas,
      numeroColumnas: columnas.length,
      primeraFila,
    },
    tiemposMs: {
      descarga: Math.round(descargaFin - inicio),
      lectura: Math.round(fin - descargaFin),
      total: Math.round(fin - inicio),
    },
  };
}
