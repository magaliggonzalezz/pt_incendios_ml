import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import MapControls from "./MapControls";
import MapLegend from "./MapLegend";
import {
  obtenerCapaTematicaViewport,
  obtenerEstacionesSmn,
  obtenerGeometriasEstados,
  obtenerGeometriasMunicipios,
} from "../../services/geometrias.service";
import { obtenerIncendiosConafor, obtenerPuntosFirms } from "../../services/puntosMapa.service";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const EMPTY_FEATURE_COLLECTION = { type: "FeatureCollection", features: [] };
const VIEWPORT_DEBOUNCE_MS = 400;

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

const PHYSIOGRAPHY_COLORS = [
  "#F87171", "#D8B4FE", "#FDE68A", "#22C55E", "#EC4899", "#BAE6FD", "#EF4444", "#FDBA74",
  "#A78BFA", "#34D399", "#F9A8D4", "#93C5FD", "#C4B5FD", "#FCA5A5", "#67E8F9", "#A3E635", "#FBBF24", "#2DD4BF",
];
const SOIL_COLORS = [
  "#C4A484", "#8B6F47", "#A67C52", "#D7C4A3", "#B08968", "#9C6644", "#C9ADA7", "#A8A29E",
  "#86A873", "#7F9E71", "#C2B280", "#D4A373", "#B7B7A4", "#A98467", "#8D6E63", "#DDBEA9",
];
const LAND_USE_COLORS = [
  "#4ADE80", "#16A34A", "#65A30D", "#84CC16", "#BEF264", "#FDE047", "#FACC15", "#EAB308",
  "#FB7185", "#F43F5E", "#E879F9", "#C026D3", "#A855F7", "#38BDF8", "#06B6D4", "#14B8A6",
  "#D6D3D1", "#A8A29E", "#FDBA74", "#F59E0B",
];

const BOUNDARY_STYLES = {
  esri: {
    state: { color: "#F8FAFC", weight: 2.2, opacity: 0.98, fillOpacity: 0 },
    stateHalo: { color: "#0F172A", weight: 4.8, opacity: 0.62, fillOpacity: 0 },
    municipality: { color: "#E2E8F0", weight: 1.15, opacity: 0.94, fillOpacity: 0 },
    municipalityHalo: { color: "#0F172A", weight: 2.8, opacity: 0.48, fillOpacity: 0 },
  },
  osm: {
    state: { color: "#0F3D3A", weight: 2.2, opacity: 0.98, fillOpacity: 0 },
    stateHalo: { color: "#FFFFFF", weight: 4.8, opacity: 0.94, fillOpacity: 0 },
    municipality: { color: "#1F5D58", weight: 1.2, opacity: 0.96, fillOpacity: 0 },
    municipalityHalo: { color: "#FFFFFF", weight: 3, opacity: 0.9, fillOpacity: 0 },
  },
  topo: {
    state: { color: "#063E3A", weight: 2.3, opacity: 1, fillOpacity: 0 },
    stateHalo: { color: "#FFFFFF", weight: 5.2, opacity: 0.96, fillOpacity: 0 },
    municipality: { color: "#155E59", weight: 1.25, opacity: 0.98, fillOpacity: 0 },
    municipalityHalo: { color: "#FFFFFF", weight: 3.2, opacity: 0.92, fillOpacity: 0 },
  },
};

const SELECTED_TERRITORY_STYLE = { color: "#0F766E", weight: 3, opacity: 1, fillOpacity: 0 };
const FIRMS_CONFIDENCE_COLORS = { low: "#FACC15", nominal: "#F97316", high: "#DC2626" };
const FIRMS_TYPE_LABELS = {
  0: "0 · Incendio de vegetación presunto",
  1: "1 · Volcán activo",
  2: "2 · Otra fuente terrestre estática",
  3: "3 · Detección offshore",
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
  return nivelAgregacion === "municipio" ? normalizeGeoKey(row?.cvegeo, 5) : normalizeGeoKey(row?.cve_ent, 2);
}

function filterFeatureCollection(collection, predicate) {
  if (!collection?.features) return EMPTY_FEATURE_COLLECTION;
  return { ...collection, features: collection.features.filter(predicate) };
}

