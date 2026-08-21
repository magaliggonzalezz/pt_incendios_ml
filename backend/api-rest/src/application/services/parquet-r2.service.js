import parquet from "parquetjs-lite";

import { descargarObjetoR2, obtenerMetadataObjetoR2 } from "../../data/storage/r2.js";

const MUNICIPIO_DIA_2025_KEY =
  "resultados/municipio_dia/app_municipio_dia_resultados_2025.parquet";

export async function inspeccionarMunicipioDia2025() {
  const inicio = performance.now();
  const metadata = await obtenerMetadataObjetoR2(MUNICIPIO_DIA_2025_KEY);
  const buffer = await descargarObjetoR2(MUNICIPIO_DIA_2025_KEY);
  const descargaFin = performance.now();

  const reader = await parquet.ParquetReader.openBuffer(buffer);

  try {
    const cursor = reader.getCursor();
    const primeraFila = await cursor.next();
    const columnas = primeraFila ? Object.keys(primeraFila) : [];
    const fin = performance.now();

    return {
      ok: true,
      advertencia:
        "Prueba piloto: este endpoint descarga el Parquet completo en memoria. No es todavía la estrategia final de consulta.",
      objeto: metadata,
      parquet: {
        columnas,
        numeroColumnas: columnas.length,
        primeraFila,
      },
      tiemposMs: {
        descarga: Math.round(descargaFin - inicio),
        total: Math.round(fin - inicio),
      },
    };
  } finally {
    await reader.close();
  }
}
