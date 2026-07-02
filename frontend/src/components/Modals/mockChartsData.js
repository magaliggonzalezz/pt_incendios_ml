// Paleta mock temporal; sustituir por color_sugerido_app real cuando llegue la API.
export const CLUSTER_APP_COLORS = {
  0: "#64748B",
  1: "#2563EB",
  2: "#B91C1C",
  3: "#0891B2",
  4: "#D97706",
  5: "#EA580C",
  6: "#7C3AED",
};
const CLUSTER_MOCKS = [
  {
    cluster_id: 0,
    estado_app: "Sin incendio activo",
    etiqueta_final: "Condicion estable sin actividad termica relevante",
    descripcion_app: "Predomina una condicion estable sin senales recientes de incendio activo.",
    explicacion_app: "El patron combina baja deteccion satelital, baja afectacion oficial y condiciones climaticas sin presion extrema.",
    color_sugerido_app: CLUSTER_APP_COLORS[0],
    prioridad_visual_app: 7,
    dias: 92000,
  },
  {
    cluster_id: 1,
    estado_app: "Baja actividad termica",
    etiqueta_final: "Actividad satelital aislada",
    descripcion_app: "Se observan senales termicas aisladas, sin acumulacion critica.",
    explicacion_app: "El patron concentra detecciones dispersas y baja relacion con registros oficiales de incendio.",
    color_sugerido_app: CLUSTER_APP_COLORS[1],
    prioridad_visual_app: 5,
    dias: 37000,
  },
  {
    cluster_id: 2,
    estado_app: "Incendio activo extremo",
    etiqueta_final: "Alta actividad termica y afectacion registrada",
    descripcion_app: "Patron con alta intensidad satelital y registros oficiales relevantes.",
    explicacion_app: "Combina conteos FIRMS elevados, FRP acumulado alto y superficie registrada por CONAFOR.",
    color_sugerido_app: CLUSTER_APP_COLORS[2],
    prioridad_visual_app: 1,
    dias: 18500,
  },
  {
    cluster_id: 3,
    estado_app: "Condicion humeda sin incendio activo",
    etiqueta_final: "Baja actividad por humedad o precipitacion",
    descripcion_app: "Condicion con baja actividad termica asociada a mayor humedad o lluvia.",
    explicacion_app: "El patron presenta baja deteccion satelital y precipitacion promedio relativamente alta.",
    color_sugerido_app: CLUSTER_APP_COLORS[3],
    prioridad_visual_app: 6,
    dias: 42000,
  },
  {
    cluster_id: 4,
    estado_app: "Condicion de riesgo climatico",
    etiqueta_final: "Temperatura elevada sin confirmacion de incendio",
    descripcion_app: "Riesgo ambiental elevado sin acumulacion equivalente de incendios confirmados.",
    explicacion_app: "Predominan temperaturas altas y baja precipitacion, con actividad termica moderada o incipiente.",
    color_sugerido_app: CLUSTER_APP_COLORS[4],
    prioridad_visual_app: 3,
    dias: 61000,
  },
  {
    cluster_id: 5,
    estado_app: "Incendio activo moderado",
    etiqueta_final: "Actividad termica con registro parcial",
    descripcion_app: "Patron con actividad termica clara y afectacion oficial moderada.",
    explicacion_app: "Combina detecciones FIRMS persistentes con registros CONAFOR acotados.",
    color_sugerido_app: CLUSTER_APP_COLORS[5],
    prioridad_visual_app: 2,
    dias: 28500,
  },
  {
    cluster_id: 6,
    estado_app: "Actividad residual o dispersa",
    etiqueta_final: "Senales termicas bajas o fragmentadas",
    descripcion_app: "Senales termicas dispersas que no forman un episodio dominante.",
    explicacion_app: "El patron agrupa observaciones de baja magnitud, con poca continuidad temporal y territorial.",
    color_sugerido_app: CLUSTER_APP_COLORS[6],
    prioridad_visual_app: 4,
    dias: 13000,
  },
];

const withClusterKey = (row) => ({ ...row, cluster_som_k07: row.cluster_id });
const clusterById = new Map(CLUSTER_MOCKS.map((cluster) => [cluster.cluster_id, cluster]));

