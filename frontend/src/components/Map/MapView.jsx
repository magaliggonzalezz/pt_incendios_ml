import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import MapControls from "./MapControls";
import MapLegend from "./MapLegend";
import {
  obtenerCapaTematica,
  obtenerCapaTematicaViewport,
  obtenerEstacionesSmn,
  obtenerGeometriasEstados,
  obtenerGeometriasMunicipios,
} from "../../services/geometrias.service";
import {
  obtenerIncendiosConafor,
  obtenerPuntosFirms,
} from "../../services/puntosMapa.service";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const EMPTY_FEATURE_COLLECTION = { type: "FeatureCollection", features: [] };

const BASE_LAYERS = {
  esri: {
    name: "Satelital",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri",
  },
  osm: {
    name: "OpenStreetMap",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
  },
  topo: {
    name: "Topográfico",
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenTopoMap (CC-BY-SA)",
  },
};

const THEMATIC_STYLES = {
  fisiografia: { color: "#8B5CF6", weight: 1, fillColor: "#8B5CF6", fillOpacity: 0.12 },
  hidrografia: { color: "#38BDF8", weight: 1.2, opacity: 0.85 },
  edafologia: { color: "#A16207", weight: 0.7, fillColor: "#CA8A04", fillOpacity: 0.18 },
  uso_suelo_vegetacion: { color: "#15803D", weight: 0.7, fillColor: "#22C55E", fillOpacity: 0.16 },
};

const STATE_BOUNDARY_STYLE = {
  color: "#F8FAFC",
  weight: 2,
  opacity: 0.95,
  fillOpacity: 0,
};

const MUNICIPAL_BOUNDARY_STYLE = {
  color: "#CBD5E1",
  weight: 1.1,
  opacity: 0.9,
  fillOpacity: 0,
};

const SELECTED_TERRITORY_STYLE = {
  color: "#0F766E",
  weight: 3,
  opacity: 1,
  fillOpacity: 0,
};

const FIRMS_CONFIDENCE_COLORS = {
  low: "#FACC15",
  nominal: "#F97316",
  high: "#DC2626",
};

const PROPERTY_LABELS = {
  cve_ent: "Clave de entidad",
  cve_mun: "Clave de municipio",
  cvegeo: "CVEGEO",
  nomgeo: "Nombre geográfico",
  nom_ent: "Entidad",
  nom_mun: "Municipio",
  nombre_estacion: "Estación",
  situacion_operativa: "Situación operativa",
  fisiografia_nombre: "Provincia fisiográfica",
  corriente_nombre: "Corriente",
  orden_corriente: "Orden de corriente",
  grupo1_nombre: "Grupo de suelo",
  textura_nombre: "Textura",
  usv_descripcion: "Uso de suelo / vegetación",
  fecha_inicio: "Fecha de inicio",
  fecha_fin: "Fecha de fin",
  fecha_termino: "Fecha de término",
  anio_inicio: "Año inicial",
  anio_fin: "Año final",
  cobertura_inicio: "Cobertura desde",
  cobertura_fin: "Cobertura hasta",
};

function normalizeGeoKey(value, length) {
  if (value === undefined || value === null || value === "") return "";
  return String(value).trim().padStart(length, "0");
}

function getFeatureKey(feature, nivelAgregacion) {
  return nivelAgregacion === "municipio"
    ? normalizeGeoKey(feature?.properties?.cvegeo, 5)
    : normalizeGeoKey(feature?.properties?.cve_ent ?? feature?.properties?.cvegeo, 2);
}

function getRowKey(row, nivelAgregacion) {
  return nivelAgregacion === "municipio"
    ? normalizeGeoKey(row?.cvegeo, 5)
    : normalizeGeoKey(row?.cve_ent, 2);
}

function filterFeatureCollection(collection, predicate) {
  if (!collection?.features) return EMPTY_FEATURE_COLLECTION;
  return { ...collection, features: collection.features.filter(predicate) };
}

