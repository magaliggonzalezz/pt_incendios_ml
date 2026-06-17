import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import MapControls from "./MapControls";
import MapLegend from "./MapLegend";
import { getSimulatedMapFeatures } from "../../data/dashboardMock";
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

function MapPopupCloser({ onClose }) {
  const map = useMap();

  useEffect(() => {
    const closePopupFromOutside = (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest(".leaflet-popup")) return;
      if (target.closest(".leaflet-interactive")) return;

      map.closePopup();
      onClose?.();
    };

    document.addEventListener("pointerdown", closePopupFromOutside, true);
    return () => document.removeEventListener("pointerdown", closePopupFromOutside, true);
  }, [map, onClose]);

  return null;
}

export default function MapView({
  consultaActiva = null,
  onConsultaChange,
  onConsultar,
  leftPanelOpen = false,
  rightPanelOpen = false,
  selectedMlCluster = null,
}) {
  const [baseLayerId, setBaseLayerId] = useState("esri");
  const [selectedFeatureId, setSelectedFeatureId] = useState(null);
  const activeLayer = BASE_LAYERS[baseLayerId];
  const simulatedFeatures = useMemo(
    () => getSimulatedMapFeatures(consultaActiva, selectedMlCluster),
    [consultaActiva, selectedMlCluster]
  );
  const popupPaddingTopLeft = useMemo(
    () => [leftPanelOpen ? 440 : 84, 96],
    [leftPanelOpen]
  );
  const popupPaddingBottomRight = useMemo(
    () => [rightPanelOpen ? 340 : 72, 92],
    [rightPanelOpen]
  );

  return (
    <div
      className="mapWrap"
      role="region"
      aria-label="Mapa interactivo de incendios forestales en México"
      aria-describedby="map-accessible-summary"
    >
      <p id="map-accessible-summary" className="srOnly">
        Mapa interactivo de México con controles para buscar ubicaciones, acercar, alejar, restablecer la vista y cambiar la capa base. Los resultados numéricos de la consulta también están disponibles en el panel de resultados y en la tabla del modal de resultados.
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
        {simulatedFeatures.map((feature) => {
          const isSelected = selectedFeatureId === feature.id;

          return (
            <CircleMarker
              key={feature.id}
              center={feature.position}
              radius={isSelected ? feature.radius + 2 : feature.radius}
              pathOptions={{
                color: isSelected ? "#FFFFFF" : "rgba(255,255,255,.92)",
                weight: isSelected ? 3 : 1,
                fillColor: feature.color,
                fillOpacity: feature.opacity ?? (isSelected ? 0.96 : 0.86),
              }}
              eventHandlers={{
                popupopen: () => setSelectedFeatureId(feature.id),
                popupclose: () => setSelectedFeatureId((currentId) => (currentId === feature.id ? null : currentId)),
              }}
            >
              {!isSelected && (
                <Tooltip
                  className={`mapFeatureTooltip mapFeatureTooltip-${feature.type}`}
                  direction="top"
                  offset={[0, -8]}
                  opacity={1}
                  sticky
                >
                  <MapFeatureDetails feature={feature} compact />
                </Tooltip>
              )}
              <Popup
                className={`mapFeaturePopup mapFeaturePopup-${feature.type}`}
                closeButton
                closeOnClick
                autoPan
                autoPanPaddingTopLeft={popupPaddingTopLeft}
                autoPanPaddingBottomRight={popupPaddingBottomRight}
                maxWidth={280}
                minWidth={220}
                offset={[0, -8]}
              >
                <MapFeatureDetails feature={feature} />
              </Popup>
            </CircleMarker>
          );
        })}
        <MapResizeInvalidator watchKey={`${leftPanelOpen}-${rightPanelOpen}-${baseLayerId}`} />
        <MapPopupCloser onClose={() => setSelectedFeatureId(null)} />
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
      <MapLegend consultaActiva={consultaActiva} rightPanelOpen={rightPanelOpen} />
    </div>
  );
}

function MapFeatureDetails({ feature, compact = false }) {
  const rows = compact ? feature.rows.slice(0, 7) : feature.rows;

  return (
    <div className={compact ? "mapFeatureTooltipInner" : "mapFeaturePopupScroll"} tabIndex={compact ? undefined : 0}>
      <div className="mapFeatureTooltipTitle">
        <span aria-hidden="true" />
        {feature.title}
      </div>
      <dl>
        {rows.map(([label, value]) => (
          <div key={`${feature.id}-${label}`}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