function pointInRing(point, ring) {
  if (!Array.isArray(ring) || ring.length < 3) return false;
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = Number(ring[i]?.[0]);
    const yi = Number(ring[i]?.[1]);
    const xj = Number(ring[j]?.[0]);
    const yj = Number(ring[j]?.[1]);
    if (![xi, yi, xj, yj].every(Number.isFinite)) continue;
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / ((yj - yi) || Number.EPSILON) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

function pointInPolygonCoordinates(point, polygon) {
  if (!Array.isArray(polygon) || !polygon.length || !pointInRing(point, polygon[0])) return false;
  for (let i = 1; i < polygon.length; i += 1) if (pointInRing(point, polygon[i])) return false;
  return true;
}

function pointInGeometry(point, geometry) {
  if (!geometry || !Array.isArray(point) || point.length < 2) return false;
  if (geometry.type === "Polygon") return pointInPolygonCoordinates(point, geometry.coordinates);
  if (geometry.type === "MultiPolygon") return geometry.coordinates.some((polygon) => pointInPolygonCoordinates(point, polygon));
  return false;
}

function bboxToString(bounds) {
  if (!bounds?.isValid?.()) return "";
  return [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
}

function isAbortError(error) {
  return error?.name === "AbortError" || /aborted|abort/i.test(String(error?.message || ""));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#039;");
}

function formatMapValue(value, options = {}) {
  if (value === undefined || value === null || value === "") return null;
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return null;
  if (options.number) {
    const number = Number(value);
    if (Number.isFinite(number)) return number.toLocaleString("es-MX", { maximumFractionDigits: options.maximumFractionDigits ?? 2 });
  }
  return String(value);
}

function firstProp(props, keys = []) {
  for (const key of keys) {
    const value = props?.[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return null;
}

function orderedRows(props, order = []) {
  return order.map(([label, keyOrGetter, options]) => {
    const raw = typeof keyOrGetter === "function" ? keyOrGetter(props) : props?.[keyOrGetter];
    return [label, formatMapValue(raw, options)];
  }).filter(([, value]) => value !== null);
}

function infoRowsHtml(rows) {
  return rows.filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("");
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
  if (!popupBody) return;

  layer.bindPopup(
    `<div class="mapFeaturePopupScroll"><div class="mapFeatureTooltipTitle"><span></span>${escapeHtml(title)}</div><dl>${popupBody}</dl></div>`,
    { className: `mapFeaturePopup mapFeaturePopup-${kind}`, maxWidth: 350, keepInView: true, autoPan: true },
  );

  layer.on("popupopen", (event) => {
    window.dispatchEvent(new CustomEvent("map:feature-popup-open"));
    const popup = event.popup;
    const leftOpen = Boolean(document.querySelector(".leftPanel.open"));
    const rightOpen = Boolean(document.querySelector(".rightPanel.open"));
    popup.options.autoPanPaddingTopLeft = L.point(leftOpen ? 324 : 20, 76);
    popup.options.autoPanPaddingBottomRight = L.point(rightOpen ? 324 : 20, 64);
    window.requestAnimationFrame(() => popup._adjustPan?.());
  });
}

function hashIndex(value, size) {
  const text = String(value ?? "Sin dato");
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0) % size;
}

function categoryColor(value, palette) {
  return palette[hashIndex(value, palette.length)];
}

function thematicOutline(baseLayerId) {
  return baseLayerId === "esri" ? "rgba(255,255,255,.88)" : "rgba(15,23,42,.72)";
}

function thematicFillOpacity(baseLayerId, kind) {
  if (baseLayerId === "esri") return kind === "soil" ? 0.52 : 0.56;
  if (baseLayerId === "topo") return kind === "soil" ? 0.50 : 0.54;
  return kind === "soil" ? 0.46 : 0.50;
}

function physiographyStyle(feature, baseLayerId) {
  const props = feature?.properties || {};
  const value = firstProp(props, ["fisiografia_nombre", "fisiografia_clave", "provincia", "PROVINCIA"]);
  const fillColor = categoryColor(value, PHYSIOGRAPHY_COLORS);
  return { color: thematicOutline(baseLayerId), weight: 1, fillColor, fillOpacity: thematicFillOpacity(baseLayerId, "physiography"), opacity: 0.94 };
}

function soilStyle(feature, baseLayerId) {
  const props = feature?.properties || {};
  const value = firstProp(props, ["grupo1_nombre", "grupo1", "GRUPO1", "clave_wrb", "CLAVE_WRB"]);
  const fillColor = categoryColor(value, SOIL_COLORS);
  return { color: thematicOutline(baseLayerId), weight: 0.8, fillColor, fillOpacity: thematicFillOpacity(baseLayerId, "soil"), opacity: 0.9 };
}

function landUseStyle(feature, baseLayerId) {
  const props = feature?.properties || {};
  const value = firstProp(props, ["usv_descripcion", "usv_clave", "descripcion", "DESCRIPCION"]);
  const fillColor = categoryColor(value, LAND_USE_COLORS);
  return { color: thematicOutline(baseLayerId), weight: 0.75, fillColor, fillOpacity: thematicFillOpacity(baseLayerId, "landUse"), opacity: 0.9 };
}

function hydrologyStyle(feature) {
  const order = Number(firstProp(feature?.properties || {}, ["orden_corriente", "orden", "ORDEN"]));
  const normalized = Number.isFinite(order) ? Math.max(0, Math.min(7, order)) : 1;
  return { color: "#0284C7", weight: 0.75 + normalized * 0.18, opacity: 0.82 };
}

function legendItems(features, getter, palette) {
  const seen = new Map();
  for (const feature of features || []) {
    const value = getter(feature?.properties || {});
    if (value === undefined || value === null || value === "") continue;
    const key = String(value);
    if (!seen.has(key)) seen.set(key, { label: key, color: categoryColor(key, palette) });
  }
  const all = [...seen.values()].sort((a, b) => a.label.localeCompare(b.label, "es-MX"));
  return { items: all, total: all.length };
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
  return { radius, color: isNight ? "#111827" : "#FFF7ED", weight: isNight ? 1.8 : 1.4, fillColor: FIRMS_CONFIDENCE_COLORS[category], fillOpacity: 0.88, opacity: 0.95 };
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
  return { radius, color: "#7F1D1D", weight: 1.5, fillColor: conaforImpactColor(props.tipo_impacto), fillOpacity: 0.82, opacity: 0.95 };
}

function bindFirmsInfo(feature, layer) {
  const props = feature?.properties || {};
  const category = firmsConfidenceCategory(props);
  const confidenceLabel = { low: "Baja", nominal: "Nominal", high: "Alta" }[category];
  const dayNight = String(props.daynight || "").toUpperCase() === "N" ? "Noche" : "Día";
  const typeLabel = FIRMS_TYPE_LABELS[Number(props.type)] || props.type;
  const displayProps = { ...props, confianza_interpretada: confidenceLabel, periodo_dia: dayNight, tipo_interpretado: typeLabel };
  bindRichInfo(layer, {
    title: "Anomalía térmica FIRMS",
    kind: "firms",
    tooltipRows: orderedRows(displayProps, [
      ["Estado", "estado"], ["Municipio", "municipio"], ["Fecha", "fecha"], ["Hora", "acq_time"],
      ["Categoría de confianza", "confianza_interpretada"], ["FRP", "frp", { number: true }],
    ]),
    popupRows: orderedRows(displayProps, [
      ["Estado", "estado"], ["Municipio", "municipio"], ["CVEGEO", "cvegeo"], ["Clave de entidad", "cve_ent"], ["Clave de municipio", "cve_mun"],
      ["Fecha", "fecha"], ["Hora de adquisición", "acq_time"], ["Satélite", "satellite"], ["Instrumento", "instrument"],
      ["Confianza", "confidence", { number: true }], ["Categoría de confianza", "confianza_interpretada"], ["FRP", "frp", { number: true }],
      ["Día / noche", "periodo_dia"], ["Brillo", "brightness", { number: true }], ["Tipo", "tipo_interpretado"],
      ["Scan", "scan", { number: true }], ["Track", "track", { number: true }],
    ]),
  });
}

function bindConaforInfo(feature, layer) {
  const props = feature?.properties || {};
  bindRichInfo(layer, {
    title: "Incendio CONAFOR",
    kind: "conafor",
    tooltipRows: orderedRows(props, [
      ["Estado", "estado"], ["Municipio", "municipio"], ["Inicio", "fecha_inicio"], ["Superficie (ha)", "superficie_total_ha", { number: true }], ["Tipo", "tipo_incendio"], ["Causa", "causa"],
    ]),
    popupRows: orderedRows(props, [
      ["Estado", "estado"], ["Municipio", "municipio"], ["CVEGEO", "cvegeo"], ["Clave de entidad", "cve_ent"], ["Clave de municipio", "cve_mun"],
      ["Inicio", "fecha_inicio"], ["Término", "fecha_termino"], ["Clave del incendio", "clave_incendio"], ["Superficie total (ha)", "superficie_total_ha", { number: true }],
      ["Categoría de superficie", "superficie_categoria"], ["Tipo de impacto", "tipo_impacto"], ["Tipo de incendio", "tipo_incendio"], ["Causa", "causa"], ["Causa específica", "causa_especifica"],
      ["Vegetación", "tipo_vegetacion"], ["Régimen de fuego", "regimen_fuego"], ["Región", "region"], ["Predio", "predio"],
      ["Arbolado adulto", "arbolado_adulto", { number: true }], ["Arbustivo", "arbustivo", { number: true }], ["Herbáceo", "herbaceo", { number: true }],
      ["Hojarasca", "hojarasca", { number: true }], ["Renuevo", "renuevo", { number: true }], ["Duración", "duracion"], ["Detección", "deteccion"], ["Llegada", "llegada"],
    ]),
  });
}

function bindStateInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["nomgeo", "nom_ent", "NOM_ENT"]);
  const rows = orderedRows(props, [["Estado", () => estado], ["Clave de entidad", () => firstProp(props, ["cve_ent", "CVE_ENT", "cvegeo", "CVEGEO"])]]);
  bindRichInfo(layer, { title: estado || "Entidad federativa", kind: "limites", tooltipRows: rows, popupRows: rows });
}

function bindMunicipalityInfo(feature, layer) {
  const props = feature?.properties || {};
  const municipio = firstProp(props, ["nomgeo", "nom_mun", "NOM_MUN"]);
  const estado = firstProp(props, ["nom_ent", "NOM_ENT"]);
  bindRichInfo(layer, {
    title: municipio || "Municipio", kind: "limites",
    tooltipRows: orderedRows(props, [["Estado", () => estado], ["Municipio", () => municipio], ["CVEGEO", () => firstProp(props, ["cvegeo", "CVEGEO"])]]),
    popupRows: orderedRows(props, [["Estado", () => estado], ["Municipio", () => municipio], ["CVEGEO", () => firstProp(props, ["cvegeo", "CVEGEO"])], ["Clave de entidad", () => firstProp(props, ["cve_ent", "CVE_ENT"])], ["Clave de municipio", () => firstProp(props, ["cve_mun", "CVE_MUN"])]]),
  });
}

function bindPhysiographyInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["nom_ent_web", "nom_ent", "NOM_ENT", "estado"]);
  const provincia = firstProp(props, ["fisiografia_nombre", "provincia", "PROVINCIA"]);
  bindRichInfo(layer, {
    title: provincia || "Provincia fisiográfica INEGI", kind: "fisiografia",
    tooltipRows: orderedRows(props, [["Estado", () => estado], ["Provincia fisiográfica", () => provincia], ["Clave", () => firstProp(props, ["fisiografia_clave", "clave", "CLAVE"])]]),
    popupRows: orderedRows(props, [["Estado", () => estado], ["Clave de entidad", () => firstProp(props, ["cve_ent_web", "cve_ent", "CVE_ENT"])], ["Provincia fisiográfica", () => provincia], ["Clave de provincia", () => firstProp(props, ["fisiografia_clave", "clave", "CLAVE"])], ["Entidad fisiográfica", () => firstProp(props, ["fisiografia_entidad", "entidad", "ENTIDAD"])]]),
  });
}

function bindHydrologyInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["nom_ent_web", "nom_ent", "NOM_ENT", "estado"]);
  const corriente = firstProp(props, ["corriente_nombre", "nombre", "NOMBRE"]);
  bindRichInfo(layer, {
    title: corriente || "Corriente de agua INEGI", kind: "hidrografia",
    tooltipRows: orderedRows(props, [["Estado", () => estado], ["Corriente", () => corriente], ["Orden", () => firstProp(props, ["orden_corriente", "orden", "ORDEN"])]]),
    popupRows: orderedRows(props, [
      ["Estado", () => estado], ["Clave de entidad", () => firstProp(props, ["cve_ent_web", "cve_ent", "CVE_ENT"])],
      ["Corriente", () => corriente], ["Orden de corriente", () => firstProp(props, ["orden_corriente", "orden", "ORDEN"])],
      ["Tipo de segmento", () => firstProp(props, ["segmento_tipo", "tipo", "TIPO"])],
      ["Tipo de corriente", () => firstProp(props, ["corriente_tipo", "ter_gen", "Ter_Gen"])],
      ["Condición de desaparición", () => firstProp(props, ["condicion_desaparicion", "c_desapa", "C_DESAPA"])],
    ]),
  });
}

function bindSoilInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["nom_ent_web", "nom_ent", "NOM_ENT", "estado"]);
  const suelo = firstProp(props, ["grupo1_nombre", "grupo1", "GRUPO1"]);
  bindRichInfo(layer, {
    title: suelo || "Edafología INEGI", kind: "edafologia",
    tooltipRows: orderedRows(props, [["Estado", () => estado], ["Grupo de suelo", () => suelo], ["Textura", () => firstProp(props, ["textura_nombre", "textura", "TEXTURA"])]]),
    popupRows: orderedRows(props, [["Estado", () => estado], ["Clave de entidad", () => firstProp(props, ["cve_ent_web", "cve_ent", "CVE_ENT"])], ["Grupo de suelo", () => suelo], ["Textura", () => firstProp(props, ["textura_nombre", "textura", "TEXTURA"])]]),
  });
}

function bindLandUseInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["nom_ent_web", "nom_ent", "NOM_ENT", "estado"]);
  const descripcion = firstProp(props, ["usv_descripcion", "descripcion", "DESCRIPCION"]);
  bindRichInfo(layer, {
    title: descripcion || "Uso de suelo y vegetación INEGI", kind: "uso-suelo",
    tooltipRows: orderedRows(props, [["Estado", () => estado], ["Uso de suelo / vegetación", () => descripcion]]),
    popupRows: orderedRows(props, [["Estado", () => estado], ["Clave de entidad", () => firstProp(props, ["cve_ent_web", "cve_ent", "CVE_ENT"])], ["Clave de categoría", () => firstProp(props, ["usv_clave", "clave", "CLAVE"])], ["Uso de suelo / vegetación", () => descripcion]]),
  });
}

function bindSmnInfo(feature, layer) {
  const props = feature?.properties || {};
  const estado = firstProp(props, ["estado", "nom_ent", "NOM_ENT"]);
  const municipio = firstProp(props, ["municipio", "nom_mun", "NOM_MUN"]);
  const estacion = firstProp(props, ["nombre_estacion", "estacion", "nombre", "NOMBRE"]);
  const idEstacion = firstProp(props, ["id_estacion", "id_estacion_cabecera", "estacion_id", "id"]);
  bindRichInfo(layer, {
    title: estacion || "Estación meteorológica SMN-CONAGUA", kind: "smn",
    tooltipRows: orderedRows(props, [["ID de estación", () => idEstacion], ["Estación meteorológica", () => estacion], ["Estado", () => estado], ["Municipio", () => municipio], ["Situación operativa", () => firstProp(props, ["situacion_operativa", "situacion", "estatus"])]]),
    popupRows: orderedRows(props, [
      ["ID de estación", () => idEstacion], ["Estación meteorológica", () => estacion], ["Estado", () => estado], ["Municipio", () => municipio],
      ["Clave de entidad", () => firstProp(props, ["cve_ent", "CVE_ENT"])], ["CVEGEO", () => firstProp(props, ["cvegeo", "CVEGEO"])],
      ["CVE-OMM", () => firstProp(props, ["cve_omm", "CVE_OMM", "clave_omm", "omm", "wmo"])],
      ["Altitud (m s. n. m.)", () => firstProp(props, ["altitud_msnm", "altitud", "elevacion_m", "elevacion"]), { number: true }],
      ["Situación operativa", () => firstProp(props, ["situacion_operativa", "situacion", "estatus"])],
      ["Cobertura desde", () => firstProp(props, ["cobertura_inicio", "fecha_inicio", "fecha_min"])], ["Cobertura hasta", () => firstProp(props, ["cobertura_fin", "fecha_fin", "fecha_max"])],
      ["Latitud", () => firstProp(props, ["latitud", "latitude"]), { number: true, maximumFractionDigits: 6 }], ["Longitud", () => firstProp(props, ["longitud", "longitude"]), { number: true, maximumFractionDigits: 6 }],
    ]),
  });
}

function normalizeText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
}

function stationMatchesOperationalFilter(feature, filtros) {
  const filterOperando = filtros?.operando === true;
  const filterSuspendida = filtros?.suspendida === true;
  if (!filterOperando && !filterSuspendida) return true;
  const status = normalizeText(feature?.properties?.situacion_operativa);
  if (!status) return false;
  if (status.includes("operando") || status.includes("operativa")) return filterOperando;
  if (status.includes("suspend")) return filterSuspendida;
  return false;
}

function stationMatchesTerritory(feature, cveEnt) {
  if (!cveEnt) return true;
  const featureCveEnt = normalizeGeoKey(feature?.properties?.cve_ent ?? feature?.properties?.CVE_ENT, 2);
  return featureCveEnt ? featureCveEnt === cveEnt : true;
}

function stationMatchesMunicipality(feature, municipioGeojson) {
  if (!municipioGeojson?.features?.length) return true;
  const coordinates = feature?.geometry?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length < 2) return false;
  return municipioGeojson.features.some((municipio) => pointInGeometry(coordinates, municipio.geometry));
}