function bboxToString(bounds) {
  if (!bounds?.isValid?.()) return "";
  return [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMapValue(value, options = {}) {
  if (value === undefined || value === null || value === "") return null;
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return null;
  if (options.number) {
    const number = Number(value);
    if (Number.isFinite(number)) {
      return number.toLocaleString("es-MX", {
        maximumFractionDigits: options.maximumFractionDigits ?? 2,
      });
    }
  }
  return String(value);
}

function friendlyPropertyLabel(key) {
  if (PROPERTY_LABELS[key]) return PROPERTY_LABELS[key];
  return String(key)
    .replace(/^_+/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function propertyRows(props, preferred = []) {
  const used = new Set();
  const rows = [];

  preferred.forEach(([label, key, options]) => {
    const value = formatMapValue(props?.[key], options);
    if (value === null) return;
    used.add(key);
    rows.push([label, value]);
  });

  Object.entries(props || {}).forEach(([key, rawValue]) => {
    if (key.startsWith("__") || used.has(key)) return;
    const value = formatMapValue(rawValue);
    if (value === null) return;
    rows.push([friendlyPropertyLabel(key), value]);
  });

  return rows;
}

function infoRowsHtml(rows) {
  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("");
}

function bindRichInfo(layer, { title, kind = "generic", tooltipRows, popupRows }) {
  const tooltipBody = infoRowsHtml(tooltipRows);
  if (tooltipBody) {
    layer.bindTooltip(
      `<div class="mapFeatureTooltipInner"><div class="mapFeatureTooltipTitle"><span></span>${escapeHtml(title)}</div><dl>${tooltipBody}</dl></div>`,
      { sticky: true, direction: "top", className: `mapFeatureTooltip mapFeaturePopup-${kind}` },
    );
  }

  const popupBody = infoRowsHtml(popupRows);
  if (popupBody) {
    layer.bindPopup(
      `<div class="mapFeaturePopupScroll"><div class="mapFeatureTooltipTitle"><span></span>${escapeHtml(title)}</div><dl>${popupBody}</dl></div>`,
      { className: `mapFeaturePopup mapFeaturePopup-${kind}`, maxWidth: 340 },
    );
  }
}

function bindGenericLayerInfo(feature, layer, { title, kind, preferred = [], tooltipCount = 5 }) {
  const props = feature?.properties || {};
  const rows = propertyRows(props, preferred);
  bindRichInfo(layer, {
    title,
    kind,
    tooltipRows: rows.slice(0, tooltipCount),
    popupRows: rows.slice(0, 40),
  });
}

function firmsConfidenceCategory(props) {
  const category = String(props?.confidence_category || "").toLowerCase();
  if (FIRMS_CONFIDENCE_COLORS[category]) return category;
  const confidence = Number(props?.confidence);
  if (!Number.isFinite(confidence)) return "nominal";
  if (confidence >= 80) return "high";
  if (confidence >= 30) return "nominal";
  return "low";
}

function firmsMarkerStyle(feature) {
  const props = feature?.properties || {};
  const category = firmsConfidenceCategory(props);
  const frp = Math.max(0, Number(props.frp) || 0);
  const radius = Math.min(8, Math.max(3.5, 3.5 + Math.log10(frp + 1) * 1.8));
  const isNight = String(props.daynight || "").toUpperCase() === "N";

  return {
    radius,
    color: isNight ? "#111827" : "#FFF7ED",
    weight: isNight ? 1.8 : 1.4,
    fillColor: FIRMS_CONFIDENCE_COLORS[category],
    fillOpacity: 0.88,
    opacity: 0.95,
  };
}

function conaforImpactColor(value) {
  const impact = String(value || "").toLowerCase();
  if (impact.includes("alto") || impact.includes("severo") || impact.includes("extremo")) return "#7F1D1D";
  if (impact.includes("moderado")) return "#DC2626";
  if (impact.includes("bajo")) return "#F97316";
  return "#B91C1C";
}

function conaforMarkerStyle(feature) {
  const props = feature?.properties || {};
  const superficie = Math.max(0, Number(props.superficie_total_ha) || 0);
  const radius = Math.min(9, Math.max(4.5, 4.5 + Math.log10(superficie + 1) * 1.5));
  return {
    radius,
    color: "#7F1D1D",
    weight: 1.5,
    fillColor: conaforImpactColor(props.tipo_impacto),
    fillOpacity: 0.82,
    opacity: 0.95,
  };
}

function bindFirmsInfo(feature, layer) {
  const props = feature?.properties || {};
  const category = firmsConfidenceCategory(props);
  const confidenceLabel = { low: "Baja", nominal: "Nominal", high: "Alta" }[category];
  const dayNight = String(props.daynight || "").toUpperCase() === "N" ? "Noche" : "Día";

  bindRichInfo(layer, {
    title: "Detección FIRMS",
    kind: "firms",
    tooltipRows: [
      ["Fecha", props.fecha],
      ["Hora", props.acq_time],
      ["Municipio", props.municipio],
      ["Confianza", confidenceLabel],
      ["FRP", formatMapValue(props.frp, { number: true })],
      ["Día / noche", dayNight],
    ],
    popupRows: propertyRows(
      { ...props, confianza_interpretada: confidenceLabel, periodo_dia: dayNight },
      [
        ["Fecha", "fecha"],
        ["Hora de adquisición", "acq_time"],
        ["Estado", "estado"],
        ["Municipio", "municipio"],
        ["Confianza", "confianza_interpretada"],
        ["FRP", "frp", { number: true }],
        ["Día / noche", "periodo_dia"],
        ["Satélite", "satellite"],
        ["Instrumento", "instrument"],
        ["Brillo", "brightness", { number: true }],
        ["Tipo", "type"],
        ["Scan", "scan", { number: true }],
        ["Track", "track", { number: true }],
        ["Versión", "version"],
      ],
    ).slice(0, 40),
  });
}

function bindConaforInfo(feature, layer) {
  const props = feature?.properties || {};
  bindRichInfo(layer, {
    title: "Incendio CONAFOR",
    kind: "conafor",
    tooltipRows: [
      ["Inicio", props.fecha_inicio],
      ["Municipio", props.municipio],
      ["Superficie (ha)", formatMapValue(props.superficie_total_ha, { number: true })],
      ["Impacto", props.tipo_impacto],
      ["Tipo", props.tipo_incendio],
      ["Causa", props.causa],
    ],
    popupRows: propertyRows(props, [
      ["Inicio", "fecha_inicio"],
      ["Término", "fecha_termino"],
      ["Estado", "estado"],
      ["Municipio", "municipio"],
      ["Clave", "clave_incendio"],
      ["Superficie total (ha)", "superficie_total_ha", { number: true }],
      ["Tipo de impacto", "tipo_impacto"],
      ["Tipo de incendio", "tipo_incendio"],
      ["Causa", "causa"],
      ["Causa específica", "causa_especifica"],
      ["Vegetación", "tipo_vegetacion"],
      ["Régimen de fuego", "regimen_fuego"],
      ["Región", "region"],
      ["Predio", "predio"],
      ["Duración", "duracion"],
      ["Detección", "deteccion"],
      ["Llegada", "llegada"],
    ]).slice(0, 40),
  });
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function stationMatchesOperationalFilter(feature, filtros) {
  const status = normalizeText(feature?.properties?.situacion_operativa);
  if (!status) return true;
  if (status.includes("operando") || status.includes("operativa")) return filtros?.operando !== false;
  if (status.includes("suspend")) return filtros?.suspendida !== false;
  return true;
}

function stationMatchesTerritory(feature, cveEnt) {
  if (!cveEnt) return true;
  const featureCveEnt = normalizeGeoKey(
    feature?.properties?.cve_ent ?? feature?.properties?.CVE_ENT,
    2,
  );
  return featureCveEnt ? featureCveEnt === cveEnt : true;
}

function stationCoversPeriod(feature, scope) {
  if (!scope?.anio) return true;
  const props = feature?.properties || {};
  const targetYear = Number(scope.anio);
  const targetMonth = scope.tipoPeriodo === "anio_mes" ? Number(scope.mes) : null;

  const start = props.fecha_inicio ?? props.fecha_min ?? props.cobertura_inicio ?? props.inicio_datos;
  const end = props.fecha_fin ?? props.fecha_max ?? props.cobertura_fin ?? props.fin_datos;
  if (start || end) {
    const startText = start ? String(start).slice(0, 10) : `${targetYear}-01-01`;
    const endText = end ? String(end).slice(0, 10) : `${targetYear}-12-31`;
    const from = targetMonth ? `${targetYear}-${String(targetMonth).padStart(2, "0")}-01` : `${targetYear}-01-01`;
    const to = targetMonth ? `${targetYear}-${String(targetMonth).padStart(2, "0")}-31` : `${targetYear}-12-31`;
    return startText <= to && endText >= from;
  }

  const startYear = Number(props.anio_inicio ?? props.anio_min ?? props.year_min);
  const endYear = Number(props.anio_fin ?? props.anio_max ?? props.year_max);
  if (Number.isFinite(startYear) || Number.isFinite(endYear)) {
    return (!Number.isFinite(startYear) || targetYear >= startYear) &&
      (!Number.isFinite(endYear) || targetYear <= endYear);
  }

  return true;
}

function MapViewportTracker({ onChange }) {
  const map = useMapEvents({
    moveend() {
      onChange(bboxToString(map.getBounds()));
    },
    zoomend() {
      onChange(bboxToString(map.getBounds()));
    },
  });

  useEffect(() => {
    onChange(bboxToString(map.getBounds()));
  }, [map, onChange]);

  return null;
}

function MapResizeInvalidator({ watchKey }) {
  const map = useMap();

  useEffect(() => {
    const invalidate = () => window.requestAnimationFrame(() => map.invalidateSize());
    invalidate();
    window.addEventListener("resize", invalidate);
    return () => window.removeEventListener("resize", invalidate);
  }, [map]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => map.invalidateSize(), 220);
    return () => window.clearTimeout(timeoutId);
  }, [map, watchKey]);

  return null;
}

function MapPopupCloser() {
  const map = useMap();

  useEffect(() => {
    const closePopupFromOutside = (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest(".leaflet-popup")) return;
      if (target.closest(".leaflet-interactive")) return;
      map.closePopup();
    };

    document.addEventListener("pointerdown", closePopupFromOutside, true);
    return () => document.removeEventListener("pointerdown", closePopupFromOutside, true);
  }, [map]);

  return null;
}

function FitGeoJsonBounds({ geojson, enabled, fitKey }) {
  const map = useMap();

  useEffect(() => {
    if (!enabled || !geojson?.features?.length) return;
    const layer = L.geoJSON(geojson);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 32], maxZoom: 11 });
  }, [map, geojson, enabled, fitKey]);

  return null;
}

