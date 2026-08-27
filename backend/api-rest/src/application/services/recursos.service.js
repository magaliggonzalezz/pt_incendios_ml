const YEAR_MIN = 2001;
const YEAR_MAX = 2025;

function parseYear(value) {
  const year = Number(value);
  if (!Number.isInteger(year) || year < YEAR_MIN || year > YEAR_MAX) {
    const error = new Error(`anio debe ser un entero entre ${YEAR_MIN} y ${YEAR_MAX}`);
    error.statusCode = 400;
    throw error;
  }
  return year;
}

function recursoMunicipioDia(year) {
  return {
    id: "municipio_dia",
    nombre: `Resultados ML municipio-día ${year}`,
    descripcion: "Resultados municipio-día derivados del proyecto.",
    formato: "parquet",
    key: `resultados/municipio_dia/app_municipio_dia_resultados_${year}.parquet`,
    descargable: true,
  };
}

function recursoDetalleExportacion(year) {
  return {
    id: "detalle_exportacion",
    nombre: `Detalle de exportación ML ${year}`,
    descripcion: "Dataset detallado de resultados derivados preparado para exportación.",
    formato: "parquet",
    key: `exportacion/municipio_dia/app_municipio_dia_detalle_exportacion_${year}.parquet`,
    descargable: true,
  };
}

export function obtenerExportacionesPorAnio(anio) {
  const year = parseYear(anio);
  const recursos = [recursoMunicipioDia(year), recursoDetalleExportacion(year)];

  return {
    anio: year,
    periodo: { desde: YEAR_MIN, hasta: YEAR_MAX },
    recursos: recursos.map(({ key, ...recurso }) => ({
      ...recurso,
      endpointDescarga: `/api/recursos/exportaciones/${recurso.id}?anio=${year}`,
    })),
  };
}

export function resolverExportacion({ id, anio }) {
  const year = parseYear(anio);
  const recursos = {
    municipio_dia: recursoMunicipioDia(year),
    detalle_exportacion: recursoDetalleExportacion(year),
  };

  const recurso = recursos[id];
  if (!recurso) {
    const error = new Error("recurso de exportación no válido");
    error.statusCode = 404;
    throw error;
  }

  return recurso;
}

export function obtenerConfiguracionRecursos() {
  return {
    periodo: { desde: YEAR_MIN, hasta: YEAR_MAX },
    almacenamiento: "Cloudflare R2 privado",
    formatosExportacion: ["parquet"],
  };
}