function stationCoversPeriod(feature, scope) {
  if (!scope) return true;
  const props = feature?.properties || {};
  const start = props.fecha_inicio ?? props.fecha_min ?? props.cobertura_inicio ?? props.inicio_datos;
  const end = props.fecha_fin ?? props.fecha_max ?? props.cobertura_fin ?? props.fin_datos;
  let from = null;
  let to = null;
  if (scope.tipoPeriodo === "anio" && scope.anio) { from = `${scope.anio}-01-01`; to = `${scope.anio}-12-31`; }
  else if (scope.tipoPeriodo === "anio_mes" && scope.anio && scope.mes) { from = `${scope.anio}-${String(scope.mes).padStart(2, "0")}-01`; to = `${scope.anio}-${String(scope.mes).padStart(2, "0")}-31`; }
  else if (scope.tipoPeriodo === "fecha" && scope.fechaInicio) { from = scope.fechaInicio; to = scope.fechaInicio; }
  else if (scope.tipoPeriodo === "rango_fechas" && scope.fechaInicio && scope.fechaFin) { from = scope.fechaInicio; to = scope.fechaFin; }
  else if (scope.tipoPeriodo === "comparar_anios" && scope.anioInicio && scope.anioFin) {
    const minYear = Math.min(Number(scope.anioInicio), Number(scope.anioFin));
    const maxYear = Math.max(Number(scope.anioInicio), Number(scope.anioFin));
    from = `${minYear}-01-01`; to = `${maxYear}-12-31`;
  }
  if (!from || !to) return true;
  if (start || end) {
    const startText = start ? String(start).slice(0, 10) : from;
    const endText = end ? String(end).slice(0, 10) : to;
    return startText <= to && endText >= from;
  }
  const targetStartYear = Number(from.slice(0, 4));
  const targetEndYear = Number(to.slice(0, 4));
  const startYear = Number(props.anio_inicio ?? props.anio_min ?? props.year_min);
  const endYear = Number(props.anio_fin ?? props.anio_max ?? props.year_max);
  if (Number.isFinite(startYear) || Number.isFinite(endYear)) {
    return (!Number.isFinite(startYear) || targetEndYear >= startYear) && (!Number.isFinite(endYear) || targetStartYear <= endYear);
  }
  return true;
}

function topFrequency(features, getter) {
  const counts = new Map();
  features.forEach((feature) => {
    const value = getter(feature?.properties || {});
    if (!value) return;
    const key = String(value);
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  let best = null;
  let max = 0;
  counts.forEach((count, value) => { if (count > max) { best = value; max = count; } });
  return best ? { value: best, count: max } : null;
}

function coverageRange(features) {
  const starts = [];
  const ends = [];
  features.forEach((feature) => {
    const props = feature?.properties || {};
    const start = firstProp(props, ["cobertura_inicio", "fecha_inicio", "fecha_min"]);
    const end = firstProp(props, ["cobertura_fin", "fecha_fin", "fecha_max"]);
    if (start) starts.push(String(start).slice(0, 10));
    if (end) ends.push(String(end).slice(0, 10));
  });
  if (!starts.length && !ends.length) return null;
  starts.sort(); ends.sort();
  return { from: starts[0] || null, to: ends[ends.length - 1] || null };
}

function MapViewportTracker({ onChange }) {
  const timerRef = useRef(null);
  const lastBboxRef = useRef("");
  const map = useMapEvents({ moveend() { scheduleViewportUpdate(); }, zoomend() { scheduleViewportUpdate(); } });
  const emitViewport = () => {
    const bbox = bboxToString(map.getBounds());
    if (!bbox || bbox === lastBboxRef.current) return;
    lastBboxRef.current = bbox;
    onChange(bbox);
  };
  const scheduleViewportUpdate = () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(emitViewport, VIEWPORT_DEBOUNCE_MS);
  };
  useEffect(() => {
    emitViewport();
    return () => { if (timerRef.current) window.clearTimeout(timerRef.current); };
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
      if (!(target instanceof Element) || target.closest(".leaflet-popup") || target.closest(".leaflet-interactive")) return;
      map.closePopup();
    };
    const closeForLegend = () => map.closePopup();
    document.addEventListener("pointerdown", closePopupFromOutside, true);
    window.addEventListener("map:legend-open", closeForLegend);
    return () => {
      document.removeEventListener("pointerdown", closePopupFromOutside, true);
      window.removeEventListener("map:legend-open", closeForLegend);
    };
  }, [map]);
  return null;
}

function SyncTerritoryView({ geojson, hasTerritory, fitKey }) {
  const map = useMap();
  useEffect(() => {
    if (!hasTerritory) {
      map.setView(DEFAULT_VIEW.center, DEFAULT_VIEW.zoom, { animate: true });
      return;
    }
    if (!geojson?.features?.length) return;
    const layer = L.geoJSON(geojson);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [36, 36], maxZoom: 11 });
  }, [map, geojson, hasTerritory, fitKey]);
  return null;
}