const TERRITORIES = [
  { territorio: "Guerrero", nombre_entidad: "Guerrero", cve_ent: "12", cluster_id: 2, firms_detection_count_total: 84500, firms_frp_total: 152000, conafor_event_count_total: 74, conafor_total_hectareas_total: 18600, temperatura_maxima_c_promedio: 36.8, precipitacion_mm_promedio: 18 },
  { territorio: "Campeche", nombre_entidad: "Campeche", cve_ent: "04", cluster_id: 5, firms_detection_count_total: 68200, firms_frp_total: 119500, conafor_event_count_total: 51, conafor_total_hectareas_total: 9400, temperatura_maxima_c_promedio: 35.4, precipitacion_mm_promedio: 32 },
  { territorio: "Chiapas", nombre_entidad: "Chiapas", cve_ent: "07", cluster_id: 4, firms_detection_count_total: 55300, firms_frp_total: 86400, conafor_event_count_total: 39, conafor_total_hectareas_total: 7200, temperatura_maxima_c_promedio: 34.1, precipitacion_mm_promedio: 44 },
  { territorio: "Jalisco", nombre_entidad: "Jalisco", cve_ent: "14", cluster_id: 2, firms_detection_count_total: 49800, firms_frp_total: 92800, conafor_event_count_total: 66, conafor_total_hectareas_total: 15400, temperatura_maxima_c_promedio: 33.2, precipitacion_mm_promedio: 21 },
  { territorio: "Michoacan", nombre_entidad: "Michoacan", cve_ent: "16", cluster_id: 5, firms_detection_count_total: 43200, firms_frp_total: 74700, conafor_event_count_total: 58, conafor_total_hectareas_total: 12100, temperatura_maxima_c_promedio: 32.8, precipitacion_mm_promedio: 24 },
  { territorio: "Oaxaca", nombre_entidad: "Oaxaca", cve_ent: "20", cluster_id: 4, firms_detection_count_total: 38900, firms_frp_total: 63800, conafor_event_count_total: 42, conafor_total_hectareas_total: 8800, temperatura_maxima_c_promedio: 35.7, precipitacion_mm_promedio: 27 },
  { territorio: "Tabasco", nombre_entidad: "Tabasco", cve_ent: "27", cluster_id: 3, firms_detection_count_total: 25100, firms_frp_total: 32100, conafor_event_count_total: 18, conafor_total_hectareas_total: 2600, temperatura_maxima_c_promedio: 33.9, precipitacion_mm_promedio: 78 },
  { territorio: "Veracruz", nombre_entidad: "Veracruz", cve_ent: "30", cluster_id: 1, firms_detection_count_total: 21800, firms_frp_total: 28700, conafor_event_count_total: 24, conafor_total_hectareas_total: 3100, temperatura_maxima_c_promedio: 31.6, precipitacion_mm_promedio: 63 },
  { territorio: "Chihuahua", nombre_entidad: "Chihuahua", cve_ent: "08", cluster_id: 6, firms_detection_count_total: 17600, firms_frp_total: 25100, conafor_event_count_total: 31, conafor_total_hectareas_total: 6900, temperatura_maxima_c_promedio: 30.5, precipitacion_mm_promedio: 12 },
  { territorio: "Yucatan", nombre_entidad: "Yucatan", cve_ent: "31", cluster_id: 0, firms_detection_count_total: 12600, firms_frp_total: 16400, conafor_event_count_total: 12, conafor_total_hectareas_total: 1300, temperatura_maxima_c_promedio: 34.7, precipitacion_mm_promedio: 48 },
];

const topRows = TERRITORIES.map((territory) => {
  const cluster = clusterById.get(territory.cluster_id);
  return withClusterKey({
    ...territory,
    estado_app: cluster.estado_app,
    etiqueta_final: cluster.etiqueta_final,
    descripcion_app: cluster.descripcion_app,
    explicacion_app: cluster.explicacion_app,
    color_sugerido_app: cluster.color_sugerido_app,
    prioridad_visual_app: cluster.prioridad_visual_app,
    dias: cluster.dias,
  });
});

const temporalValues = [22000, 28000, 76000, 142000, 207000, 42000, 19000, 16000, 9000, 13000, 19000, 21000];

export const MOCK_CHARTS_DATA = {
  territorio: "Mexico",
  periodo: "2025",
  nivelAgregacion: "entidad",
  tipoPeriodo: "anio",
  clusterId: 2,
  dias_cluster_0: 92000,
  dias_cluster_1: 37000,
  dias_cluster_2: 18500,
  dias_cluster_3: 42000,
  dias_cluster_4: 61000,
  dias_cluster_5: 28500,
  dias_cluster_6: 13000,
  catalogRows: CLUSTER_MOCKS.map(withClusterKey),
  summaryRows: CLUSTER_MOCKS.map((cluster) => withClusterKey({
    ...cluster,
    n_observaciones: cluster.dias,
    firms_detection_count_total: Math.round(cluster.dias * (cluster.cluster_id === 2 ? 1.8 : cluster.cluster_id === 5 ? 1.2 : 0.45)),
    firms_frp_total: Math.round(cluster.dias * (cluster.cluster_id === 2 ? 3.2 : cluster.cluster_id === 5 ? 2.1 : 0.8)),
    conafor_event_count_total: [8, 13, 92, 5, 26, 61, 11][cluster.cluster_id],
    conafor_total_hectareas_total: [900, 1300, 23800, 420, 4100, 12700, 1500][cluster.cluster_id],
    temperatura_maxima_c_promedio: [29.4, 31.1, 37.2, 27.8, 36.5, 34.8, 32.2][cluster.cluster_id],
    precipitacion_mm_promedio: [52, 38, 12, 84, 18, 24, 34][cluster.cluster_id],
  })),
  temporalRows: temporalValues.map((value, index) => ({
    anio: 2025,
    mes: index + 1,
    label: `${["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"][index]} 2025`,
    firms_detection_count_total: value,
  })),
  topRows,
  scatterRows: topRows,
  exportRows: topRows.map((row, index) => ({
    ...row,
    id_observacion: `mock-${index + 1}`,
    fecha: `2025-${String((index % 12) + 1).padStart(2, "0")}-01`,
  })),
};
