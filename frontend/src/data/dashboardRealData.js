const sum = (rows, field) => rows.reduce((total, row) => total + Number(row?.[field] || 0), 0);

function getPeriodoLabel(consulta) {
  if (consulta.tipoPeriodo === "anio_mes") return `${String(consulta.mes).padStart(2, "0")}/${consulta.anio}`;
  return String(consulta.anio || "");
}

function getDominantCluster(rows) {
  const totals = new Map();
  rows.forEach((row) => {
    const id = Number(row.cluster);
    totals.set(id, (totals.get(id) || 0) + Number(row.observaciones || 0));
  });
  let selected = null;
  let max = -1;
  totals.forEach((value, id) => {
    if (value > max) {
      selected = id;
      max = value;
    }
  });
  return selected;
}

export function buildRealDashboardResults({ consulta, rows, clusters, estados, municipios }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const clusterId = getDominantCluster(safeRows);
  const cluster = (clusters || []).find((item) => Number(item.cluster) === Number(clusterId));
  const estado = (estados || []).find((item) => item.cve_ent === consulta.cveEnt);
  const municipio = (municipios || []).find((item) => item.cvegeo === consulta.cvegeo);

  return {
    fuente: "api-v2",
    nivelAgregacion: consulta.nivelAgregacion,
    periodo: getPeriodoLabel(consulta),
    territorio: municipio?.nombre || estado?.nombre || (consulta.nivelAgregacion === "municipio" ? "Municipios seleccionados" : "México"),
    observaciones: sum(safeRows, "observaciones"),
    dias_incendio: sum(safeRows, "dias_incendio"),
    dias_extremo: sum(safeRows, "dias_extremo"),
    conafor_eventos: sum(safeRows, "conafor_eventos"),
    conafor_ha: sum(safeRows, "conafor_ha"),
    firms_detecciones: sum(safeRows, "firms_detecciones"),
    firms_frp: sum(safeRows, "firms_frp"),
    resultadoMl: cluster ? {
      cluster_id: cluster.cluster,
      estado_app: cluster.estado_app,
      etiqueta_final: cluster.etiqueta_final,
      color_sugerido_app: cluster.color,
      prioridad_visual_app: cluster.prioridad_visual,
    } : null,
    rows: safeRows,
    exportRows: safeRows,
    exportColumns: safeRows.length ? Object.keys(safeRows[0]) : [],
    totalRecords: safeRows.length,
  };
}
