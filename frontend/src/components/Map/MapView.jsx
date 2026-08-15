import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import MapControls from "./MapControls";
import MapLegend from "./MapLegend";
import { obtenerGeometriasEstados, obtenerGeometriasMunicipios } from "../../services/geometrias.service";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };

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
  const activeLayer = BASE_LAYERS[baseLayerId];
  const rows = resumenConsulta?.rows ?? [];
  const mapScope = consultaEjecutada;

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
          const data = await obtenerGeometriasMunicipios(mapScope.cveEnt);
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

  const rowByKey = useMemo(() => {
    const map = new Map();
    rows.forEach((row) => {
      const key = mapScope?.nivelAgregacion === "municipio" ? row.cvegeo : row.cve_ent;
      if (key) map.set(String(key), row);
    });
    return map;
  }, [rows, mapScope?.nivelAgregacion]);

  const filteredGeojson = useMemo(() => {
    if (!geojson?.features) return null;
    if (!mapScope) return geojson;

    if (mapScope.nivelAgregacion === "entidad" && mapScope.cveEnt) {
      return {
        ...geojson,
        features: geojson.features.filter((feature) => String(feature?.properties?.cve_ent || "") === mapScope.cveEnt),
      };
    }

    if (mapScope.nivelAgregacion === "municipio" && mapScope.cvegeo) {
      return {
        ...geojson,
        features: geojson.features.filter((feature) => String(feature?.properties?.cvegeo || "") === mapScope.cvegeo),
      };
    }

    return geojson;
  }, [geojson, mapScope]);

  const styleFeature = (feature) => {
    const key = mapScope?.nivelAgregacion === "municipio"
      ? String(feature?.properties?.cvegeo || "")
      : String(feature?.properties?.cve_ent || "");
    const row = rowByKey.get(key);
    const isSelectedCluster = selectedMlCluster === null || selectedMlCluster === "" || Number(row?.cluster) === Number(selectedMlCluster);

    return {
      color: row ? "#FFFFFF" : "rgba(255,255,255,.65)",
      weight: row ? 1.6 : 0.8,
      fillColor: row?.color_sugerido_app || "#64748B",
      fillOpacity: row ? (isSelectedCluster ? 0.72 : 0.16) : 0.08,
    };
  };

  const onEachFeature = (feature, layer) => {
    const key = mapScope?.nivelAgregacion === "municipio"
      ? String(feature?.properties?.cvegeo || "")
      : String(feature?.properties?.cve_ent || "");
    const row = rowByKey.get(key);
    const name = feature?.properties?.nomgeo || row?.nombre_municipio || row?.nombre_entidad || key;

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

  return (
    <div
      className="mapWrap"
      role="region"
      aria-label="Mapa interactivo de incendios forestales en México"
      aria-describedby="map-accessible-summary"
    >
      <p id="map-accessible-summary" className="srOnly">
        Mapa interactivo de México con límites administrativos de INEGI coloreados según el cluster ML de la última consulta ejecutada.
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

        {filteredGeojson?.features?.length ? (
          <GeoJSON
            key={`${fitKey}-${resumenConsulta?.periodo || "sin-resultados"}-${selectedMlCluster ?? "all"}`}
            data={filteredGeojson}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        ) : null}

        <FitGeoJsonBounds
          geojson={filteredGeojson}
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
      <MapLegend
        resumenConsulta={resumenConsulta}
        rightPanelOpen={rightPanelOpen}
        selectedMlCluster={selectedMlCluster}
      />
    </div>
  );
}
