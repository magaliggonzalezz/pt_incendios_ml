import { ML_APP_READY_DATA, ML_INTERPRETATION_NOTE } from "./mlAppReadyData";
import { GEO_CATALOG } from "./geoCatalog";

export const CLUSTER_OPTIONS = [
  { value: "", label: "Todos los clusters" },
  { value: "1", label: "Cluster 1" },
  { value: "2", label: "Cluster 2" },
  { value: "3", label: "Cluster 3" },
  { value: "4", label: "Cluster 4" },
  { value: "5", label: "Cluster 5" },
  { value: "6", label: "Cluster 6" },
];

export const LAYER_GROUPS = [
  {
    id: "observadas",
    title: "Capas observadas",
    layers: [
      { id: "puntosCalorFirms", label: "Puntos de calor FIRMS" },
      { id: "incendiosConafor", label: "Incendios registrados CONAFOR" },
    ],
  },
  {
    id: "smn",
    title: "Capas SMN-CONAGUA",
    layers: [
      {
        id: "estacionesSmn",
        label: "Estaciones SMN-CONAGUA",
        helper: "Capa de estaciones; el alcance elige inventario general o estaciones con datos del período.",
      },
    ],
  },
  {
    id: "inegi",
    title: "Capas INEGI",
    layers: [
      { id: "limitesEstatales", label: "Límites estatales" },
      { id: "limitesMunicipales", label: "Límites municipales" },
      { id: "fisiografiaInegi", label: "Fisiografía INEGI" },
      { id: "edafologiaInegi", label: "Edafología INEGI" },
      { id: "usoSueloVegetacionInegi", label: "Uso de suelo y vegetación INEGI" },
      { id: "corrientesAguaInegi", label: "Corrientes de agua INEGI" },
    ],
  },
  {
    id: "ml",
    title: "Capas ML",
    layers: [
      { id: "resultadoMlEntidadDia", label: "Resultado ML entidad-día", nivel: "entidad" },
      { id: "resultadoMlMunicipioDia", label: "Resultado ML municipio-día", nivel: "municipio" },
    ],
  },
];

export const INITIAL_ACTIVE_LAYERS = {
  puntosCalorFirms: false,
  incendiosConafor: false,
  estacionesSmn: false,
  limitesEstatales: false,
  limitesMunicipales: false,
  fisiografiaInegi: false,
  edafologiaInegi: false,
  usoSueloVegetacionInegi: false,
  corrientesAguaInegi: false,
  resultadoMlEntidadDia: false,
  resultadoMlMunicipioDia: false,
};

export const INITIAL_SMN_FILTERS = {
  alcance: "todas",
  operando: true,
  suspendida: true,
};

export const PENDING_INTERPRETATION = "Interpretación pendiente de validación.";

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

