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
        label: "Estaciones meteorológicas SMN-CONAGUA",
        helper: "Capa de estaciones meteorológicas; el alcance puede mostrar el inventario general o solo estaciones con cobertura en el período seleccionado.",
      },
    ],
  },
  {
    id: "inegi",
    title: "Capas INEGI",
    layers: [
      { id: "limitesEstatales", label: "Límites estatales" },
      { id: "limitesMunicipales", label: "Límites municipales" },
      {
        id: "elevacionMdeInegi",
        label: "Elevación MDE INEGI",
        helper: "Elevación del terreno derivada del Modelo Digital de Elevación, clasificada por rangos en metros sobre el nivel del mar.",
      },
      { id: "fisiografiaInegi", label: "Provincias fisiográficas INEGI" },
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
  elevacionMdeInegi: false,
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
      nivel_confirmacion_conafor: "Alta",
      nivel_cobertura_smn: "Media",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
    {
      cluster_id: 6,
      n_observaciones: 19092,
      dias_con_conafor: 1690,
      firms_total: 138367,
      cluster_label: "Cluster 6",
      cluster_name: "Baja actividad térmica",
      nivel_actividad_firms: "Baja",
      nivel_confirmacion_conafor: "Baja",
      nivel_cobertura_smn: "Alta",
      color_sugerido: "#2563EB",
      orden_visualizacion: 4,
    },
  ],
  municipio: [],
};

function normalizeClave(value, width) {
  if (value === undefined || value === null || value === "") return "";
  return String(value).padStart(width, "0");
}

export function getNivelUiLabel(nivel) {
  if (nivel === "municipio") return "Municipal";
  if (nivel === "entidad") return "Estatal";
  return "Sin consulta";
}

export { ML_INTERPRETATION_NOTE, clusterLegendItems, CLUSTER_APP_METADATA_BY_ID, MONTH_LABELS, STATE_BY_ID, MUNICIPALITY_BY_CVEGEO, ML_CLUSTER_SUMMARIES };
