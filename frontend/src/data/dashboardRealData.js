const sum = (rows, field) => rows.reduce((total, row) => total + Number(row?.[field] || 0), 0);

const observationWeight = (row) => (
  row?.observaciones === undefined || row?.observaciones === null
    ? 1
    : Number(row.observaciones || 0)
);

const dailyFlag = (row, aggregateField, predicate) => (
  row?.[aggregateField] === undefined || row?.[aggregateField] === null
    ? Number(Boolean(predicate(row)))
    : Number(row[aggregateField] || 0)
);

function hasField(rows, field) {
  return rows.some((row) => row?.[field] !== undefined && row?.[field] !== null);
}

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
    totals.set(id, (totals.get(id) || 0) + observationWeight(row));
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
  const cveEnt = row.cve_ent || (row.cvegeo ? String(row.cvegeo).slice(0, 2) : undefined);
  const estado = (estados || []).find((item) => item.cve_ent === cveEnt);
  const municipio = (municipios || []).find((item) => item.cvegeo === row.cvegeo);
  const observaciones = observationWeight(row);

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
    n_observaciones: observaciones,
    dias: observaciones,
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
    const observaciones = observationWeight(row);
    current.n_observaciones += observaciones;
    current.dias += observaciones;
    current.dias_con_firms += dailyFlag(row, "dias_firms", (item) => Number(item.firms_detecciones || 0) > 0);
    current.dias_con_conafor += dailyFlag(row, "dias_conafor", (item) => Number(item.conafor_eventos || 0) > 0);
    current.dias_con_smn += dailyFlag(row, "dias_smn", (item) => Number(item.smn_obs || 0) > 0);
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

function temporalKey(row) {
  if (row.fecha) return String(row.fecha).slice(0, 10);
  if (row.anio !== undefined && row.mes !== undefined) return `${row.anio}-${String(row.mes).padStart(2, "0")}`;
  return row.periodo_serie || "";
}

function temporalLabel(key) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(key)) {
    const [, month, day] = key.split("-");
    return `${day}/${month}`;
  }
  if (/^\d{4}-\d{2}$/.test(key)) {
    const [year, month] = key.split("-");
    const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
    return `${monthNames[Number(month) - 1]} ${year}`;
  }
  return key;
}

function buildTemporalSeries(rows = []) {
  const grouped = new Map();

  rows.forEach((row) => {
    const periodKey = temporalKey(row);
    if (!periodKey) return;
    const series = row.serie_temporal ? String(row.serie_temporal) : "Periodo";
    const key = `${series}|${periodKey}`;
    const current = grouped.get(key) ?? {
      periodKey,
      label: temporalLabel(periodKey),
      series,
      observaciones: 0,
      firms_detecciones: 0,
      firms_frp: 0,
      conafor_eventos: 0,
      conafor_ha: 0,
      precipWeighted: 0,
      tempMinWeighted: 0,
      tempMaxWeighted: 0,
      climateWeight: 0,
    };

    const weight = Math.max(1, observationWeight(row));
    current.observaciones += observationWeight(row);
    current.firms_detecciones += Number(row.firms_detecciones || 0);
    current.firms_frp += Number(row.firms_frp || 0);
    current.conafor_eventos += Number(row.conafor_eventos || 0);
    current.conafor_ha += Number(row.conafor_ha || 0);

    if (row.precip_mm !== undefined && row.precip_mm !== null) current.precipWeighted += Number(row.precip_mm) * weight;
    if (row.temp_min_c !== undefined && row.temp_min_c !== null) current.tempMinWeighted += Number(row.temp_min_c) * weight;
    if (row.temp_max_c !== undefined && row.temp_max_c !== null) current.tempMaxWeighted += Number(row.temp_max_c) * weight;
    if ([row.precip_mm, row.temp_min_c, row.temp_max_c].some((value) => value !== undefined && value !== null)) current.climateWeight += weight;

    grouped.set(key, current);
  });

  return Array.from(grouped.values())
    .map((row) => ({
      periodKey: row.periodKey,
      label: row.label,
      series: row.series,
      observaciones: row.observaciones,
      firms_detecciones: row.firms_detecciones,
      firms_frp: row.firms_frp,
      conafor_eventos: row.conafor_eventos,
      conafor_ha: row.conafor_ha,
      precip_mm: row.climateWeight ? row.precipWeighted / row.climateWeight : null,
      temp_min_c: row.climateWeight ? row.tempMinWeighted / row.climateWeight : null,
      temp_max_c: row.climateWeight ? row.tempMaxWeighted / row.climateWeight : null,
    }))
    .sort((a, b) => a.periodKey.localeCompare(b.periodKey) || a.series.localeCompare(b.series));
}

export function buildRealDashboardResults({ consulta, rows, clusters, estados, municipios, temporalRows = [] }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const safeTemporalRows = Array.isArray(temporalRows) ? temporalRows : [];
  const clusterId = getDominantCluster(safeRows);
  const cluster = (clusters || []).find((item) => Number(item.cluster) === Number(clusterId));
  const estado = (estados || []).find((item) => item.cve_ent === consulta.cveEnt);
  const municipio = (municipios || []).find((item) => item.cvegeo === consulta.cvegeo);
  const decoratedRows = safeRows.map((row) => decorateRow(row, { clusters, estados, municipios }));
  const summaryRows = buildSummaryRows(safeRows, clusters);

  return {
    fuente: "api-v2",
    tipoPeriodo: consulta.tipoPeriodo,
    nivelAgregacion: consulta.nivelAgregacion,
    periodo: getPeriodoLabel(consulta),
    territorio: municipio?.nombre || estado?.nombre || (consulta.nivelAgregacion === "municipio" ? "Municipios seleccionados" : "México"),
    observaciones: safeRows.reduce((total, row) => total + observationWeight(row), 0),
    dias_incendio: hasField(safeRows, "dias_incendio") ? sum(safeRows, "dias_incendio") : null,
    dias_extremo: hasField(safeRows, "dias_extremo") ? sum(safeRows, "dias_extremo") : null,
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
    temporalRows: buildTemporalSeries(safeTemporalRows),
    rows: decoratedRows,
    exportRows: decoratedRows,
    exportColumns: safeRows.length ? Object.keys(safeRows[0]) : [],
    totalRecords: safeRows.length,
  };
}
