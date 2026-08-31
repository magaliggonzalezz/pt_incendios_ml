const sum = (rows, field) => rows.reduce((total, row) => total + Number(row?.[field] || 0), 0);

function getPeriodoLabel(consulta) {
  if (consulta.tipoPeriodo === "anio_mes") return `${String(consulta.mes).padStart(2, "0")}/${consulta.anio}`;
  if (consulta.tipoPeriodo === "comparar_anios") return `${consulta.anioInicio} vs ${consulta.anioFin}`;
  if (consulta.tipoPeriodo === "fecha") return String(consulta.fechaInicio || "");
  if (consulta.tipoPeriodo === "rango_fechas") return `${consulta.fechaInicio || ""} a ${consulta.fechaFin || ""}`;
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

function clusterMetaById(clusters = []) {
  return new Map(clusters.map((row) => [Number(row.cluster), row]));
}

function decorateRow(row, { clusters, estados, municipios }) {
  const clusterMap = clusterMetaById(clusters);
  const meta = clusterMap.get(Number(row.cluster)) ?? {};
  const estado = (estados || []).find((item) => item.cve_ent === row.cve_ent);
  const municipio = (municipios || []).find((item) => item.cvegeo === row.cvegeo);

  return {
    ...row,
    cluster_som_k07: row.cluster,
    cluster_id: row.cluster,
    estado_app: meta.estado_app,
    etiqueta_final: meta.etiqueta_final,
    color_sugerido_app: meta.color,
    prioridad_visual_app: meta.prioridad_visual,
    nombre_entidad: estado?.nombre,
    nombre_municipio: municipio?.nombre,
    n_observaciones: Number(row.observaciones || 0),
    dias: Number(row.observaciones || 0),
    firms_detection_count_total: Number(row.firms_detecciones || 0),
    firms_frp_total: Number(row.firms_frp || 0),
    conafor_event_count_total: Number(row.conafor_eventos || 0),
    conafor_total_hectareas_total: Number(row.conafor_ha || 0),
    precipitacion_mm_promedio: row.precip_mm,
    temperatura_minima_c_promedio: row.temp_min_c,
    temperatura_maxima_c_promedio: row.temp_max_c,
  };
}

function buildSummaryRows(rows, clusters) {
  const metaMap = clusterMetaById(clusters);
  const grouped = new Map();
  rows.forEach((row) => {
    const clusterId = Number(row.cluster);
    const current = grouped.get(clusterId) ?? {
      cluster_som_k07: clusterId,
      cluster_id: clusterId,
      n_observaciones: 0,
      dias: 0,
      dias_con_firms: 0,
      dias_con_conafor: 0,
      dias_con_smn: 0,
      firms_detection_count_total: 0,
      conafor_event_count_total: 0,
      conafor_total_hectareas_total: 0,
    };
    current.n_observaciones += Number(row.observaciones || 0);
    current.dias += Number(row.observaciones || 0);
    current.dias_con_firms += Number(row.dias_firms || 0);
    current.dias_con_conafor += Number(row.dias_conafor || 0);
    current.dias_con_smn += Number(row.dias_smn || 0);
    current.firms_detection_count_total += Number(row.firms_detecciones || 0);
    current.conafor_event_count_total += Number(row.conafor_eventos || 0);
    current.conafor_total_hectareas_total += Number(row.conafor_ha || 0);
    grouped.set(clusterId, current);
  });

  return Array.from(grouped.values()).map((row) => {
    const meta = metaMap.get(Number(row.cluster_id)) ?? {};
    return {
      ...row,
      estado_app: meta.estado_app,
      etiqueta_final: meta.etiqueta_final,
      color_sugerido_app: meta.color,
      prioridad_visual_app: meta.prioridad_visual,
    };
  });
}

function buildCatalogRows(clusters = []) {
  return clusters.map((cluster) => ({
    cluster_som_k07: cluster.cluster,
    cluster_id: cluster.cluster,
    estado_app: cluster.estado_app,
    etiqueta_final: cluster.etiqueta_final,
    color_sugerido_app: cluster.color,
    prioridad_visual_app: cluster.prioridad_visual,
  }));
}

function temporalRow(label, year, rows) {
  return {
    anio: Number(year),
    label,
    observaciones: sum(rows, "observaciones"),
    firms_detection_count_total: sum(rows, "firms_detecciones"),
    firms_frp_total: sum(rows, "firms_frp"),
    conafor_event_count_total: sum(rows, "conafor_eventos"),
    conafor_total_hectareas_total: sum(rows, "conafor_ha"),
  };
}

function buildTemporalRows(consulta, rows) {
  if (!rows.length) return [];
  if (consulta.tipoPeriodo === "anio_mes") {
    return [{
      anio: Number(consulta.anio),
      mes: Number(consulta.mes),
      label: `${String(consulta.mes).padStart(2, "0")}/${consulta.anio}`,
      firms_detection_count_total: sum(rows, "firms_detecciones"),
      firms_frp_total: sum(rows, "firms_frp"),
      conafor_event_count_total: sum(rows, "conafor_eventos"),
      conafor_total_hectareas_total: sum(rows, "conafor_ha"),
    }];
  }
  if (consulta.tipoPeriodo === "comparar_anios") {
    const yearA = rows.filter((row) => Number(row.anio_comparacion) === Number(consulta.anioInicio));
    const yearB = rows.filter((row) => Number(row.anio_comparacion) === Number(consulta.anioFin));
    return [
      temporalRow(String(consulta.anioInicio), consulta.anioInicio, yearA),
      temporalRow(String(consulta.anioFin), consulta.anioFin, yearB),
    ];
  }
  return [];
}

export function buildRealDashboardResults({ consulta, rows, clusters, estados, municipios }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const clusterId = getDominantCluster(safeRows);
  const cluster = (clusters || []).find((item) => Number(item.cluster) === Number(clusterId));
  const estado = (estados || []).find((item) => item.cve_ent === consulta.cveEnt);
  const municipio = (municipios || []).find((item) => item.cvegeo === consulta.cvegeo);
  const decoratedRows = safeRows.map((row) => decorateRow(row, { clusters, estados, municipios }));
  const summaryRows = buildSummaryRows(safeRows, clusters);

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
    clusterId,
    resultadoMl: cluster ? {
      cluster_id: cluster.cluster,
      cluster_som_k07: cluster.cluster,
      estado_app: cluster.estado_app,
      etiqueta_final: cluster.etiqueta_final,
      color_sugerido_app: cluster.color,
      prioridad_visual_app: cluster.prioridad_visual,
    } : null,
    summaryRows,
    catalogRows: buildCatalogRows(clusters),
    topRows: decoratedRows,
    scatterRows: decoratedRows,
    temporalRows: buildTemporalRows(consulta, safeRows),
    rows: decoratedRows,
    exportRows: decoratedRows,
    exportColumns: safeRows.length ? Object.keys(safeRows[0]) : [],
    totalRecords: safeRows.length,
  };
}