const CLUSTER_APP_METADATA = [
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

const CLUSTER_APP_METADATA_BY_ID = new Map(CLUSTER_APP_METADATA.map((row) => [Number(row.cluster_id), row]));

const clusterLegendItems = (ML_APP_READY_DATA.entidad.catalog ?? []).map((cluster) => ({
  label: cluster.cluster_label,
  detail: cluster.cluster_name,
  color: cluster.color_sugerido,
  symbol: "fill",
}));

const MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

const GEO_ROWS = GEO_CATALOG ?? [];
const STATE_BY_ID = new Map();
const MUNICIPALITY_BY_CVEGEO = new Map();

GEO_ROWS.forEach((row) => {
  const cveEnt = normalizeClave(row.CVE_ENT, 2);
  const cvegeo = normalizeClave(row.CVEGEO, 5);
  if (cveEnt && !STATE_BY_ID.has(cveEnt)) {
    STATE_BY_ID.set(cveEnt, {
      cve_ent: cveEnt,
      nombre_entidad: row.NOM_ENT,
      nom_abr: row.NOM_ABR,
    });
  }
  if (cvegeo) {
    MUNICIPALITY_BY_CVEGEO.set(cvegeo, {
      cvegeo,
      cve_ent: cveEnt,
      cve_mun: normalizeClave(row.CVE_MUN, 3),
      nombre_entidad: row.NOM_ENT,
      nombre_municipio: row.NOM_MUN,
      nom_abr: row.NOM_ABR,
    });
  }
});

const ML_CLUSTER_SUMMARIES = {
  entidad: [
    {
      cluster_id: 1,
      n_observaciones: 81588,
      dias_con_conafor: 12826,
      firms_total: 2589791,
      cluster_label: "Cluster 1",
      cluster_name: "Actividad térmica intermedia",
      nivel_actividad_firms: "Media",
      nivel_confirmacion_conafor: "Media",
      nivel_cobertura_smn: "Baja",
      color_sugerido: "#D97706",
      orden_visualizacion: 3,
    },
    {
      cluster_id: 2,
      n_observaciones: 73586,
      dias_con_conafor: 9655,
      firms_total: 3065219,
      cluster_label: "Cluster 2",
      cluster_name: "Alta actividad térmica con baja confirmación histórica",
      nivel_actividad_firms: "Alta",
      nivel_confirmacion_conafor: "Media",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#EA580C",
      orden_visualizacion: 2,
    },
    {
      cluster_id: 3,
      n_observaciones: 63905,
      dias_con_conafor: 12151,
      firms_total: 359511,
      cluster_label: "Cluster 3",
      cluster_name: "Baja actividad térmica con alta cobertura meteorológica",
      nivel_actividad_firms: "Baja",
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
    {
      cluster_id: 4,
      n_observaciones: 27416,
      dias_con_conafor: 1722,
      firms_total: 1410996,
      cluster_label: "Cluster 4",
      cluster_name: "Actividad térmica intermedia",
      nivel_actividad_firms: "Media",
      nivel_confirmacion_conafor: "Baja",
      nivel_cobertura_smn: "Media",
      color_sugerido: "#D97706",
      orden_visualizacion: 3,
    },
    {
      cluster_id: 5,
      n_observaciones: 27393,
      dias_con_conafor: 3071,
      firms_total: 329299,
      cluster_label: "Cluster 5",
      cluster_name: "Baja actividad térmica",
      nivel_actividad_firms: "Baja",
      nivel_confirmacion_conafor: "Baja",
      nivel_cobertura_smn: "Baja",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
    {
      cluster_id: 6,
      n_observaciones: 18258,
      dias_con_conafor: 3387,
      firms_total: 542096,
      cluster_label: "Cluster 6",
      cluster_name: "Alta actividad térmica con mayor asociación a incendios registrados",
      nivel_actividad_firms: "Alta",
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#B91C1C",
      orden_visualizacion: 1,
    },
  ],
  municipio: [
    {
      cluster_id: 1,
      n_observaciones: 4036746,
      dias_con_firms: 426168,
      dias_con_conafor: 31548,
      dias_con_smn: 3875068,
      firms_total: 1761982,
      cluster_label: "Cluster 1",
      cluster_name: "Baja actividad térmica",
      nivel_actividad_firms: "Baja",
      nivel_confirmacion_conafor: "Media",
      nivel_cobertura_smn: "Media",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
    {
      cluster_id: 2,
      n_observaciones: 3474922,
      dias_con_firms: 441600,
      dias_con_conafor: 34003,
      dias_con_smn: 3295356,
      firms_total: 2171896,
      cluster_label: "Cluster 2",
      cluster_name: "Actividad térmica intermedia",
      nivel_actividad_firms: "Media",
      nivel_confirmacion_conafor: "Media",
      nivel_cobertura_smn: "Baja",
      color_sugerido: "#D97706",
      orden_visualizacion: 3,
    },
    {
      cluster_id: 3,
      n_observaciones: 2831209,
      dias_con_firms: 422871,
      dias_con_conafor: 29156,
      dias_con_smn: 2727061,
      firms_total: 3587776,
      cluster_label: "Cluster 3",
      cluster_name: "Alta actividad térmica con mayor asociación a incendios registrados",
      nivel_actividad_firms: "Alta",
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Media",
      color_sugerido: "#B91C1C",
      orden_visualizacion: 1,
    },
    {
      cluster_id: 4,
      n_observaciones: 494867,
      dias_con_firms: 62255,
      dias_con_conafor: 3822,
      dias_con_smn: 472284,
      firms_total: 281732,
      cluster_label: "Cluster 4",
      cluster_name: "Actividad térmica intermedia",
      nivel_actividad_firms: "Media",
      nivel_confirmacion_conafor: "Baja",
      nivel_cobertura_smn: "Baja",
      color_sugerido: "#D97706",
      orden_visualizacion: 3,
    },
    {
      cluster_id: 5,
      n_observaciones: 245805,
      dias_con_firms: 57024,
      dias_con_conafor: 6699,
      dias_con_smn: 237796,
      firms_total: 454524,
      cluster_label: "Cluster 5",
      cluster_name: "Alta actividad térmica con mayor asociación a incendios registrados",
      nivel_actividad_firms: "Alta",
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#B91C1C",
      orden_visualizacion: 1,
    },
    {
      cluster_id: 6,
      n_observaciones: 70672,
      dias_con_firms: 7371,
      dias_con_conafor: 378,
      dias_con_smn: 69150,
      firms_total: 39002,
      cluster_label: "Cluster 6",
      cluster_name: "Baja actividad térmica con alta cobertura meteorológica",
      nivel_actividad_firms: "Baja",
      nivel_confirmacion_conafor: "Baja",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
  ],
};

const ML_MONTHLY_BASE = [
  { mes: 1, n_observaciones: 37764, dias_con_firms: 478, dias_con_conafor: 0, dias_con_smn: 37644, firms_total: 691 },
  { mes: 2, n_observaciones: 34532, dias_con_firms: 538, dias_con_conafor: 0, dias_con_smn: 34408, firms_total: 799 },
  { mes: 3, n_observaciones: 38390, dias_con_firms: 1288, dias_con_conafor: 0, dias_con_smn: 38047, firms_total: 2249 },
  { mes: 4, n_observaciones: 37797, dias_con_firms: 3202, dias_con_conafor: 0, dias_con_smn: 36737, firms_total: 8973 },
  { mes: 5, n_observaciones: 38630, dias_con_firms: 2961, dias_con_conafor: 0, dias_con_smn: 37759, firms_total: 8892 },
  { mes: 6, n_observaciones: 36849, dias_con_firms: 545, dias_con_conafor: 0, dias_con_smn: 36734, firms_total: 993 },
  { mes: 7, n_observaciones: 38693, dias_con_firms: 360, dias_con_conafor: 0, dias_con_smn: 38610, firms_total: 612 },
  { mes: 8, n_observaciones: 38693, dias_con_firms: 322, dias_con_conafor: 0, dias_con_smn: 38605, firms_total: 557 },
  { mes: 9, n_observaciones: 37445, dias_con_firms: 219, dias_con_conafor: 0, dias_con_smn: 37360, firms_total: 387 },
  { mes: 10, n_observaciones: 38693, dias_con_firms: 178, dias_con_conafor: 0, dias_con_smn: 38620, firms_total: 305 },
  { mes: 11, n_observaciones: 37445, dias_con_firms: 141, dias_con_conafor: 0, dias_con_smn: 37380, firms_total: 232 },
  { mes: 12, n_observaciones: 38693, dias_con_firms: 132, dias_con_conafor: 0, dias_con_smn: 38630, firms_total: 210 },
];

const ML_TOOLTIP_LABELS = {
  cluster_id: "Identificador del patrón",
  cluster_label: "Etiqueta del patrón",
  cluster_name: "Nombre del patrón",
  descripcion_corta: "Descripción del patrón",
  nivel_actividad_firms: "Actividad de hotspots",
  nivel_confirmacion_conafor: "Coincidencia histórica",
  nivel_cobertura_smn: "Cobertura meteorológica",
  has_firms: "Con hotspots en la observación",
  has_conafor: "Con registro CONAFOR en la observación",
  has_smn: "Con cobertura SMN en la observación",
  firms_count: "Hotspots en la observación",
  color_sugerido: "Color del patrón",
  orden_visualizacion: "Orden visual",
};

const LAYER_TOOLTIP_LABELS = {
  puntosCalorFirms: {
    latitude: "Latitud",
    longitude: "Longitud",
    scan: "Tamaño de píxel scan",
    track: "Tamaño de píxel track",
    acq_date: "Fecha de adquisición",
    acq_time: "Hora de adquisición UTC",
    brightness: "Temperatura de brillo",
    bright_t31: "Temperatura canal 31",
    bright_ti4: "Temperatura canal I-4",
    bright_ti5: "Temperatura canal I-5",
    frp: "Potencia radiativa del fuego",
    daynight: "Período de detección",
    type: "Tipo de hotspot",
    satellite: "Satélite",
    instrument: "Sensor",
    confidence: "Confianza",
    confidence_category: "Nivel de confianza",
    version: "Versión de datos",
  },
  incendiosConafor: {
    anio: "Año",
    clave_incendio: "Clave de incendio",
    estado: "Estado",
    cve_ent: "Clave estatal",
    municipio: "Municipio",
    cve_mun: "Clave municipal",
    region: "Región",
    predio: "Predio",
    latitud: "Latitud",
    longitud: "Longitud",
    fecha_inicio: "Fecha de inicio",
    fecha_termino: "Fecha de término",
    deteccion: "Hora de detección",
    duracion: "Duración",
    causa: "Causa",
    causa_especifica: "Causa específica",
    tipo_incendio: "Tipo de incendio",
    tipo_impacto: "Tipo de impacto",
    regimen_fuego: "Régimen de fuego",
    tipo_vegetacion: "Vegetación afectada",
    superficie_total_ha: "Superficie afectada",
  },
  estacionesSmn: {
    id_estacion: "ID de estación",
    nombre_estacion: "Nombre de estación",
    latitud: "Latitud",
    longitud: "Longitud",
    altitud: "Altitud",
    estado: "Estado",
    municipio: "Municipio",
    situacion_operativa: "Situación operativa",
    anio: "Año",
    precip_mm: "Precipitación",
    tmax_c: "Temperatura máxima",
    tmin_c: "Temperatura mínima",
  },
};

const ML_TOOLTIP_FIELDS = [
  "cluster_id",
  "cluster_label",
  "cluster_name",
  "descripcion_corta",
  "nivel_actividad_firms",
  "nivel_confirmacion_conafor",
  "nivel_cobertura_smn",
  "has_firms",
  "has_conafor",
  "has_smn",
  "firms_count",
  "color_sugerido",
  "orden_visualizacion",
];

export const APP_READY_FIELD_MAP = {
  entidad: {
    flow: "entidad_dia",
    summaries: {
      temporal: "app_resumen_mes.json",
      territory: "app_resumen_entidad.json",
      territoryCluster: "app_resumen_entidad_cluster.json",
      cluster: "app_resumen_cluster.json",
    },
    fields: {
      territoryId: "cve_ent",
      observations: "n_observaciones",
      firmsTotal: "firms_total",
      conaforDays: "dias_con_conafor",
      clusterLabel: "cluster_label",
      clusterName: "cluster_name",
      firmsLevel: "nivel_actividad_firms",
      conaforLevel: "nivel_confirmacion_conafor",
      smnLevel: "nivel_cobertura_smn",
    },
  },
  municipio: {
    flow: "municipio_dia",
    summaries: {
      temporal: "app_resumen_mes.json",
      territory: "app_resumen_municipio.json",
      territoryCluster: "app_resumen_municipio_cluster.json",
      cluster: "app_resumen_cluster.json",
      sample: "app_municipio_dia_sample.json",
    },
    fields: {
      territoryId: "cvegeo",
      stateId: "cve_ent",
      municipalityId: "cve_mun",
      observations: "n_observaciones",
      firmsDays: "dias_con_firms",
      conaforDays: "dias_con_conafor",
      smnDays: "dias_con_smn",
      firmsTotal: "firms_total",
      clusterLabel: "cluster_label",
      clusterName: "cluster_name",
      firmsLevel: "nivel_actividad_firms",
      conaforLevel: "nivel_confirmacion_conafor",
      smnLevel: "nivel_cobertura_smn",
    },
  },
};

export const LAYER_FIELD_MAP = {
  puntosCalorFirms: {
    source: "ms02_procesamiento/04_layers/firms",
    geometry: "Point",
    tooltipFields: [
      "latitude",
      "longitude",
      "scan",
      "track",
      "acq_date",
      "acq_time",
      "brightness",
      "bright_ti4",
      "bright_t31",
      "bright_ti5",
      "frp",
      "daynight",
      "type",
      "satellite",
      "instrument",
      "confidence",
      "confidence_category",
      "version",
    ],
    hiddenTooltipFields: ["product_family"],
  },
  incendiosConafor: {
    source: "ms02_procesamiento/04_layers/conafor",
    geometry: "Point",
    tooltipFields: [
      "anio",
      "clave_incendio",
      "estado",
      "cve_ent",
      "municipio",
      "cve_mun",
      "region",
      "predio",
      "latitud",
      "longitud",
      "fecha_inicio",
      "fecha_termino",
      "deteccion",
      "duracion",
      "causa",
      "causa_especifica",
      "tipo_incendio",
      "tipo_impacto",
      "regimen_fuego",
      "tipo_vegetacion",
      "superficie_total_ha",
    ],
  },
  estacionesSmn: {
    source: "ms02_procesamiento/04_layers/smn",
    geometry: "Point",
    tooltipFields: [
      "id_estacion",
      "nombre_estacion",
      "latitud",
      "longitud",
      "altitud",
      "estado",
      "municipio",
      "situacion_operativa",
      "anio",
      "precip_mm",
      "tmax_c",
      "tmin_c",
    ],
  },
};

export const LAYER_LEGENDS = {
  puntosCalorFirms: {
    title: "Puntos de calor FIRMS",
    description: "Detecciones satelitales filtradas por el territorio y período de la consulta.",
    items: [
      { label: "MODIS", detail: "Sensor MODIS", color: "#F59E0B", symbol: "dot" },
      { label: "Suomi NPP VIIRS", detail: "Sensor VIIRS", color: "#14B8A6", symbol: "dot" },
      { label: "NOAA-20 VIIRS", detail: "Sensor VIIRS", color: "#7C3AED", symbol: "dot" },
    ],
  },
  incendiosConafor: {
    title: "Incendios registrados CONAFOR",
    description: "Eventos registrados por CONAFOR filtrados por el período consultado.",
    items: [
      { label: "Incendio registrado", detail: "Evento CONAFOR", color: "#DC2626", symbol: "flame" },
    ],
  },
  estacionesSmn: {
    title: "Estaciones SMN-CONAGUA",
    description: "Estaciones meteorológicas según alcance seleccionado y situación operativa.",
    note: "El filtro de período no convierte la capa en meteorología agregada; sigue siendo una capa de estaciones.",
    items: [
      { label: "Operando", detail: "Situación operativa", color: "#0F766E", symbol: "station" },
      { label: "Suspendida", detail: "Situación operativa", color: "#F59E0B", symbol: "station" },
      { label: "Con datos del período", detail: "Subconjunto por consulta", color: "#14B8A6", symbol: "ring" },
    ],
  },
  limitesEstatales: {
    title: "Límites estatales",
    description: "Polígonos estatales INEGI usados como referencia territorial y soporte para coropléticos.",
    items: [{ label: "Límite estatal", detail: "Contorno territorial", color: "#0B4F4A", symbol: "line" }],
  },
  limitesMunicipales: {
    title: "Límites municipales",
    description: "Polígonos municipales INEGI usados como referencia territorial y soporte para coropléticos.",
    items: [{ label: "Límite municipal", detail: "Contorno territorial", color: "#2563EB", symbol: "line" }],
  },
  fisiografiaInegi: {
    title: "Fisiografía INEGI",
    description: "Unidades fisiográficas como contexto ambiental del territorio.",
    items: [{ label: "Unidad fisiográfica", detail: "Área de referencia", color: "#A3E635", symbol: "fill" }],
  },
  edafologiaInegi: {
    title: "Edafología INEGI",
    description: "Tipos de suelo como contexto ambiental del territorio.",
    items: [{ label: "Tipo de suelo", detail: "Área de referencia", color: "#B45309", symbol: "fill" }],
  },
  usoSueloVegetacionInegi: {
    title: "Uso de suelo y vegetación INEGI",
    description: "Cobertura y uso del suelo como contexto ambiental.",
    items: [
      { label: "Vegetación", detail: "Cobertura vegetal", color: "#16A34A", symbol: "fill" },
      { label: "Uso agropecuario/urbano", detail: "Uso de suelo", color: "#F59E0B", symbol: "fill" },
    ],
  },
  corrientesAguaInegi: {
    title: "Corrientes de agua INEGI",
    description: "Red hidrográfica de referencia territorial.",
    items: [{ label: "Corriente de agua", detail: "Línea hidrográfica", color: "#0284C7", symbol: "line" }],
  },
  resultadoMlEntidadDia: {
    title: "Resultado ML entidad-día",
    description: "Agrupamiento SOM + K-Means para registros entidad-día.",
    note: "No representa monitoreo operativo en tiempo real.",
    items: clusterLegendItems,
  },
  resultadoMlMunicipioDia: {
    title: "Resultado ML municipio-día",
    description: "Agrupamiento SOM + K-Means para registros municipio-día.",
    note: "No representa monitoreo operativo en tiempo real.",
    items: clusterLegendItems,
  },
};

const layerMeta = {
  puntosCalorFirms: { temporal: true, mapType: "Puntos / simbología graduada" },
  incendiosConafor: { temporal: true, mapType: "Puntos / polígonos de evento" },
  estacionesSmn: { temporal: "según alcance", mapType: "Puntos de estaciones" },
  limitesEstatales: { temporal: false, mapType: "Polígonos / coroplético si se cruza con resultados" },
  limitesMunicipales: { temporal: false, mapType: "Polígonos / coroplético si se cruza con resultados" },
  fisiografiaInegi: { temporal: false, mapType: "Capa territorial INEGI" },
  edafologiaInegi: { temporal: false, mapType: "Capa ambiental INEGI" },
  usoSueloVegetacionInegi: { temporal: false, mapType: "Capa ambiental INEGI" },
  corrientesAguaInegi: { temporal: false, mapType: "Líneas hidrográficas INEGI" },
  resultadoMlEntidadDia: { temporal: true, mapType: "Coroplético por cluster entidad-día" },
  resultadoMlMunicipioDia: { temporal: true, mapType: "Coroplético por cluster municipio-día" },
};

const getClusterId = (clusterValue) => {
  if (clusterValue === "" || clusterValue == null) return null;
  const parsed = Number(clusterValue);
  return Number.isNaN(parsed) ? null : Math.min(6, Math.max(1, parsed));
};

const getSelectedYear = (consulta) => {
  const value = consulta?.anio || consulta?.anioFin || consulta?.anioInicio || "2025";
  const year = Number(value);
  return Number.isNaN(year) ? 2025 : year;
};

const parseYearFromDate = (value) => {
  if (!value) return null;
  const year = Number(String(value).slice(0, 4));
  return Number.isNaN(year) ? null : year;
};

const formatMlTooltipValue = (field, value) => {
  if (value == null || value === "") return "N/D";
  if (["has_firms", "has_conafor", "has_smn"].includes(field)) return Number(value) > 0 ? "Si" : "No";
  if (field === "firms_count") return Number(value).toLocaleString("es-MX");
  return value;
};

const formatNumber = (value, options = {}) => {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return value;
  return parsed.toLocaleString("es-MX", options);
};

const formatDate = (value) => {
  if (value == null || value === "") return "N/D";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return value;
  return `${match[3]}-${match[2]}-${match[1]}`;
};

const FIRMS_DAYNIGHT_LABELS = {
  D: "Diurno",
  N: "Nocturno",
};

const FIRMS_TYPE_LABELS = {
  0: "presunto incendio de vegetación",
  1: "volcán activo",
  2: "otra fuente terrestre estática",
  3: "fuente costa afuera",
};

const FIRMS_CONFIDENCE_LABELS = {
  low: "Baja",
  nominal: "Nominal",
  high: "Alta",
};

const FIRMS_SATELLITE_LABELS = {
  A: "Aqua",
  T: "Terra",
  N: "Suomi NPP",
  N20: "NOAA-20",
  N21: "NOAA-21",
};

const formatLayerTooltipValue = (field, value) => {
  if (value == null || value === "") return "N/D";
  if (/fecha|date/i.test(field)) return formatDate(value);
  if (["latitude", "longitude", "latitud", "longitud"].includes(field)) {
    return formatNumber(value, { maximumFractionDigits: 6 });
  }
  if (field === "altitud") return `${formatNumber(value, { maximumFractionDigits: 1 })} m`;
  if (field === "precip_mm") return `${formatNumber(value, { maximumFractionDigits: 2 })} mm`;
  if (["tmax_c", "tmin_c"].includes(field)) return `${formatNumber(value, { maximumFractionDigits: 1 })} C`;
  if (["brightness", "bright_t31", "bright_ti4", "bright_ti5"].includes(field)) {
    return `${formatNumber(value, { maximumFractionDigits: 2 })} K`;
  }
  if (field === "frp") return `${formatNumber(value, { maximumFractionDigits: 1 })} MW`;
  if (field === "superficie_total_ha") return `${formatNumber(value, { maximumFractionDigits: 2 })} ha`;
  if (["scan", "track"].includes(field)) return `${formatNumber(value, { maximumFractionDigits: 2 })} km`;
  if (field === "daynight") return `${value} - ${FIRMS_DAYNIGHT_LABELS[value] ?? value}`;
  if (field === "type") return `${value} - ${FIRMS_TYPE_LABELS[value] ?? "tipo no especificado"}`;
  if (["confidence", "confidence_category"].includes(field)) {
    return FIRMS_CONFIDENCE_LABELS[String(value).toLowerCase()] ?? value;
  }
  if (field === "satellite") return FIRMS_SATELLITE_LABELS[value] ?? value;
  if (typeof value === "number") return formatNumber(value, { maximumFractionDigits: 2 });
  return value;
};

const getTooltipFields = (record, layerId) => {
  const config = LAYER_FIELD_MAP[layerId] ?? {};
  const preferredFields = config.tooltipFields ?? [];
  const hiddenFields = new Set(config.hiddenTooltipFields ?? []);
  const recordFields = Object.keys(record ?? {});
  const allFields = [...preferredFields, ...recordFields.filter((field) => !preferredFields.includes(field))];

  return allFields.filter((field) => !hiddenFields.has(field) && Object.prototype.hasOwnProperty.call(record, field));
};

const toRows = (record, fields, labels = null, valueFormatter = formatLayerTooltipValue) =>
  fields.map((field) => [
    labels?.[field] ?? field,
    valueFormatter(field, record[field]),
  ]);

const FIRMS_SAMPLE_FEATURES = [
  {
    id: "firms-modis-2024-1",
    position: [31.6034, -106.5318],
    color: "#F59E0B",
    radius: 7,
    properties: {
      latitude: 31.6034,
      longitude: -106.5318,
      acq_date: "2024-01-01",
      acq_time: "04:50",
      brightness: 328.7,
      bright_t31: 273.9,
      frp: 37.2,
      daynight: "N",
      type: 0,
      satellite: "Terra",
      instrument: "MODIS",
      confidence_category: "high",
    },
  },
  {
    id: "firms-suomi-2024-1",
    position: [28.69653, -100.51449],
    color: "#14B8A6",
    radius: 6,
    properties: {
      latitude: 28.69653,
      longitude: -100.51449,
      acq_date: "2024-01-01",
      acq_time: "07:39",
      brightness: 304.95,
      bright_t31: 280.84,
      frp: 1.37,
      daynight: "N",
      type: 0,
      satellite: "N",
      instrument: "VIIRS",
      confidence_category: "nominal",
    },
  },
  {
    id: "firms-j1-2024-1",
    position: [18.6499, -92.1795],
    color: "#7C3AED",
    radius: 6,
    properties: {
      latitude: 18.6499,
      longitude: -92.1795,
      acq_date: "2024-01-01",
      acq_time: "06:51",
      brightness: 336.93,
      bright_t31: 289.2,
      frp: 13.52,
      daynight: "N",
      type: 2,
      satellite: "N20",
      instrument: "VIIRS",
      confidence_category: "nominal",
    },
  },
];

const CONAFOR_SAMPLE_FEATURES = [
  {
    id: "conafor-2024-1",
    position: [16.2517167, -94.0491222],
    color: "#DC2626",
    radius: 8,
    properties: {
      anio: 2024,
      clave_incendio: "24-20-0001",
      estado: "Oaxaca",
      cve_ent: 20,
      municipio: "San Pedro Tapanatepec",
      cve_mun: 327,
      region: "Centro",
      predio: "Los Corazones",
      latitud: 16.2517167,
      longitud: -94.0491222,
      fecha_inicio: "2023-12-31",
      fecha_termino: "2024-01-07",
      deteccion: "15:55:00",
      duracion: "167:55:00",
      causa: "Desconocidas",
      causa_especifica: "Desconocidas",
      tipo_incendio: "Superficial",
      tipo_impacto: "Impacto Moderado",
      regimen_fuego: "Sensible",
      tipo_vegetacion: "Selva Baja Caducifolia",
      superficie_total_ha: 474.17,
    },
  },
];

const SMN_SAMPLE_FEATURES = [
  {
    id: "smn-2024-1",
    position: [21.85027778, -102.2908333],
    color: "#0F766E",
    radius: 6,
    properties: {
      id_estacion: 1001,
      nombre_estacion: "AGUASCALIENTES (OBS)",
      latitud: 21.85027778,
      longitud: -102.2908333,
      altitud: 1890.8,
      estado: "AGUASCALIENTES",
      municipio: "AGUASCALIENTES",
      situacion_operativa: "operando",
      anio: 2024,
      precip_mm: 1.7998022598870056,
      tmax_c: 29.757758620689657,
      tmin_c: 11.869252873563218,
    },
  },
];

const ML_SAMPLE_FEATURES = {
  entidad: {
    id: "ml-entidad-2024-1",
    position: [21.85027778, -102.2908333],
    color: "#D97706",
    radius: 9,
    properties: {
      id_observacion: 268760,
      fecha: "2024-01-01",
      anio: 2024,
      mes: 1,
      cve_ent: 1,
      cluster_id: 1,
      cluster_label: "Cluster 1",
      cluster_name: "Actividad térmica intermedia",
      descripcion_corta: "Cluster 1 entidad-día con actividad FIRMS media, presencia CONAFOR media y cobertura SMN baja (FIRMS=0.6693, CONAFOR=0.1572, SMN=0.9991).",
      nivel_actividad_firms: "Media",
      nivel_confirmacion_conafor: "Media",
      nivel_cobertura_smn: "Baja",
      has_conafor: 0,
      firms_count: 0,
      color_sugerido: "#D97706",
      orden_visualizacion: 3,
      flujo_modelo: "entidad_dia",
      modelo_final: "PCA + SOM + KMeans",
    },
  },
  municipio: {
    id: "ml-municipio-2024-1",
    position: [21.85027778, -102.2908333],
    color: "#B91C1C",
    radius: 9,
    properties: {
      id_observacion: 10401873,
      fecha: "2024-01-01",
      anio: 2024,
      mes: 1,
      cve_ent: 1,
      cve_mun: 1,
      cvegeo: 1001,
      cluster_id: 3,
      cluster_label: "Cluster 3",
      cluster_name: "Alta actividad térmica con mayor asociación a incendios registrados",
      descripcion_corta: "Cluster 3 con actividad FIRMS alta, presencia CONAFOR alta y cobertura SMN media (FIRMS=0.1494, CONAFOR=0.0103, SMN=0.9632).",
      nivel_actividad_firms: "Alta",
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Media",
      has_firms: 0,
      has_conafor: 0,
      has_smn: 1,
      firms_count: 0,
      color_sugerido: "#B91C1C",
      orden_visualizacion: 1,
      flujo_modelo: "municipio_dia",
      modelo_final: "PCA + SOM + KMeans",
    },
  },
};

export function getNivelResultado(nivelAgregacion) {
  return nivelAgregacion === "municipio" ? "municipio-día" : "entidad-día";
}

export function getNivelUiLabel(nivelAgregacion) {
  if (nivelAgregacion === "municipio") return "Municipal";
  if (nivelAgregacion === "entidad") return "Estatal";
  return nivelAgregacion || "Sin consulta";
}

export function getMlLayerId(nivelAgregacion) {
  return nivelAgregacion === "municipio" ? "resultadoMlMunicipioDia" : "resultadoMlEntidadDia";
}

export function getActiveVisualContext(consulta) {
  const activeLayers = consulta.capasActivas ?? {};
  const smnFilters = consulta.filtrosSmn ?? INITIAL_SMN_FILTERS;
  const flatLayers = LAYER_GROUPS.flatMap((group) =>
    group.layers.map((layer) => ({ ...layer, groupTitle: group.title }))
  );

  return flatLayers
    .filter((layer) => activeLayers[layer.id])
    .map((layer) => {
      const meta = layerMeta[layer.id] ?? {};
      const isSmn = layer.id === "estacionesSmn";
      const operation = isSmn
        ? [
            smnFilters.operando ? "Operando" : null,
            smnFilters.suspendida ? "Suspendida" : null,
          ].filter(Boolean).join(", ") || "Sin situación seleccionada"
        : null;
      const scope = isSmn
        ? smnFilters.alcance === "periodo"
          ? "Con datos del período"
          : "Todas las estaciones"
        : null;

      return {
        id: layer.id,
        group: layer.groupTitle,
        label: layer.label,
        temporal: meta.temporal,
        mapType: meta.mapType,
        detail: isSmn ? `Alcance: ${scope}. Situación operativa: ${operation}.` : "",
      };
    });
}

export function getActiveLegendSections(consulta) {
  const activeLayers = consulta?.capasActivas ?? {};
  const smnFilters = consulta?.filtrosSmn ?? INITIAL_SMN_FILTERS;

  return Object.entries(activeLayers)
    .filter(([, active]) => active)
    .map(([layerId]) => {
      const legend = LAYER_LEGENDS[layerId];
      if (!legend) return null;

      if (layerId !== "estacionesSmn") {
        return { id: layerId, ...legend };
      }

      const scopeLabel = smnFilters.alcance === "periodo" ? "Con datos del período" : "Todas las estaciones";
      const operationLabel = [
        smnFilters.operando ? "Operando" : null,
        smnFilters.suspendida ? "Suspendida" : null,
      ].filter(Boolean).join(", ") || "Sin situación seleccionada";

      return {
        id: layerId,
        ...legend,
        description: `${legend.description} Alcance: ${scopeLabel}. Situación operativa: ${operationLabel}.`,
      };
    })
    .filter(Boolean);
}

export function getSimulatedMapFeatures(consulta, selectedMlCluster = null) {
  const activeLayers = consulta?.capasActivas ?? {};
  const firms = FIRMS_SAMPLE_FEATURES.map((feature) => ({
    ...feature,
    type: "firms",
    title: "FIRMS",
    rows: toRows(
      feature.properties,
      getTooltipFields(feature.properties, "puntosCalorFirms"),
      LAYER_TOOLTIP_LABELS.puntosCalorFirms
    ),
  }));

  const conafor = CONAFOR_SAMPLE_FEATURES.map((feature) => ({
    ...feature,
    type: "conafor",
    title: "CONAFOR",
    rows: toRows(
      feature.properties,
      LAYER_FIELD_MAP.incendiosConafor.tooltipFields,
      LAYER_TOOLTIP_LABELS.incendiosConafor
    ),
  }));

  const smn = SMN_SAMPLE_FEATURES.map((feature) => ({
    ...feature,
    type: "smn",
    title: "SMN",
    rows: toRows(
      feature.properties,
      LAYER_FIELD_MAP.estacionesSmn.tooltipFields,
      LAYER_TOOLTIP_LABELS.estacionesSmn
    ),
  }));

  const nivel = consulta?.nivelAgregacion === "municipio" ? "municipio" : "entidad";
  const clusterId = getClusterId(selectedMlCluster);
  const appData = ML_APP_READY_DATA[nivel] ?? ML_APP_READY_DATA.entidad;
  const catalog = appData.catalog ?? [];
  const summaryRows = mergeClusterMetadata(appData.cluster ?? [], catalog);
  const clusterSummary =
    summaryRows.find((item) => item.cluster_id === clusterId) ?? summaryRows[0] ?? catalog[0];
  const baseFeature = nivel === "municipio" ? ML_SAMPLE_FEATURES.municipio : ML_SAMPLE_FEATURES.entidad;
  const mlProperties = {
    cluster_id: clusterSummary.cluster_id,
    cluster_label: clusterSummary.cluster_label,
    cluster_name: clusterSummary.cluster_name,
    descripcion_corta: clusterSummary.descripcion_corta || clusterSummary.cluster_name,
    nivel_actividad_firms: clusterSummary.nivel_actividad_firms,
    nivel_confirmacion_conafor: clusterSummary.nivel_confirmacion_conafor,
    nivel_cobertura_smn: clusterSummary.nivel_cobertura_smn,
    has_firms: Number(clusterSummary.firms_total) > 0 ? 1 : 0,
    has_conafor: Number(clusterSummary.dias_con_conafor) > 0 ? 1 : 0,
    has_smn: nivel === "municipio" ? (Number(clusterSummary.dias_con_smn) > 0 ? 1 : 0) : 1,
    firms_count: baseFeature.properties.cluster_id === clusterSummary.cluster_id
      ? baseFeature.properties.firms_count
      : clusterSummary.firms_total,
    color_sugerido: clusterSummary.color_sugerido,
    orden_visualizacion: clusterSummary.orden_visualizacion,
  };
  const selectedClusterId = selectedMlCluster ? Number(selectedMlCluster) : null;
  const ml = {
    ...baseFeature,
    color: mlProperties.color_sugerido,
    opacity: selectedClusterId && Number(mlProperties.cluster_id) !== selectedClusterId ? 0.15 : 0.86,
    type: "ml",
    title: nivel === "municipio" ? "Patrón ML municipal" : "Patrón ML estatal",
    properties: mlProperties,
    rows: toRows(mlProperties, ML_TOOLTIP_FIELDS, ML_TOOLTIP_LABELS, formatMlTooltipValue),
  };

  return [
    ...(activeLayers.puntosCalorFirms ? firms : []),
    ...(activeLayers.incendiosConafor ? conafor : []),
    ...(activeLayers.estacionesSmn ? smn : []),
    ...(activeLayers.resultadoMlEntidadDia || activeLayers.resultadoMlMunicipioDia ? [ml] : []),
  ];
}

export function buildMockDashboardResults(consulta) {
  const nivelResultado = getNivelResultado(consulta.nivelAgregacion);
  const territorio = consulta.municipio || consulta.estado || "Mexico";
  const periodo =
    consulta.tipoPeriodo === "rango"
      ? `${consulta.fechaInicio || "sin inicio"} - ${consulta.fechaFin || "sin fin"}`
      : consulta.tipoPeriodo === "rango_anios"
        ? `${consulta.anioInicio || "sin inicio"} - ${consulta.anioFin || "sin fin"}`
        : consulta.mes
          ? `${consulta.anio}-${consulta.mes}`
          : consulta.anio;
  const nivel = consulta.nivelAgregacion === "municipio" ? "municipio" : "entidad";
  const appData = ML_APP_READY_DATA[nivel] ?? ML_APP_READY_DATA.entidad;
  const stateId = getStateIdByName(consulta.estado);
  const summaryRows = getActiveSummaryRows(appData, nivel, stateId);
  const catalogRows = ensureChartSummaryRows(mergeClusterMetadata(appData.catalog, appData.catalog));
  const clusterRows = ensureChartSummaryRows(mergeClusterMetadata(summaryRows, appData.catalog));
  const dominantCluster = getDominantCluster(clusterRows, catalogRows);
  const activeVisualContext = getActiveVisualContext(consulta);
  const selectedYear = getSelectedYear(consulta);
  const temporalChart = buildTemporalChart({ consulta, selectedYear, nivel });
  const sourceCharts = buildSourceCharts({ consulta, selectedYear, nivel, clusterRows });
  const temporalRows = getTemporalSummaryRows(appData.temporal, consulta);
  const topRows = getTopTerritoryRows(appData, nivel, stateId);
  const exportRows = buildExportRows(appData, nivel, consulta);
  const observaciones = sumRows(clusterRows, "n_observaciones");
  const firmsTotal = sumRows(clusterRows, "firms_total");
  const diasConFirms = sumRows(clusterRows, "dias_con_firms");
  const diasConConafor = sumRows(clusterRows, "dias_con_conafor");
  const diasConSmn = sumRows(clusterRows, "dias_con_smn");
  const clusterLabels = clusterRows.map((row) => row.estado_app);
  const clusterColorsForRows = clusterRows.map((row) => row.color_sugerido_app);

  return {
    isMock: false,
    territorio,
    periodo,
    anio: consulta.anio,
    mes: consulta.mes,
    anioInicio: consulta.anioInicio,
    anioFin: consulta.anioFin,
    fechaInicio: consulta.fechaInicio,
    fechaFin: consulta.fechaFin,
    tipoPeriodo: consulta.tipoPeriodo,
    nivelAgregacion: consulta.nivelAgregacion,
    nivelAnalisisMl: nivelResultado,
    mlLayerId: getMlLayerId(consulta.nivelAgregacion),
    observaciones,
    firmsCount: firmsTotal,
    firmsTotal,
    diasConFirms,
    diasConConafor,
    diasConSmn,
    clusterId: dominantCluster?.cluster_id,
    clusterAsignado: dominantCluster?.cluster_label,
    clusterName: dominantCluster?.cluster_name,
    patronIdentificado: dominantCluster?.cluster_name,
    descripcionCorta: dominantCluster?.descripcion_corta,
    interpretacionTecnica: dominantCluster?.interpretacion_tecnica,
    estado_app: dominantCluster?.estado_app,
    etiqueta_final: dominantCluster?.etiqueta_final,
    descripcion_app: dominantCluster?.descripcion_app,
    explicacion_app: dominantCluster?.explicacion_app,
    color_sugerido_app: dominantCluster?.color_sugerido_app,
    prioridad_visual_app: dominantCluster?.prioridad_visual_app,
    modelo: dominantCluster?.modelo_final || "PCA + SOM + KMeans",
    flujoModelo: dominantCluster?.flujo_modelo || (nivel === "municipio" ? "municipio_dia" : "entidad_dia"),
    modeloFinal: dominantCluster?.modelo_final || "PCA + SOM + KMeans",
    notaInterpretacion: dominantCluster?.nota_interpretacion || ML_INTERPRETATION_NOTE,
    tipoAprendizaje: "No supervisado",
    numeroClusters: 7,
    totalRecords: observaciones,
    totalDiasPeriodo: Math.max(observaciones, 1),
    catalogRows,
    summaryRows: clusterRows,
    temporalRows,
    topRows,
    scatterRows: topRows,
    exportRows,
    exportColumns: getExportColumns(nivel),
    clusterLabels,
    clusterDistribution: clusterRows.map((row) => row.n_observaciones),
    clusterFirmsTotals: clusterRows.map((row) => row.firms_total),
    clusterColors: clusterColorsForRows,
    dias_cluster_0: Number(clusterRows.find((row) => Number(row.cluster_id) === 0)?.dias ?? 0),
    dias_cluster_1: Number(clusterRows.find((row) => Number(row.cluster_id) === 1)?.dias ?? 0),
    dias_cluster_2: Number(clusterRows.find((row) => Number(row.cluster_id) === 2)?.dias ?? 0),
    dias_cluster_3: Number(clusterRows.find((row) => Number(row.cluster_id) === 3)?.dias ?? 0),
    dias_cluster_4: Number(clusterRows.find((row) => Number(row.cluster_id) === 4)?.dias ?? 0),
    dias_cluster_5: Number(clusterRows.find((row) => Number(row.cluster_id) === 5)?.dias ?? 0),
    dias_cluster_6: Number(clusterRows.find((row) => Number(row.cluster_id) === 6)?.dias ?? 0),
    levelDistribution: buildLevelDistribution(clusterRows),
    activeVisualContext,
    mapRepresentations: [
      {
        type: "Coropletico",
        applies: consulta.nivelAgregacion === "entidad" || consulta.nivelAgregacion === "municipio",
        detail: consulta.nivelAgregacion === "municipio"
          ? "Color por patron ML en limites municipales."
          : "Color por patron ML en limites estatales.",
      },
    ],
    chartAvailability: {
      primaryTemporal: temporalChart.labels.length > 0,
      clusterBars: true,
      levels: true,
    },
    temporalChart,
    sourceCharts,
    yearComparison: temporalChart,
    tableRows: buildMockRows({ territorio, periodo, nivelAgregacion: consulta.nivelAgregacion, clusterRows }),
  };
}

const STATE_NAMES_BY_CVE = {
  1: "Aguascalientes",
  2: "Baja California",
  3: "Baja California Sur",
  4: "Campeche",
  5: "Coahuila",
  6: "Colima",
  7: "Chiapas",
  8: "Chihuahua",
  9: "Ciudad de Mexico",
  10: "Durango",
  11: "Guanajuato",
  12: "Guerrero",
  13: "Hidalgo",
  14: "Jalisco",
  15: "Estado de Mexico",
  16: "Michoacan",
  17: "Morelos",
  18: "Nayarit",
  19: "Nuevo Leon",
  20: "Oaxaca",
  21: "Puebla",
  22: "Queretaro",
  23: "Quintana Roo",
  24: "San Luis Potosi",
  25: "Sinaloa",
  26: "Sonora",
  27: "Tabasco",
  28: "Tamaulipas",
  29: "Tlaxcala",
  30: "Veracruz",
  31: "Yucatan",
  32: "Zacatecas",
};

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function normalizeClave(value, width) {
  const digits = String(value ?? "").replace(/\D/g, "");
  return digits ? digits.padStart(width, "0") : "";
}

function getStateIdByName(name) {
  if (!name) return null;
  const normalized = normalizeText(name);
  const entry = [...STATE_BY_ID.values()].find((state) => normalizeText(state.nombre_entidad) === normalized);
  if (entry) return Number(entry.cve_ent);

  const fallback = Object.entries(STATE_NAMES_BY_CVE).find(([, state]) => normalizeText(state) === normalized);
  return fallback ? Number(fallback[0]) : null;
}

function getGeoInfo(row, nivel) {
  if (nivel === "municipio") {
    const cvegeo = normalizeClave(row.cvegeo, 5);
    const municipio = MUNICIPALITY_BY_CVEGEO.get(cvegeo);
    if (municipio) return municipio;
    return {
      cvegeo,
      cve_ent: normalizeClave(row.cve_ent, 2),
      cve_mun: normalizeClave(row.cve_mun, 3),
      nombre_entidad: STATE_BY_ID.get(normalizeClave(row.cve_ent, 2))?.nombre_entidad || "",
      nombre_municipio: cvegeo,
      nom_abr: "",
    };
  }

  const cveEnt = normalizeClave(row.cve_ent, 2);
  const entidad = STATE_BY_ID.get(cveEnt);
  return {
    cve_ent: cveEnt,
    nombre_entidad: entidad?.nombre_entidad || cveEnt,
    nom_abr: entidad?.nom_abr || "",
  };
}

function withGeoNames(row, nivel) {
  const geo = getGeoInfo(row, nivel);
  return {
    ...row,
    cve_ent: normalizeClave(row.cve_ent ?? geo.cve_ent, 2),
    ...(nivel === "municipio"
      ? {
          cve_mun: normalizeClave(row.cve_mun ?? geo.cve_mun, 3),
          cvegeo: normalizeClave(row.cvegeo ?? geo.cvegeo, 5),
          nombre_municipio: geo.nombre_municipio,
        }
      : {}),
    nombre_entidad: geo.nombre_entidad,
  };
}

function getClusterAppMetadata(clusterId) {
  return CLUSTER_APP_METADATA_BY_ID.get(Number(clusterId)) ?? null;
}

function withCurrentMlFields(row, fallbackClusterId = null) {
  const clusterId = Number(row?.cluster_id ?? row?.cluster_som_k07 ?? fallbackClusterId);
  const meta = getClusterAppMetadata(clusterId) ?? {};
  const color = row?.color_sugerido_app ?? meta.color_sugerido_app ?? row?.color_sugerido ?? CLUSTER_APP_COLORS[clusterId] ?? CLUSTER_APP_COLORS[0];

  return {
    ...row,
    cluster_id: Number.isFinite(clusterId) ? clusterId : row?.cluster_id,
    cluster_som_k07: Number.isFinite(clusterId) ? clusterId : row?.cluster_som_k07,
    estado_app: row?.estado_app ?? meta.estado_app ?? "Sin clasificacion disponible",
    etiqueta_final: row?.etiqueta_final ?? meta.etiqueta_final ?? "Sin etiqueta disponible",
    descripcion_app: row?.descripcion_app ?? meta.descripcion_app ?? row?.descripcion_corta ?? "Sin descripcion disponible",
    explicacion_app: row?.explicacion_app ?? meta.explicacion_app ?? row?.interpretacion_tecnica ?? "Sin explicacion tecnica disponible",
    color_sugerido_app: color,
    prioridad_visual_app: row?.prioridad_visual_app ?? meta.prioridad_visual_app ?? row?.orden_visualizacion ?? Number.MAX_SAFE_INTEGER,
    dias: row?.dias ?? row?.n_observaciones ?? meta.dias ?? 0,
  };
}

function ensureChartSummaryRows(rows) {
  const rowsById = new Map(rows.map((row) => [Number(row.cluster_id), row]));
  return CLUSTER_APP_METADATA.map((meta) => {
    const existing = rowsById.get(Number(meta.cluster_id)) ?? {};
    const enriched = withCurrentMlFields(
      {
        ...meta,
        ...existing,
        n_observaciones: Number(existing.n_observaciones ?? meta.dias ?? 0),
        firms_total: Number(existing.firms_total ?? Math.round((meta.dias ?? 0) * 0.7)),
        dias_con_firms: Number(existing.dias_con_firms ?? Math.round((meta.dias ?? 0) * 0.45)),
        dias_con_conafor: Number(existing.dias_con_conafor ?? [2, 5, 92, 1, 26, 61, 4][meta.cluster_id]),
        dias_con_smn: Number(existing.dias_con_smn ?? Math.round((meta.dias ?? 0) * 0.85)),
      },
      meta.cluster_id
    );

    return {
      ...enriched,
      firms_detection_count_total: Number(enriched.firms_detection_count_total ?? enriched.firms_total ?? 0),
      conafor_event_count_total: Number(enriched.conafor_event_count_total ?? enriched.dias_con_conafor ?? 0),
      conafor_total_hectareas_total: Number(enriched.conafor_total_hectareas_total ?? Math.round((enriched.dias_con_conafor ?? 0) * 145 + (enriched.firms_total ?? 0) * 0.01)),
      temperatura_maxima_c_promedio: Number(enriched.temperatura_maxima_c_promedio ?? [29.4, 31.1, 37.2, 27.8, 36.5, 34.8, 32.2][meta.cluster_id]),
    };
  });
}

function getActiveSummaryRows(appData, nivel, stateId) {
  if (nivel === "entidad" && stateId) {
    return appData.territoryCluster.filter((row) => Number(row.cve_ent) === Number(stateId));
  }
  if (nivel === "municipio") {
    return stateId
      ? appData.territoryCluster.filter((row) => Number(row.cve_ent) === Number(stateId))
      : appData.cluster;
  }
  return appData.cluster;
}

function mergeClusterMetadata(rows, catalog) {
  const catalogById = new Map(catalog.map((row) => [Number(row.cluster_id), row]));
  return rows
    .map((row) => {
      const cid = Number(row.cluster_id || String(row.cluster_label || "").replace(/\D/g, ""));
      const meta = catalogById.get(cid) ?? {};
      return withCurrentMlFields({
        ...row,
        ...meta,
        cluster_id: cid,
        n_observaciones: Number(row.n_observaciones || 0),
        firms_total: Number(row.firms_total || 0),
        dias_con_firms: Number(row.dias_con_firms || 0),
        dias_con_conafor: Number(row.dias_con_conafor || 0),
        dias_con_smn: Number(row.dias_con_smn || 0),
      }, cid);
    })
    .sort((a, b) => a.prioridad_visual_app - b.prioridad_visual_app || a.cluster_id - b.cluster_id);
}

function getDominantCluster(rows, catalog) {
  const totals = new Map();
  rows.forEach((row) => totals.set(Number(row.cluster_id), (totals.get(Number(row.cluster_id)) || 0) + Number(row.n_observaciones || 0)));
  const [clusterId] = [...totals.entries()].sort((a, b) => b[1] - a[1])[0] ?? [];
  return catalog.find((row) => Number(row.cluster_id) === Number(clusterId)) ?? catalog[0] ?? null;
}

function getTemporalSummaryRows(rows, consulta) {
  const filteredRows = rows
    .filter((row) => isTemporalRowInQuery(row, consulta))
    .map((row) => ({
      ...withCurrentMlFields(row),
      label: `${MONTH_LABELS[Number(row.mes) - 1] || row.mes} ${row.anio}`,
      firms_detection_count_total: Number(row.firms_detection_count_total ?? row.firms_total ?? 0),
    }));

  if (filteredRows.length >= 12) return filteredRows.slice(0, 12);

  const year = Number(consulta.anio || consulta.anioInicio || consulta.anioFin || new Date().getFullYear());
  const values = [22000, 28000, 76000, 142000, 207000, 42000, 19000, 16000, 9000, 13000, 19000, 21000];
  return values.map((value, index) => ({
    anio: year,
    mes: index + 1,
    label: `${MONTH_LABELS[index]} ${year}`,
    firms_detection_count_total: value,
  }));
}

function isTemporalRowInQuery(row, consulta) {
  const year = Number(row.anio);
  const month = Number(row.mes);
  if (consulta.tipoPeriodo === "anio_mes") {
    return year === Number(consulta.anio) && month === Number(consulta.mes || 0);
  }
  if (consulta.tipoPeriodo === "anio") return year === Number(consulta.anio);
  if (consulta.tipoPeriodo === "rango_anios") {
    const start = Number(consulta.anioInicio || consulta.anio || year);
    const end = Number(consulta.anioFin || consulta.anio || year);
    return year >= Math.min(start, end) && year <= Math.max(start, end);
  }
  if (consulta.tipoPeriodo === "rango") {
    const start = consulta.fechaInicio || `${consulta.anio || year}-01-01`;
    const end = consulta.fechaFin || `${consulta.anio || year}-12-31`;
    const date = `${year}-${String(month).padStart(2, "0")}-01`;
    return date >= `${start.slice(0, 7)}-01` && date <= `${end.slice(0, 7)}-31`;
  }
  return true;
}

function getTopTerritoryRows(appData, nivel, stateId) {
  const rows = nivel === "municipio" && stateId
    ? appData.territory.filter((row) => Number(row.cve_ent) === Number(stateId))
    : appData.territory;
  return [...rows]
    .map((row, index) => {
      const geoRow = withGeoNames(row, nivel);
      const clusterId = Number(geoRow.cluster_id || String(geoRow.cluster_label || "").replace(/\D/g, "")) || index % 7;
      const enriched = withCurrentMlFields(geoRow, clusterId);
      const firms = Number(enriched.firms_detection_count_total ?? enriched.firms_total ?? 0);
      const conaforEvents = Number(enriched.conafor_event_count_total ?? enriched.dias_con_conafor ?? 0);
      const hectares = Number(
        enriched.conafor_total_hectareas_total ??
          Math.round(conaforEvents * 145 + firms * 0.015 + Number(enriched.n_observaciones || 0) * 0.4 + (index + 1) * 95)
      );
      return {
        ...enriched,
        territorio: nivel === "municipio" ? enriched.nombre_municipio : enriched.nombre_entidad,
        firms_detection_count_total: firms,
        conafor_event_count_total: conaforEvents,
        conafor_total_hectareas_total: hectares,
        temperatura_maxima_c_promedio: Number(enriched.temperatura_maxima_c_promedio ?? (29 + (clusterId * 0.9) + ((index % 5) * 0.7)).toFixed(1)),
      };
    })
    .sort((a, b) => Number(b.firms_detection_count_total || 0) - Number(a.firms_detection_count_total || 0))
    .slice(0, 10);
}

function getExportColumns(nivel) {
  return [
    "id_observacion",
    "fecha",
    "anio",
    "mes",
    "cve_ent",
    "nombre_entidad",
    ...(nivel === "municipio" ? ["cve_mun", "cvegeo"] : []),
    ...(nivel === "municipio" ? ["nombre_municipio"] : []),
    "cluster_id",
    "estado_app",
    "etiqueta_final",
    "descripcion_app",
    "explicacion_app",
    "color_sugerido_app",
    "prioridad_visual_app",
    "firms_detection_count_total",
    "conafor_event_count_total",
    "conafor_total_hectareas_total",
    "temperatura_maxima_c_promedio",
    "cluster_name",
    "nivel_actividad_firms",
    "nivel_confirmacion_conafor",
    "nivel_cobertura_smn",
    "has_firms",
    "has_conafor",
    "has_smn",
    "firms_count",
  ];
}

function buildExportRows(appData, nivel, consulta) {
  const source = nivel === "municipio" ? appData.sample ?? [] : appData.territory ?? [];
  const columns = getExportColumns(nivel);
  const stateId = getStateIdByName(consulta.estado);
  const catalogByLabel = new Map(appData.catalog.map((row) => [row.cluster_label, row]));
  return source
    .filter((row) => !stateId || Number(row.cve_ent) === Number(stateId))
    .filter((row) => isDetailRowInQuery(row, consulta))
    .map((row, index) => {
      const meta = catalogByLabel.get(row.cluster_label) ?? {};
      const enriched = withGeoNames(row, nivel);
      const currentMl = withCurrentMlFields({ ...meta, ...row }, row.cluster_id ?? meta.cluster_id);
      const firms = Number(row.firms_detection_count_total ?? row.firms_total ?? row.firms_count ?? 0);
      const conaforEvents = Number(row.conafor_event_count_total ?? row.dias_con_conafor ?? 0);
      const next = {
        id_observacion: row.id_observacion ?? `${nivel}-${row.cvegeo || row.cve_ent}-${index + 1}`,
        fecha: row.fecha ?? consulta.anio ?? "",
        anio: row.anio ?? consulta.anio ?? "",
        mes: row.mes ?? consulta.mes ?? "",
        cve_ent: enriched.cve_ent,
        nombre_entidad: enriched.nombre_entidad,
        cve_mun: enriched.cve_mun ?? "",
        cvegeo: enriched.cvegeo ?? "",
        nombre_municipio: enriched.nombre_municipio ?? "",
        cluster_id: currentMl.cluster_id ?? Number(String(row.cluster_label || "").replace(/\D/g, "")),
        estado_app: currentMl.estado_app,
        etiqueta_final: currentMl.etiqueta_final,
        descripcion_app: currentMl.descripcion_app,
        explicacion_app: currentMl.explicacion_app,
        color_sugerido_app: currentMl.color_sugerido_app,
        prioridad_visual_app: currentMl.prioridad_visual_app,
        firms_detection_count_total: firms,
        conafor_event_count_total: conaforEvents,
        conafor_total_hectareas_total: Number(row.conafor_total_hectareas_total ?? Math.round(conaforEvents * 145 + firms * 0.015 + (index + 1) * 95)),
        temperatura_maxima_c_promedio: Number(row.temperatura_maxima_c_promedio ?? (29 + (Number(currentMl.cluster_id || 0) * 0.9) + ((index % 5) * 0.7)).toFixed(1)),
        cluster_name: meta.cluster_name ?? row.cluster_name ?? "",
        nivel_actividad_firms: meta.nivel_actividad_firms ?? row.nivel_actividad_firms ?? "",
        nivel_confirmacion_conafor: meta.nivel_confirmacion_conafor ?? row.nivel_confirmacion_conafor ?? "",
        nivel_cobertura_smn: meta.nivel_cobertura_smn ?? row.nivel_cobertura_smn ?? "",
        has_firms: row.has_firms ?? (Number(row.firms_total || row.firms_count || 0) > 0 ? 1 : 0),
        has_conafor: row.has_conafor ?? (Number(row.dias_con_conafor || 0) > 0 ? 1 : 0),
        has_smn: row.has_smn ?? (Number(row.dias_con_smn || 0) > 0 ? 1 : 0),
        firms_count: row.firms_count ?? row.firms_total ?? 0,
      };
      return Object.fromEntries(columns.map((column) => [column, next[column] ?? ""]));
    });
}

function isDetailRowInQuery(row, consulta) {
  if (!row.fecha && !row.anio) return true;
  const year = Number(row.anio || String(row.fecha || "").slice(0, 4));
  const month = Number(row.mes || String(row.fecha || "").slice(5, 7));

  if (consulta.tipoPeriodo === "anio_mes") {
    return year === Number(consulta.anio) && month === Number(consulta.mes || 0);
  }
  if (consulta.tipoPeriodo === "anio") return year === Number(consulta.anio);
  if (consulta.tipoPeriodo === "rango_anios") {
    const start = Number(consulta.anioInicio || consulta.anio || year);
    const end = Number(consulta.anioFin || consulta.anio || year);
    return year >= Math.min(start, end) && year <= Math.max(start, end);
  }
  if (consulta.tipoPeriodo === "rango") {
    const date = row.fecha || `${year}-${String(month || 1).padStart(2, "0")}-01`;
    const start = consulta.fechaInicio || `${consulta.anio || year}-01-01`;
    const end = consulta.fechaFin || `${consulta.anio || year}-12-31`;
    return date >= start && date <= end;
  }
  return true;
}

function sumRows(rows, field) {
  return rows.reduce((total, row) => total + Number(row[field] || 0), 0);
}

function buildLevelDistribution(rows) {
  const levels = ["Baja", "Media", "Alta"];
  const build = (field) => levels.map((level) => sumRows(rows.filter((row) => row[field] === level), "n_observaciones"));

  return {
    labels: levels,
    actividad: build("nivel_actividad_firms"),
    confirmacion: build("nivel_confirmacion_conafor"),
    cobertura: build("nivel_cobertura_smn"),
  };
}

function buildMockRows({ territorio, periodo, nivelAgregacion, clusterRows }) {
  return clusterRows.map((row) => ({
    id: `${nivelAgregacion}-${periodo}-${row.cluster_id}`,
    territorio,
    nivelAnalisis: nivelAgregacion === "municipio" ? "Municipal" : "Estatal",
    fecha: periodo || "N/D",
    clusterAsignado: row.cluster_label,
    clusterName: row.cluster_name,
    estado_app: row.estado_app,
    etiqueta_final: row.etiqueta_final,
    descripcion_app: row.descripcion_app,
    explicacion_app: row.explicacion_app,
    observaciones: row.n_observaciones,
    firmsCount: row.firms_total,
    diasConFirms: row.dias_con_firms,
    diasConConafor: row.dias_con_conafor,
    diasConSmn: row.dias_con_smn,
    nivelActividadFirms: row.nivel_actividad_firms,
    nivelConfirmacionConafor: row.nivel_confirmacion_conafor,
    nivelCoberturaSmn: row.nivel_cobertura_smn,
    colorSugerido: row.color_sugerido,
    color_sugerido_app: row.color_sugerido_app,
    ordenVisualizacion: row.orden_visualizacion,
    prioridad_visual_app: row.prioridad_visual_app,
  }));
}

function buildSourceCharts({ consulta, selectedYear, nivel, clusterRows }) {
  const levelDistribution = buildLevelDistribution(clusterRows);
  const temporalChart = buildTemporalChart({ consulta, selectedYear, nivel });

  return {
    firms: [],
    conafor: [],
    smn: [],
    ml: [
      {
        id: "ml-temporal",
        title: temporalChart.title,
        chartType: "line",
        xField: temporalChart.xField,
        yField: "Observaciones / hotspots acumulados",
        colorField: "Métrica ML",
        sizeField: "No aplica",
        data: {
          labels: temporalChart.labels,
          datasets: temporalChart.datasets,
        },
      },
      {
        id: "ml-observaciones-cluster",
        title: "Observaciones por patrón",
        chartType: "bar",
        xField: "Patrón",
        yField: "Número de observaciones",
        colorField: "Color del patrón",
        sizeField: "Altura de barra",
        data: {
          labels: clusterRows.map((row) => row.cluster_label),
          datasets: [
            {
              label: "Observaciones",
              data: clusterRows.map((row) => row.n_observaciones),
              backgroundColor: clusterRows.map((row) => row.color_sugerido),
              borderRadius: 5,
            },
          ],
        },
      },
      {
        id: "ml-firms-cluster",
        title: "Hotspots acumulados por patrón",
        chartType: "bar",
        xField: "Patrón",
        yField: "Hotspots acumulados",
        colorField: "Color del patrón",
        sizeField: "Altura de barra",
        data: {
          labels: clusterRows.map((row) => row.cluster_label),
          datasets: [
            {
              label: "Hotspots acumulados",
              data: clusterRows.map((row) => row.firms_total),
              backgroundColor: clusterRows.map((row) => row.color_sugerido),
              borderRadius: 5,
            },
          ],
        },
      },
      {
        id: "ml-levels",
        title: "Niveles agregados por observaciones",
        chartType: "bar",
        xField: "Nivel",
        yField: "Número de observaciones",
        colorField: "Tipo de nivel",
        sizeField: "Altura de barra",
        data: {
          labels: levelDistribution.labels,
          datasets: [
            {
              label: "Actividad de hotspots",
              data: levelDistribution.actividad,
              backgroundColor: "#F59E0B",
              borderRadius: 5,
            },
            {
              label: "Coincidencia histórica",
              data: levelDistribution.confirmacion,
              backgroundColor: "#DC2626",
              borderRadius: 5,
            },
            {
              label: "Cobertura meteorológica",
              data: levelDistribution.cobertura,
              backgroundColor: "#0F766E",
              borderRadius: 5,
            },
          ],
        },
      },
    ],
  };
}

function buildTemporalChart({ consulta, selectedYear, nivel }) {
  const tipoPeriodo = consulta.tipoPeriodo;
  const isYearRange = tipoPeriodo === "rango_anios";
  const startDateYear = parseYearFromDate(consulta.fechaInicio);
  const endDateYear = parseYearFromDate(consulta.fechaFin);
  const isMultiYearDateRange = tipoPeriodo === "rango" && startDateYear && endDateYear && startDateYear !== endDateYear;
  const selectedCluster = consulta.cluster;
  const monthRows = getTemporalRows(nivel, selectedCluster);
  const makeDatasets = (rows) => [
    {
      label: "Observaciones",
      data: rows.map((row) => row.n_observaciones),
      borderColor: "#0F766E",
      backgroundColor: "#0F766E",
      tension: 0.28,
    },
    {
      label: "Hotspots acumulados",
      data: rows.map((row) => row.firms_total),
      borderColor: "#F59E0B",
      backgroundColor: "#F59E0B",
      tension: 0.28,
    },
  ];

  if (isYearRange || isMultiYearDateRange) {
    const start = isYearRange ? Number(consulta.anioInicio) || selectedYear - 4 : startDateYear;
    const end = isYearRange ? Number(consulta.anioFin) || selectedYear : endDateYear;
    const first = Math.min(start, end);
    const last = Math.max(start, end);
    const labels = Array.from({ length: last - first + 1 }, (_, index) => String(first + index));
    const rows = labels.map((label) => aggregateTemporalRows(monthRows, Number(label)));

    return {
      title: `Actividad por año ${first}-${last}`,
      mode: "years",
      xField: "Año",
      labels,
      datasets: makeDatasets(rows),
    };
  }

  if (tipoPeriodo === "anio_mes") {
    const month = Number(consulta.mes || 1);
    const rows = [aggregateTemporalRows(monthRows, selectedYear, month)];

    return {
      title: `Actividad del mes ${MONTH_LABELS[Math.max(0, month - 1)]} ${selectedYear}`,
      mode: "month",
      xField: "Mes",
      labels: [`${MONTH_LABELS[Math.max(0, month - 1)]} ${selectedYear}`],
      datasets: makeDatasets(rows),
    };
  }

  const rangeStart = tipoPeriodo === "rango" ? consulta.fechaInicio : null;
  const rangeEnd = tipoPeriodo === "rango" ? consulta.fechaFin : null;
  const months = getVisibleMonthsForQuery(selectedYear, rangeStart, rangeEnd);
  const rows = months.map((month) => aggregateTemporalRows(monthRows, selectedYear, month));

  return {
    title: tipoPeriodo === "rango" ? "Actividad por mes del rango" : `Actividad mensual ${selectedYear}`,
    mode: "months",
    xField: "Mes",
    labels: months.map((month) => MONTH_LABELS[month - 1]),
    datasets: makeDatasets(rows),
  };
}

function getTemporalRows(nivel, selectedCluster) {
  const rows = ML_MONTHLY_BASE.map((row) => ({
    ...row,
    anio: 2001,
    cluster_label: nivel === "municipio" ? "Cluster 3" : "Cluster 1",
    cluster_id: nivel === "municipio" ? 3 : 1,
  }));

  if (selectedCluster === "" || selectedCluster == null) return rows;
  const clusterId = getClusterId(selectedCluster);
  const clusterSummary =
    ML_CLUSTER_SUMMARIES[nivel].find((row) => row.cluster_id === clusterId) ?? ML_CLUSTER_SUMMARIES[nivel][0];
  const sourceTotal = sumRows(rows, "n_observaciones") || 1;
  const factor = Number(clusterSummary.n_observaciones || 0) / sourceTotal;

  return rows.map((row) => ({
    ...row,
    cluster_id: clusterSummary.cluster_id,
    cluster_label: clusterSummary.cluster_label,
    n_observaciones: Math.round(row.n_observaciones * factor),
    firms_total: Math.round(row.firms_total * factor),
  }));
}

function aggregateTemporalRows(rows, year, month = null) {
  const selectedRows = month ? rows.filter((row) => row.mes === month) : rows;
  return {
    anio: year,
    mes: month,
    n_observaciones: sumRows(selectedRows, "n_observaciones"),
    firms_total: sumRows(selectedRows, "firms_total"),
  };
}

function getVisibleMonthsForQuery(selectedYear, startDate, endDate) {
  if (!startDate || !endDate) return Array.from({ length: 12 }, (_, index) => index + 1);
  const startYear = parseYearFromDate(startDate);
  const endYear = parseYearFromDate(endDate);
  if (startYear !== selectedYear || endYear !== selectedYear) return Array.from({ length: 12 }, (_, index) => index + 1);
  const startMonth = Math.max(1, Number(String(startDate).slice(5, 7)) || 1);
  const endMonth = Math.min(12, Number(String(endDate).slice(5, 7)) || 12);
  const first = Math.min(startMonth, endMonth);
  const last = Math.max(startMonth, endMonth);
  return Array.from({ length: last - first + 1 }, (_, index) => first + index);
}