export default function MapView({
  consultaActiva = null,
  consultaEjecutada = null,
  resumenConsulta = null,
  onConsultaChange,
  onConsultar,
  onLayerSummaryChange,
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
  const [viewportTerritoryKey, setViewportTerritoryKey] = useState("");
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
  const boundaryStyle = BOUNDARY_STYLES[baseLayerId] || BOUNDARY_STYLES.esri;
  const rows = resumenConsulta?.rows ?? [];
  const mapScope = consultaEjecutada;
  const overlayScope = mapScope || consultaActiva;
  const nivelMapa = mapScope?.nivelAgregacion || overlayScope?.nivelAgregacion || "entidad";
  const capasActivas = consultaActiva?.capasActivas || {};
  const filtrosSmn = consultaActiva?.filtrosSmn || {};
  const cveEntCapas = normalizeGeoKey(overlayScope?.cveEnt, 2);
  const cvegeoSeleccionado = normalizeGeoKey(overlayScope?.cvegeo, 5);
  const territoryKey = `${overlayScope?.nivelAgregacion || "entidad"}:${cveEntCapas || "mx"}:${cvegeoSeleccionado || "all"}`;
  const viewportReady = Boolean(viewportBbox && viewportTerritoryKey === territoryKey);

  const setOverlay = (key, data) => setOverlays((prev) => ({ ...prev, [key]: data || EMPTY_FEATURE_COLLECTION }));
  const handleViewportChange = useCallback((bbox) => { setViewportBbox(bbox); setViewportTerritoryKey(territoryKey); }, [territoryKey]);

  useEffect(() => {
    setLayerError(null);
    setOverlays((prev) => ({ ...prev, firms: EMPTY_FEATURE_COLLECTION, conafor: EMPTY_FEATURE_COLLECTION, fisiografia: EMPTY_FEATURE_COLLECTION, hidrografia: EMPTY_FEATURE_COLLECTION, edafologia: EMPTY_FEATURE_COLLECTION, usoSueloVegetacion: EMPTY_FEATURE_COLLECTION }));
  }, [territoryKey]);

  useEffect(() => {
    let active = true;
    obtenerGeometriasEstados().then((data) => { if (active) setEstadosGeojson(data || EMPTY_FEATURE_COLLECTION); }).catch((error) => { if (active) setGeometryError(error.message); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setMunicipiosGeojson(EMPTY_FEATURE_COLLECTION);
    if (!cveEntCapas) return () => { active = false; };
    obtenerGeometriasMunicipios(cveEntCapas).then((data) => { if (active) setMunicipiosGeojson(data || EMPTY_FEATURE_COLLECTION); }).catch((error) => { if (active) setGeometryError(error.message); });
    return () => { active = false; };
  }, [cveEntCapas]);

  useEffect(() => {
    let active = true;
    if (!capasActivas.estacionesSmn) { setOverlay("smn", EMPTY_FEATURE_COLLECTION); return () => { active = false; }; }
    obtenerEstacionesSmn().then((data) => { if (active) setOverlay("smn", data); }).catch((error) => { if (active && !isAbortError(error)) setLayerError(`SMN: ${error.message}`); });
    return () => { active = false; };
  }, [capasActivas.estacionesSmn]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const overlayKeys = ["fisiografia", "hidrografia", "edafologia", "usoSueloVegetacion"];
    if (!cveEntCapas || !viewportReady) {
      overlayKeys.forEach((key) => setOverlay(key, EMPTY_FEATURE_COLLECTION));
      return () => { active = false; controller.abort(); };
    }
    const cvegeo = cvegeoSeleccionado || "";
    const tasks = [];
    const addTask = (enabled, capa, overlayKey) => {
      if (!enabled) { setOverlay(overlayKey, EMPTY_FEATURE_COLLECTION); return; }
      tasks.push(obtenerCapaTematicaViewport(capa, cveEntCapas, viewportBbox, cvegeo, { signal: controller.signal }).then((data) => { if (active) setOverlay(overlayKey, data); }));
    };
    addTask(capasActivas.fisiografiaInegi, "fisiografia", "fisiografia");
    addTask(capasActivas.corrientesAguaInegi, "hidrografia", "hidrografia");
    addTask(capasActivas.edafologiaInegi, "edafologia", "edafologia");
    addTask(capasActivas.usoSueloVegetacionInegi, "uso_suelo_vegetacion", "usoSueloVegetacion");
    Promise.allSettled(tasks).then((results) => {
      if (!active) return;
      const errors = results.filter((result) => result.status === "rejected" && !isAbortError(result.reason)).map((result) => result.reason?.message).filter(Boolean);
      if (errors.length) setLayerError(errors.join(" | "));
    });
    return () => { active = false; controller.abort(); };
  }, [cveEntCapas, cvegeoSeleccionado, viewportBbox, viewportReady, capasActivas.fisiografiaInegi, capasActivas.corrientesAguaInegi, capasActivas.edafologiaInegi, capasActivas.usoSueloVegetacionInegi]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const pointYear = overlayScope?.tipoPeriodo === "comparar_anios" ? null : overlayScope?.anio;
    if (!pointYear || !viewportReady) {
      setOverlay("firms", EMPTY_FEATURE_COLLECTION);
      setOverlay("conafor", EMPTY_FEATURE_COLLECTION);
      return () => { active = false; controller.abort(); };
    }
    const puntosParams = { anio: pointYear, mes: overlayScope.tipoPeriodo === "anio_mes" ? overlayScope.mes : undefined, cve_ent: overlayScope.cveEnt || undefined, cvegeo: overlayScope.cvegeo || undefined, bbox: viewportBbox };
    const tasks = [];
    if (capasActivas.puntosCalorFirms) tasks.push(obtenerPuntosFirms(puntosParams, { signal: controller.signal }).then((data) => { if (active) setOverlay("firms", data); }));
    else setOverlay("firms", EMPTY_FEATURE_COLLECTION);
    if (capasActivas.incendiosConafor) tasks.push(obtenerIncendiosConafor(puntosParams, { signal: controller.signal }).then((data) => { if (active) setOverlay("conafor", data); }));
    else setOverlay("conafor", EMPTY_FEATURE_COLLECTION);
    Promise.allSettled(tasks).then((results) => {
      if (!active) return;
      const errors = results.filter((result) => result.status === "rejected" && !isAbortError(result.reason)).map((result) => result.reason?.message).filter(Boolean);
      if (errors.length) setLayerError(errors.join(" | "));
    });
    return () => { active = false; controller.abort(); };
  }, [capasActivas.puntosCalorFirms, capasActivas.incendiosConafor, viewportBbox, viewportReady, overlayScope?.anio, overlayScope?.mes, overlayScope?.tipoPeriodo, overlayScope?.cveEnt, overlayScope?.cvegeo]);

  const estadoSeleccionadoGeojson = useMemo(() => cveEntCapas ? filterFeatureCollection(estadosGeojson, (feature) => getFeatureKey(feature, "entidad") === cveEntCapas) : EMPTY_FEATURE_COLLECTION, [estadosGeojson, cveEntCapas]);
  const municipioSeleccionadoGeojson = useMemo(() => cvegeoSeleccionado ? filterFeatureCollection(municipiosGeojson, (feature) => getFeatureKey(feature, "municipio") === cvegeoSeleccionado) : EMPTY_FEATURE_COLLECTION, [municipiosGeojson, cvegeoSeleccionado]);
  const territorioSeleccionadoGeojson = cvegeoSeleccionado ? municipioSeleccionadoGeojson : estadoSeleccionadoGeojson;
  const limitesEstatalesGeojson = useMemo(() => cveEntCapas ? estadoSeleccionadoGeojson : estadosGeojson, [estadosGeojson, estadoSeleccionadoGeojson, cveEntCapas]);

  const smnFiltrado = useMemo(() => {
    if (!overlays.smn?.features) return EMPTY_FEATURE_COLLECTION;
    return filterFeatureCollection(overlays.smn, (feature) => {
      if (!stationMatchesOperationalFilter(feature, filtrosSmn)) return false;
      if (!stationMatchesTerritory(feature, cveEntCapas)) return false;
      if (cvegeoSeleccionado && !stationMatchesMunicipality(feature, municipioSeleccionadoGeojson)) return false;
      if (filtrosSmn.alcance === "periodo" && !stationCoversPeriod(feature, overlayScope)) return false;
      return true;
    });
  }, [overlays.smn, filtrosSmn, cveEntCapas, cvegeoSeleccionado, municipioSeleccionadoGeojson, overlayScope]);

  const layerSummary = useMemo(() => {
    const firms = overlays.firms?.features || [];
    const conafor = overlays.conafor?.features || [];
    const smn = smnFiltrado?.features || [];
    const day = firms.filter((feature) => String(feature?.properties?.daynight || "").toUpperCase() === "D").length;
    const night = firms.filter((feature) => String(feature?.properties?.daynight || "").toUpperCase() === "N").length;
    const satelliteInstrument = topFrequency(firms, (props) => [props.satellite, props.instrument].filter(Boolean).join(" · "));
    const conaforHa = conafor.reduce((total, feature) => total + Number(feature?.properties?.superficie_total_ha || 0), 0);
    const vegetation = topFrequency(conafor, (props) => props.tipo_vegetacion);
    const cause = topFrequency(conafor, (props) => props.causa);
    const operando = smn.filter((feature) => normalizeText(feature?.properties?.situacion_operativa).includes("operando") || normalizeText(feature?.properties?.situacion_operativa).includes("operativa")).length;
    const suspendida = smn.filter((feature) => normalizeText(feature?.properties?.situacion_operativa).includes("suspend")).length;
    return {
      firms: { count: firms.length, day, night, satelliteInstrument },
      conafor: { count: conafor.length, hectares: conaforHa, vegetation, cause },
      smn: { count: smn.length, operando, suspendida, coverage: coverageRange(smn) },
      inegi: { fisiografia: overlays.fisiografia?.features?.length || 0, edafologia: overlays.edafologia?.features?.length || 0, usoSueloVegetacion: overlays.usoSueloVegetacion?.features?.length || 0, hidrografia: overlays.hidrografia?.features?.length || 0 },
      scope: { territoryKey, viewportBbox, viewportReady },
    };
  }, [overlays, smnFiltrado, territoryKey, viewportBbox, viewportReady]);

  useEffect(() => { onLayerSummaryChange?.(layerSummary); }, [layerSummary, onLayerSummaryChange]);

  const thematicLegend = useMemo(() => ({
    fisiografia: legendItems(overlays.fisiografia?.features, (props) => firstProp(props, ["fisiografia_nombre", "fisiografia_clave", "provincia", "PROVINCIA"]), PHYSIOGRAPHY_COLORS),
    edafologia: legendItems(overlays.edafologia?.features, (props) => firstProp(props, ["grupo1_nombre", "grupo1", "GRUPO1", "clave_wrb", "CLAVE_WRB"]), SOIL_COLORS),
    usoSueloVegetacion: legendItems(overlays.usoSueloVegetacion?.features, (props) => firstProp(props, ["usv_descripcion", "usv_clave", "descripcion", "DESCRIPCION"]), LAND_USE_COLORS),
  }), [overlays.fisiografia, overlays.edafologia, overlays.usoSueloVegetacion]);

  const rowByKey = useMemo(() => {
    const map = new Map();
    rows.forEach((row) => { const key = getRowKey(row, nivelMapa); if (key) map.set(key, row); });
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
    return { ...resultadoBaseGeojson, features: resultadoBaseGeojson.features.map((feature) => {
      const key = getFeatureKey(feature, nivelMapa);
      const row = rowByKey.get(key) ?? null;
      const clusterMatches = selectedMlCluster === null || selectedMlCluster === "" || Number(row?.cluster) === Number(selectedMlCluster);
      return { ...feature, properties: { ...(feature.properties || {}), __map_key: key, __resultado: row, __map_style: { color: row ? "#FFFFFF" : "rgba(255,255,255,.65)", weight: row ? 1.6 : 0.8, fillColor: row?.color_sugerido_app || "#64748B", fillOpacity: row ? (clusterMatches ? 0.72 : 0.16) : 0.05 } } };
    }) };
  }, [resultadoBaseGeojson, rowByKey, nivelMapa, selectedMlCluster]);

  const styleFeature = (feature) => feature?.properties?.__map_style || { color: "rgba(255,255,255,.65)", weight: 0.8, fillColor: "#64748B", fillOpacity: 0.05 };
  const onEachResultFeature = (feature, layer) => {
    const key = feature?.properties?.__map_key || getFeatureKey(feature, nivelMapa);
    const row = feature?.properties?.__resultado || null;
    const name = feature?.properties?.nomgeo || feature?.properties?.nom_ent || feature?.properties?.nom_mun || row?.nombre_municipio || row?.nombre_entidad || key;
    if (!row) return;
    bindRichInfo(layer, {
      title: name, kind: "ml",
      tooltipRows: orderedRows(row, [["Estado", "nombre_entidad"], ["Municipio", "nombre_municipio"], ["Cluster", "cluster"], ["Observaciones", "observaciones", { number: true }]]),
      popupRows: orderedRows(row, [["Estado", "nombre_entidad"], ["Municipio", "nombre_municipio"], ["Clave", nivelMapa === "municipio" ? "cvegeo" : "cve_ent"], ["Cluster", "cluster"], ["Estado ML", "estado_app"], ["Etiqueta", "etiqueta_final"], ["Observaciones", "observaciones", { number: true }], ["Detecciones FIRMS", "firms_detecciones", { number: true }], ["Eventos CONAFOR", "conafor_eventos", { number: true }]]),
    });
  };

  const fitKey = territoryKey;
  const thematicKey = `${territoryKey}-${viewportReady ? viewportBbox : "pending"}`;
  const renderKey = `${fitKey}-${resumenConsulta?.periodo || "sin-resultados"}-${rows.length}-${selectedMlCluster ?? "all"}`;

  return (
    <div className="mapWrap" role="region" aria-label="Mapa interactivo de incendios forestales en México" aria-describedby="map-accessible-summary">
      <p id="map-accessible-summary" className="srOnly">Mapa interactivo de México con resultados ML y capas geográficas seleccionables.</p>
      <MapContainer center={DEFAULT_VIEW.center} zoom={DEFAULT_VIEW.zoom} minZoom={3} className="leafletMap" zoomControl={false} keyboard={true} preferCanvas={true}>
        <TileLayer url={activeLayer.url} attribution={activeLayer.attribution} />
        <MapViewportTracker onChange={handleViewportChange} />

        {capasActivas.limitesEstatales && limitesEstatalesGeojson?.features?.length ? <>
          <GeoJSON key={`lim-est-halo-${cveEntCapas || "mx"}-${baseLayerId}`} data={limitesEstatalesGeojson} style={() => boundaryStyle.stateHalo} interactive={false} />
          <GeoJSON key={`lim-est-${cveEntCapas || "mx"}-${baseLayerId}`} data={limitesEstatalesGeojson} style={() => boundaryStyle.state} onEachFeature={bindStateInfo} />
        </> : null}

        {capasActivas.limitesMunicipales && municipiosGeojson?.features?.length ? <>
          <GeoJSON key={`lim-mun-halo-${cveEntCapas}-${baseLayerId}`} data={municipiosGeojson} style={() => boundaryStyle.municipalityHalo} interactive={false} />
          <GeoJSON key={`lim-mun-${cveEntCapas}-${baseLayerId}`} data={municipiosGeojson} style={() => boundaryStyle.municipality} onEachFeature={bindMunicipalityInfo} />
        </> : null}

        {territorioSeleccionadoGeojson?.features?.length ? <GeoJSON key={`territorio-${fitKey}`} data={territorioSeleccionadoGeojson} style={() => SELECTED_TERRITORY_STYLE} interactive={false} /> : null}
        {displayGeojson?.features?.length ? <GeoJSON key={renderKey} data={displayGeojson} style={styleFeature} onEachFeature={onEachResultFeature} /> : null}
        {overlays.fisiografia?.features?.length ? <GeoJSON key={`fisiografia-${thematicKey}-${baseLayerId}`} data={overlays.fisiografia} style={(feature) => physiographyStyle(feature, baseLayerId)} onEachFeature={bindPhysiographyInfo} /> : null}
        {overlays.hidrografia?.features?.length ? <GeoJSON key={`hidrografia-${thematicKey}`} data={overlays.hidrografia} style={hydrologyStyle} onEachFeature={bindHydrologyInfo} /> : null}
        {overlays.edafologia?.features?.length ? <GeoJSON key={`edafologia-${thematicKey}-${baseLayerId}`} data={overlays.edafologia} style={(feature) => soilStyle(feature, baseLayerId)} onEachFeature={bindSoilInfo} /> : null}
        {overlays.usoSueloVegetacion?.features?.length ? <GeoJSON key={`usv-${thematicKey}-${baseLayerId}`} data={overlays.usoSueloVegetacion} style={(feature) => landUseStyle(feature, baseLayerId)} onEachFeature={bindLandUseInfo} /> : null}

        {smnFiltrado?.features?.length ? <GeoJSON key={`smn-${cveEntCapas || "mx"}-${cvegeoSeleccionado || "all"}-${filtrosSmn.alcance || "todas"}-${filtrosSmn.operando}-${filtrosSmn.suspendida}`} data={smnFiltrado} pointToLayer={(_, latlng) => L.circleMarker(latlng, { radius: 4, color: "#0F766E", weight: 1, fillColor: "#14B8A6", fillOpacity: 0.8 })} onEachFeature={bindSmnInfo} /> : null}
        {overlays.conafor?.features?.length ? <GeoJSON key={`conafor-${territoryKey}-${viewportReady ? viewportBbox : "pending"}`} data={overlays.conafor} pointToLayer={(feature, latlng) => L.circleMarker(latlng, conaforMarkerStyle(feature))} onEachFeature={bindConaforInfo} /> : null}
        {overlays.firms?.features?.length ? <GeoJSON key={`firms-${territoryKey}-${viewportReady ? viewportBbox : "pending"}`} data={overlays.firms} pointToLayer={(feature, latlng) => L.circleMarker(latlng, firmsMarkerStyle(feature))} onEachFeature={bindFirmsInfo} /> : null}

        <SyncTerritoryView geojson={territorioSeleccionadoGeojson} hasTerritory={Boolean(cveEntCapas || cvegeoSeleccionado)} fitKey={fitKey} />
        <MapResizeInvalidator watchKey={`${leftPanelOpen}-${rightPanelOpen}-${baseLayerId}`} />
        <MapPopupCloser />
        <MapControls defaultView={DEFAULT_VIEW} baseLayerId={baseLayerId} onChangeLayer={setBaseLayerId} layers={BASE_LAYERS} estadosGeojson={estadosGeojson} rightPanelOpen={rightPanelOpen} />
      </MapContainer>

      {geometryError ? <div className="mapGeometryError">No fue posible cargar la geometría: {geometryError}</div> : null}
      {layerError ? <div className="mapGeometryError">No fue posible cargar una capa: {layerError}</div> : null}
      <MapLegend resumenConsulta={resumenConsulta} rightPanelOpen={rightPanelOpen} selectedMlCluster={selectedMlCluster} capasActivas={capasActivas} thematicLegend={thematicLegend} />
    </div>
  );
}
