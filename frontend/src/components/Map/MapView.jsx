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

function bboxToString(bounds) {
  if (!bounds?.isValid?.()) return "";
  return [
    bounds.getWest(),
    bounds.getSouth(),
    bounds.getEast(),
    bounds.getNorth(),
  ].join(",");
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
    const invalidate = () => {
      window.requestAnimationFrame(() => map.invalidateSize());
    };

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
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 9 });
    }
  }, [map, geojson, enabled, fitKey]);

  return null;
}

function bindSimpleTooltip(feature, layer, fields) {
  const props = feature?.properties || {};
  const lines = fields
    .map(([label, key]) => [label, props[key]])
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `<strong>${label}:</strong> ${value}`);

  if (lines.length) {
    layer.bindTooltip(lines.join("<br/>"), { sticky: true, direction: "top" });
  }
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
  const [geojson, setGeojson] = useState(null);
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
  const nivelMapa = mapScope?.nivelAgregacion || "entidad";
  const capasActivas = consultaActiva?.capasActivas || {};
  const cveEntCapas = normalizeGeoKey(mapScope?.cveEnt || consultaActiva?.cveEnt, 2);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setGeometryError(null);

        if (!mapScope) {
          const data = await obtenerGeometriasEstados();
          if (active) setGeojson(data);
          return;
        }

        if (mapScope.nivelAgregacion === "municipio" && mapScope.cveEnt) {
          const data = await obtenerGeometriasMunicipios(normalizeGeoKey(mapScope.cveEnt, 2));
          if (active) setGeojson(data);
          return;
        }

        const data = await obtenerGeometriasEstados();
        if (active) setGeojson(data);
      } catch (error) {
        if (active) {
          setGeojson(null);
          setGeometryError(error.message);
        }
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [mapScope?.nivelAgregacion, mapScope?.cveEnt]);

  useEffect(() => {
    let active = true;

    const setLayer = (key, data) => {
      if (!active) return;
      setOverlays((prev) => ({ ...prev, [key]: data || EMPTY_FEATURE_COLLECTION }));
    };

    const clearLayer = (key) => setLayer(key, EMPTY_FEATURE_COLLECTION);

    const load = async () => {
      setLayerError(null);
      const tasks = [];

      if (capasActivas.estacionesSmn) {
        tasks.push(
          obtenerEstacionesSmn()
            .then((data) => setLayer("smn", data))
            .catch((error) => {
              throw new Error(`SMN: ${error.message}`);
            }),
        );
      } else {
        clearLayer("smn");
      }

      if (cveEntCapas && capasActivas.fisiografiaInegi) {
        tasks.push(
          obtenerCapaTematica("fisiografia", cveEntCapas)
            .then((data) => setLayer("fisiografia", data))
            .catch((error) => {
              throw new Error(`Fisiografía: ${error.message}`);
            }),
        );
      } else {
        clearLayer("fisiografia");
      }

      if (cveEntCapas && capasActivas.corrientesAguaInegi) {
        tasks.push(
          obtenerCapaTematica("hidrografia", cveEntCapas)
            .then((data) => setLayer("hidrografia", data))
            .catch((error) => {
              throw new Error(`Hidrografía: ${error.message}`);
            }),
        );
      } else {
        clearLayer("hidrografia");
      }

      if (cveEntCapas && viewportBbox && capasActivas.edafologiaInegi) {
        tasks.push(
          obtenerCapaTematicaViewport("edafologia", cveEntCapas, viewportBbox)
            .then((data) => setLayer("edafologia", data))
            .catch((error) => {
              throw new Error(`Edafología: ${error.message}`);
            }),
        );
      } else {
        clearLayer("edafologia");
      }

      if (cveEntCapas && viewportBbox && capasActivas.usoSueloVegetacionInegi) {
        tasks.push(
          obtenerCapaTematicaViewport("uso_suelo_vegetacion", cveEntCapas, viewportBbox)
            .then((data) => setLayer("usoSueloVegetacion", data))
            .catch((error) => {
              throw new Error(`Uso de suelo/vegetación: ${error.message}`);
            }),
        );
      } else {
        clearLayer("usoSueloVegetacion");
      }

      const puntosParams = mapScope?.anio
        ? {
            anio: mapScope.anio,
            mes: mapScope.tipoPeriodo === "anio_mes" ? mapScope.mes : undefined,
            cve_ent: mapScope.cveEnt || undefined,
            cvegeo: mapScope.cvegeo || undefined,
            bbox: viewportBbox || undefined,
          }
        : null;

      if (puntosParams && capasActivas.puntosCalorFirms) {
        tasks.push(
          obtenerPuntosFirms(puntosParams)
            .then((data) => setLayer("firms", data))
            .catch((error) => {
              throw new Error(`FIRMS: ${error.message}`);
            }),
        );
      } else {
        clearLayer("firms");
      }

      if (puntosParams && capasActivas.incendiosConafor) {
        tasks.push(
          obtenerIncendiosConafor(puntosParams)
            .then((data) => setLayer("conafor", data))
            .catch((error) => {
              throw new Error(`CONAFOR: ${error.message}`);
            }),
        );
      } else {
        clearLayer("conafor");
      }

      const results = await Promise.allSettled(tasks);
      if (!active) return;
      const errors = results
        .filter((result) => result.status === "rejected")
        .map((result) => result.reason?.message)
        .filter(Boolean);
      if (errors.length) setLayerError(errors.join(" | "));
    };

    load();
    return () => {
      active = false;
    };
  }, [
    capasActivas.estacionesSmn,
    capasActivas.fisiografiaInegi,
    capasActivas.corrientesAguaInegi,
    capasActivas.edafologiaInegi,
    capasActivas.usoSueloVegetacionInegi,
    capasActivas.puntosCalorFirms,
    capasActivas.incendiosConafor,
    cveEntCapas,
    viewportBbox,
    mapScope?.anio,
    mapScope?.mes,
    mapScope?.tipoPeriodo,
    mapScope?.cveEnt,
    mapScope?.cvegeo,
  ]);

  const rowByKey = useMemo(() => {
    const map = new Map();
    rows.forEach((row) => {
      const key = getRowKey(row, nivelMapa);
      if (key) map.set(key, row);
    });
    return map;
  }, [rows, nivelMapa]);

  const filteredGeojson = useMemo(() => {
    if (!geojson?.features) return null;
    if (!mapScope) return geojson;

    if (mapScope.nivelAgregacion === "entidad" && mapScope.cveEnt) {
      const target = normalizeGeoKey(mapScope.cveEnt, 2);
      return {
        ...geojson,
        features: geojson.features.filter((feature) => getFeatureKey(feature, "entidad") === target),
      };
    }

    if (mapScope.nivelAgregacion === "municipio" && mapScope.cvegeo) {
      const target = normalizeGeoKey(mapScope.cvegeo, 5);
      return {
        ...geojson,
        features: geojson.features.filter((feature) => getFeatureKey(feature, "municipio") === target),
      };
    }

    return geojson;
  }, [geojson, mapScope]);

  const displayGeojson = useMemo(() => {
    if (!filteredGeojson?.features) return null;

    return {
      ...filteredGeojson,
      features: filteredGeojson.features.map((feature) => {
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
              fillOpacity: row ? (clusterMatches ? 0.72 : 0.16) : 0.08,
            },
          },
        };
      }),
    };
  }, [filteredGeojson, rowByKey, nivelMapa, selectedMlCluster]);

  const styleFeature = (feature) => feature?.properties?.__map_style || {
    color: "rgba(255,255,255,.65)",
    weight: 0.8,
    fillColor: "#64748B",
    fillOpacity: 0.08,
  };

  const onEachFeature = (feature, layer) => {
    const key = feature?.properties?.__map_key || getFeatureKey(feature, nivelMapa);
    const row = feature?.properties?.__resultado || null;
    const name = feature?.properties?.nomgeo || feature?.properties?.nom_ent || feature?.properties?.nom_mun || row?.nombre_municipio || row?.nombre_entidad || key;

    layer.bindTooltip(
      `<strong>${name}</strong>${row ? `<br/>Cluster: ${row.cluster}<br/>Observaciones: ${row.observaciones}` : "<br/>Sin resultado para la consulta"}`,
      { sticky: true, direction: "top" }
    );

    if (row) {
      layer.bindPopup(
        `<strong>${name}</strong><br/>Clave: ${key}<br/>Cluster: ${row.cluster}<br/>Observaciones: ${row.observaciones}<br/>FIRMS: ${row.firms_detecciones || 0}<br/>CONAFOR: ${row.conafor_eventos || 0}<br/>Hectáreas: ${Number(row.conafor_ha || 0).toLocaleString("es-MX", { maximumFractionDigits: 2 })}`
      );
    }
  };

  const fitKey = mapScope
    ? `${mapScope.nivelAgregacion}-${mapScope.cveEnt || "mx"}-${mapScope.cvegeo || "all"}-${mapScope.anio || ""}-${mapScope.mes || ""}`
    : "sin-consulta";

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
      >
        <TileLayer url={activeLayer.url} attribution={activeLayer.attribution} />
        <MapViewportTracker onChange={setViewportBbox} />

        {displayGeojson?.features?.length ? (
          <GeoJSON
            key={renderKey}
            data={displayGeojson}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        ) : null}

        {overlays.fisiografia?.features?.length ? (
          <GeoJSON
            key={`fisiografia-${cveEntCapas}`}
            data={overlays.fisiografia}
            style={() => THEMATIC_STYLES.fisiografia}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Provincia", "fisiografia_nombre"]])}
          />
        ) : null}

        {overlays.hidrografia?.features?.length ? (
          <GeoJSON
            key={`hidrografia-${cveEntCapas}`}
            data={overlays.hidrografia}
            style={() => THEMATIC_STYLES.hidrografia}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Corriente", "corriente_nombre"], ["Orden", "orden_corriente"]])}
          />
        ) : null}

        {overlays.edafologia?.features?.length ? (
          <GeoJSON
            key={`edafologia-${cveEntCapas}-${viewportBbox}`}
            data={overlays.edafologia}
            style={() => THEMATIC_STYLES.edafologia}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Suelo", "grupo1_nombre"], ["Textura", "textura_nombre"]])}
          />
        ) : null}

        {overlays.usoSueloVegetacion?.features?.length ? (
          <GeoJSON
            key={`usv-${cveEntCapas}-${viewportBbox}`}
            data={overlays.usoSueloVegetacion}
            style={() => THEMATIC_STYLES.uso_suelo_vegetacion}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Uso/vegetación", "usv_descripcion"]])}
          />
        ) : null}

        {overlays.smn?.features?.length ? (
          <GeoJSON
            key="smn-estaciones"
            data={overlays.smn}
            pointToLayer={(_, latlng) => L.circleMarker(latlng, {
              radius: 4,
              color: "#0F766E",
              weight: 1,
              fillColor: "#14B8A6",
              fillOpacity: 0.8,
            })}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Estación", "nombre_estacion"], ["Situación", "situacion_operativa"]])}
          />
        ) : null}

        {overlays.conafor?.features?.length ? (
          <GeoJSON
            key={`conafor-${fitKey}-${viewportBbox}`}
            data={overlays.conafor}
            pointToLayer={(_, latlng) => L.circleMarker(latlng, {
              radius: 5,
              color: "#7F1D1D",
              weight: 1,
              fillColor: "#DC2626",
              fillOpacity: 0.85,
            })}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Incendio", "clave_incendio"], ["Inicio", "fecha_inicio"], ["Causa", "causa"], ["Superficie ha", "superficie_total_ha"]])}
          />
        ) : null}

        {overlays.firms?.features?.length ? (
          <GeoJSON
            key={`firms-${fitKey}-${viewportBbox}`}
            data={overlays.firms}
            pointToLayer={(_, latlng) => L.circleMarker(latlng, {
              radius: 4,
              color: "#9A3412",
              weight: 1,
              fillColor: "#F97316",
              fillOpacity: 0.8,
            })}
            onEachFeature={(feature, layer) => bindSimpleTooltip(feature, layer, [["Fecha", "fecha"], ["FRP", "frp"], ["Confianza", "confidence_category"], ["Satélite", "satellite"]])}
          />
        ) : null}

        <FitGeoJsonBounds
          geojson={displayGeojson}
          enabled={Boolean(mapScope && (mapScope.cveEnt || mapScope.cvegeo))}
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