export default function MapView({
  consultaActiva = null,
  consultaEjecutada = null,
  resumenConsulta = null,
  onConsultaChange,
  onConsultar,
  leftPanelOpen = false,
  rightPanelOpen = false,
  selectedMlCluster = null,
}) {
  const [baseLayerId, setBaseLayerId] = useState("esri");
  const [estadosGeojson, setEstadosGeojson] = useState(EMPTY_FEATURE_COLLECTION);
  const [municipiosGeojson, setMunicipiosGeojson] = useState(EMPTY_FEATURE_COLLECTION);
  const [geometryError, setGeometryError] = useState(null);
  const [layerError, setLayerError] = useState(null);
  const [viewportBbox, setViewportBbox] = useState("");
  const [overlays, setOverlays] = useState({
    firms: EMPTY_FEATURE_COLLECTION,
    conafor: EMPTY_FEATURE_COLLECTION,
    smn: EMPTY_FEATURE_COLLECTION,
    fisiografia: EMPTY_FEATURE_COLLECTION,
    hidrografia: EMPTY_FEATURE_COLLECTION,
    edafologia: EMPTY_FEATURE_COLLECTION,
    usoSueloVegetacion: EMPTY_FEATURE_COLLECTION,
  });

  const activeLayer = BASE_LAYERS[baseLayerId];
  const rows = resumenConsulta?.rows ?? [];
  const mapScope = consultaEjecutada;
  const overlayScope = mapScope || consultaActiva;
  const nivelMapa = mapScope?.nivelAgregacion || overlayScope?.nivelAgregacion || "entidad";
  const capasActivas = consultaActiva?.capasActivas || {};
  const filtrosSmn = consultaActiva?.filtrosSmn || {};
  const cveEntCapas = normalizeGeoKey(overlayScope?.cveEnt, 2);
  const cvegeoSeleccionado = normalizeGeoKey(overlayScope?.cvegeo, 5);

  const setOverlay = (key, data) => {
    setOverlays((prev) => ({ ...prev, [key]: data || EMPTY_FEATURE_COLLECTION }));
  };

  useEffect(() => {
    let active = true;
    obtenerGeometriasEstados()
      .then((data) => {
        if (active) setEstadosGeojson(data || EMPTY_FEATURE_COLLECTION);
      })
      .catch((error) => {
        if (active) setGeometryError(error.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setMunicipiosGeojson(EMPTY_FEATURE_COLLECTION);
    if (!cveEntCapas) return () => { active = false; };

    obtenerGeometriasMunicipios(cveEntCapas)
      .then((data) => {
        if (active) setMunicipiosGeojson(data || EMPTY_FEATURE_COLLECTION);
      })
      .catch((error) => {
        if (active) setGeometryError(error.message);
      });

    return () => {
      active = false;
    };
  }, [cveEntCapas]);

  useEffect(() => {
    let active = true;
    setOverlay("smn", EMPTY_FEATURE_COLLECTION);
    if (!capasActivas.estacionesSmn) return () => { active = false; };

    obtenerEstacionesSmn()
      .then((data) => {
        if (active) setOverlay("smn", data);
      })
      .catch((error) => {
        if (active) setLayerError(`SMN: ${error.message}`);
      });

    return () => {
      active = false;
    };
  }, [capasActivas.estacionesSmn]);

  useEffect(() => {
    let active = true;
    setOverlay("fisiografia", EMPTY_FEATURE_COLLECTION);
    setOverlay("hidrografia", EMPTY_FEATURE_COLLECTION);
    if (!cveEntCapas) return () => { active = false; };

    const tasks = [];
    if (capasActivas.fisiografiaInegi) {
      tasks.push(
        obtenerCapaTematica("fisiografia", cveEntCapas).then((data) => {
          if (active) setOverlay("fisiografia", data);
        }),
      );
    }
    if (capasActivas.corrientesAguaInegi) {
      tasks.push(
        obtenerCapaTematica("hidrografia", cveEntCapas).then((data) => {
          if (active) setOverlay("hidrografia", data);
        }),
      );
    }

    Promise.allSettled(tasks).then((results) => {
      if (!active) return;
      const errors = results.filter((result) => result.status === "rejected");
      if (errors.length) setLayerError(errors.map((result) => result.reason?.message).filter(Boolean).join(" | "));
    });

    return () => {
      active = false;
    };
  }, [cveEntCapas, capasActivas.fisiografiaInegi, capasActivas.corrientesAguaInegi]);

  useEffect(() => {
    let active = true;
    setOverlay("edafologia", EMPTY_FEATURE_COLLECTION);
    setOverlay("usoSueloVegetacion", EMPTY_FEATURE_COLLECTION);
    if (!cveEntCapas || !viewportBbox) return () => { active = false; };

    const tasks = [];
    if (capasActivas.edafologiaInegi) {
      tasks.push(
        obtenerCapaTematicaViewport("edafologia", cveEntCapas, viewportBbox).then((data) => {
          if (active) setOverlay("edafologia", data);
        }),
      );
    }
    if (capasActivas.usoSueloVegetacionInegi) {
      tasks.push(
        obtenerCapaTematicaViewport("uso_suelo_vegetacion", cveEntCapas, viewportBbox).then((data) => {
          if (active) setOverlay("usoSueloVegetacion", data);
        }),
      );
    }

    Promise.allSettled(tasks).then((results) => {
      if (!active) return;
      const errors = results.filter((result) => result.status === "rejected");
      if (errors.length) setLayerError(errors.map((result) => result.reason?.message).filter(Boolean).join(" | "));
    });

    return () => {
      active = false;
    };
  }, [
    cveEntCapas,
    viewportBbox,
    capasActivas.edafologiaInegi,
    capasActivas.usoSueloVegetacionInegi,
  ]);

  useEffect(() => {
    let active = true;
    setOverlay("firms", EMPTY_FEATURE_COLLECTION);
    setOverlay("conafor", EMPTY_FEATURE_COLLECTION);

    if (!overlayScope?.anio) return () => { active = false; };

    const puntosParams = {
      anio: overlayScope.anio,
      mes: overlayScope.tipoPeriodo === "anio_mes" ? overlayScope.mes : undefined,
      cve_ent: overlayScope.cveEnt || undefined,
      cvegeo: overlayScope.cvegeo || undefined,
    };

    const tasks = [];
    if (capasActivas.puntosCalorFirms) {
      tasks.push(
        obtenerPuntosFirms(puntosParams).then((data) => {
          if (active) setOverlay("firms", data);
        }),
      );
    }
    if (capasActivas.incendiosConafor) {
      tasks.push(
        obtenerIncendiosConafor(puntosParams).then((data) => {
          if (active) setOverlay("conafor", data);
        }),
      );
    }

    Promise.allSettled(tasks).then((results) => {
      if (!active) return;
      const errors = results.filter((result) => result.status === "rejected");
      if (errors.length) setLayerError(errors.map((result) => result.reason?.message).filter(Boolean).join(" | "));
    });

    return () => {
      active = false;
    };
  }, [
    capasActivas.puntosCalorFirms,
    capasActivas.incendiosConafor,
    overlayScope?.anio,
    overlayScope?.mes,
    overlayScope?.tipoPeriodo,
    overlayScope?.cveEnt,
    overlayScope?.cvegeo,
  ]);

  const estadoSeleccionadoGeojson = useMemo(() => {
    if (!cveEntCapas) return EMPTY_FEATURE_COLLECTION;
    return filterFeatureCollection(
      estadosGeojson,
      (feature) => getFeatureKey(feature, "entidad") === cveEntCapas,
    );
  }, [estadosGeojson, cveEntCapas]);

  const municipioSeleccionadoGeojson = useMemo(() => {
    if (!cvegeoSeleccionado) return EMPTY_FEATURE_COLLECTION;
    return filterFeatureCollection(
      municipiosGeojson,
      (feature) => getFeatureKey(feature, "municipio") === cvegeoSeleccionado,
    );
  }, [municipiosGeojson, cvegeoSeleccionado]);

  const territorioSeleccionadoGeojson = cvegeoSeleccionado
    ? municipioSeleccionadoGeojson
    : estadoSeleccionadoGeojson;

  const limitesEstatalesGeojson = useMemo(() => {
    if (!cveEntCapas) return estadosGeojson;
    return estadoSeleccionadoGeojson;
  }, [estadosGeojson, estadoSeleccionadoGeojson, cveEntCapas]);

  const smnFiltrado = useMemo(() => {
    if (!overlays.smn?.features) return EMPTY_FEATURE_COLLECTION;
    return filterFeatureCollection(overlays.smn, (feature) => {
      if (!stationMatchesOperationalFilter(feature, filtrosSmn)) return false;
      if (!stationMatchesTerritory(feature, cveEntCapas)) return false;
      if (filtrosSmn.alcance === "periodo" && !stationCoversPeriod(feature, overlayScope)) return false;
      return true;
    });
  }, [overlays.smn, filtrosSmn, cveEntCapas, overlayScope]);

  const rowByKey = useMemo(() => {
    const map = new Map();
    rows.forEach((row) => {
      const key = getRowKey(row, nivelMapa);
      if (key) map.set(key, row);
    });
    return map;
  }, [rows, nivelMapa]);

  const resultadoBaseGeojson = useMemo(() => {
    if (!mapScope) return EMPTY_FEATURE_COLLECTION;
    const source = mapScope.nivelAgregacion === "municipio" ? municipiosGeojson : estadosGeojson;
    if (!source?.features) return EMPTY_FEATURE_COLLECTION;

    if (mapScope.nivelAgregacion === "municipio" && mapScope.cvegeo) {
      const target = normalizeGeoKey(mapScope.cvegeo, 5);
      return filterFeatureCollection(source, (feature) => getFeatureKey(feature, "municipio") === target);
    }
    if (mapScope.nivelAgregacion === "entidad" && mapScope.cveEnt) {
      const target = normalizeGeoKey(mapScope.cveEnt, 2);
      return filterFeatureCollection(source, (feature) => getFeatureKey(feature, "entidad") === target);
    }
    return source;
  }, [mapScope, municipiosGeojson, estadosGeojson]);

  const displayGeojson = useMemo(() => {
    if (!resultadoBaseGeojson?.features) return EMPTY_FEATURE_COLLECTION;
    return {
      ...resultadoBaseGeojson,
      features: resultadoBaseGeojson.features.map((feature) => {
        const key = getFeatureKey(feature, nivelMapa);
        const row = rowByKey.get(key) ?? null;
        const clusterMatches =
          selectedMlCluster === null ||
          selectedMlCluster === "" ||
          Number(row?.cluster) === Number(selectedMlCluster);

        return {
          ...feature,
          properties: {
            ...(feature.properties || {}),
            __map_key: key,
            __resultado: row,
            __map_style: {
              color: row ? "#FFFFFF" : "rgba(255,255,255,.65)",
              weight: row ? 1.6 : 0.8,
              fillColor: row?.color_sugerido_app || "#64748B",
              fillOpacity: row ? (clusterMatches ? 0.72 : 0.16) : 0.05,
            },
          },
        };
      }),
    };
  }, [resultadoBaseGeojson, rowByKey, nivelMapa, selectedMlCluster]);

  const styleFeature = (feature) => feature?.properties?.__map_style || {
    color: "rgba(255,255,255,.65)",
    weight: 0.8,
    fillColor: "#64748B",
    fillOpacity: 0.05,
  };

  const onEachResultFeature = (feature, layer) => {
    const key = feature?.properties?.__map_key || getFeatureKey(feature, nivelMapa);
    const row = feature?.properties?.__resultado || null;
    const name = feature?.properties?.nomgeo || feature?.properties?.nom_ent || feature?.properties?.nom_mun || row?.nombre_municipio || row?.nombre_entidad || key;
    if (!row) return;

    bindRichInfo(layer, {
      title: name,
      kind: "ml",
      tooltipRows: [
        ["Cluster", row.cluster],
        ["Observaciones", row.observaciones],
        ["FIRMS", row.firms_detecciones ?? 0],
        ["CONAFOR", row.conafor_eventos ?? 0],
      ],
      popupRows: propertyRows(row, [
        ["Clave", nivelMapa === "municipio" ? "cvegeo" : "cve_ent"],
        ["Cluster", "cluster"],
        ["Estado ML", "estado_app"],
        ["Etiqueta", "etiqueta_final"],
      ]).slice(0, 40),
    });
  };

  const fitKey = `${overlayScope?.nivelAgregacion || "entidad"}-${cveEntCapas || "mx"}-${cvegeoSeleccionado || "all"}`;
  const renderKey = `${fitKey}-${resumenConsulta?.periodo || "sin-resultados"}-${rows.length}-${selectedMlCluster ?? "all"}`;

  return (
    <div
      className="mapWrap"
      role="region"
      aria-label="Mapa interactivo de incendios forestales en México"
      aria-describedby="map-accessible-summary"
    >
      <p id="map-accessible-summary" className="srOnly">
        Mapa interactivo de México con resultados ML y capas geográficas seleccionables.
      </p>
      <MapContainer
        center={DEFAULT_VIEW.center}
        zoom={DEFAULT_VIEW.zoom}
        minZoom={3}
        className="leafletMap"
        zoomControl={false}
        keyboard={true}
        preferCanvas={true}
      >
        <TileLayer url={activeLayer.url} attribution={activeLayer.attribution} />
        <MapViewportTracker onChange={setViewportBbox} />

        {capasActivas.limitesEstatales && limitesEstatalesGeojson?.features?.length ? (
          <GeoJSON
            key={`lim-est-${cveEntCapas || "mx"}`}
            data={limitesEstatalesGeojson}
            style={() => STATE_BOUNDARY_STYLE}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.nomgeo || feature?.properties?.nom_ent || "Entidad federativa",
              kind: "limites",
              preferred: [["Entidad", "nomgeo"], ["Clave", "cve_ent"]],
              tooltipCount: 3,
            })}
          />
        ) : null}

        {capasActivas.limitesMunicipales && municipiosGeojson?.features?.length ? (
          <GeoJSON
            key={`lim-mun-${cveEntCapas}`}
            data={municipiosGeojson}
            style={() => MUNICIPAL_BOUNDARY_STYLE}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.nomgeo || feature?.properties?.nom_mun || "Municipio",
              kind: "limites",
              preferred: [["Municipio", "nomgeo"], ["CVEGEO", "cvegeo"]],
              tooltipCount: 3,
            })}
          />
        ) : null}

        {territorioSeleccionadoGeojson?.features?.length ? (
          <GeoJSON
            key={`territorio-${fitKey}`}
            data={territorioSeleccionadoGeojson}
            style={() => SELECTED_TERRITORY_STYLE}
            interactive={false}
          />
        ) : null}

        {displayGeojson?.features?.length ? (
          <GeoJSON
            key={renderKey}
            data={displayGeojson}
            style={styleFeature}
            onEachFeature={onEachResultFeature}
          />
        ) : null}

        {overlays.fisiografia?.features?.length ? (
          <GeoJSON
            key={`fisiografia-${cveEntCapas}`}
            data={overlays.fisiografia}
            style={() => THEMATIC_STYLES.fisiografia}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.fisiografia_nombre || "Fisiografía INEGI",
              kind: "fisiografia",
              preferred: [["Provincia", "fisiografia_nombre"]],
            })}
          />
        ) : null}

        {overlays.hidrografia?.features?.length ? (
          <GeoJSON
            key={`hidrografia-${cveEntCapas}`}
            data={overlays.hidrografia}
            style={() => THEMATIC_STYLES.hidrografia}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.corriente_nombre || "Corriente de agua INEGI",
              kind: "hidrografia",
              preferred: [["Corriente", "corriente_nombre"], ["Orden", "orden_corriente"]],
            })}
          />
        ) : null}

        {overlays.edafologia?.features?.length ? (
          <GeoJSON
            key={`edafologia-${cveEntCapas}-${viewportBbox}`}
            data={overlays.edafologia}
            style={() => THEMATIC_STYLES.edafologia}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.grupo1_nombre || "Edafología INEGI",
              kind: "edafologia",
              preferred: [["Suelo", "grupo1_nombre"], ["Textura", "textura_nombre"]],
            })}
          />
        ) : null}

        {overlays.usoSueloVegetacion?.features?.length ? (
          <GeoJSON
            key={`usv-${cveEntCapas}-${viewportBbox}`}
            data={overlays.usoSueloVegetacion}
            style={() => THEMATIC_STYLES.uso_suelo_vegetacion}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.usv_descripcion || "Uso de suelo y vegetación INEGI",
              kind: "uso-suelo",
              preferred: [["Uso / vegetación", "usv_descripcion"]],
            })}
          />
        ) : null}

        {smnFiltrado?.features?.length ? (
          <GeoJSON
            key={`smn-${cveEntCapas || "mx"}-${filtrosSmn.alcance || "todas"}-${filtrosSmn.operando}-${filtrosSmn.suspendida}`}
            data={smnFiltrado}
            pointToLayer={(_, latlng) => L.circleMarker(latlng, {
              radius: 4,
              color: "#0F766E",
              weight: 1,
              fillColor: "#14B8A6",
              fillOpacity: 0.8,
            })}
            onEachFeature={(feature, layer) => bindGenericLayerInfo(feature, layer, {
              title: feature?.properties?.nombre_estacion || "Estación SMN-CONAGUA",
              kind: "smn",
              preferred: [
                ["Estación", "nombre_estacion"],
                ["Situación", "situacion_operativa"],
                ["Cobertura desde", "cobertura_inicio"],
                ["Cobertura hasta", "cobertura_fin"],
                ["Fecha inicial", "fecha_inicio"],
                ["Fecha final", "fecha_fin"],
              ],
              tooltipCount: 6,
            })}
          />
        ) : null}

        {overlays.conafor?.features?.length ? (
          <GeoJSON
            key={`conafor-${fitKey}`}
            data={overlays.conafor}
            pointToLayer={(feature, latlng) => L.circleMarker(latlng, conaforMarkerStyle(feature))}
            onEachFeature={bindConaforInfo}
          />
        ) : null}

        {overlays.firms?.features?.length ? (
          <GeoJSON
            key={`firms-${fitKey}`}
            data={overlays.firms}
            pointToLayer={(feature, latlng) => L.circleMarker(latlng, firmsMarkerStyle(feature))}
            onEachFeature={bindFirmsInfo}
          />
        ) : null}

        <FitGeoJsonBounds
          geojson={territorioSeleccionadoGeojson}
          enabled={Boolean(cveEntCapas || cvegeoSeleccionado)}
          fitKey={fitKey}
        />
        <MapResizeInvalidator watchKey={`${leftPanelOpen}-${rightPanelOpen}-${baseLayerId}`} />
        <MapPopupCloser />
        <MapControls
          defaultView={DEFAULT_VIEW}
          baseLayerId={baseLayerId}
          onChangeLayer={setBaseLayerId}
          layers={BASE_LAYERS}
          consultaActiva={consultaActiva}
          onConsultaChange={onConsultaChange}
          onConsultar={onConsultar}
          rightPanelOpen={rightPanelOpen}
        />
      </MapContainer>

      {geometryError ? <div className="mapGeometryError">No fue posible cargar la geometría: {geometryError}</div> : null}
      {layerError ? <div className="mapGeometryError">No fue posible cargar una capa: {layerError}</div> : null}
      <MapLegend
        resumenConsulta={resumenConsulta}
        rightPanelOpen={rightPanelOpen}
        selectedMlCluster={selectedMlCluster}
      />
    </div>
  );
}
