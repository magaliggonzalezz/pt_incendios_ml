import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { useMap } from "react-leaflet";
import { Search, ZoomIn, ZoomOut, Home, Layers, ScanSearch } from "lucide-react";
import { GEO_CATALOG } from "../../data/geoCatalog";
import { obtenerGeometriasMunicipios } from "../../services/geometrias.service";
import "./MapControls.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const ICON_COLOR = "#0B4F4A";
const ICON_SIZE = 18;
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";
const MDE_TILE_URL = `${API_URL}/api/recursos/relieve-mde/tiles/{z}/{x}/{y}.png`;
const MDE_PANE = "mdeReliefPane";
const MDE_APPEARANCE = {
  esri: { opacity: 0.72, filter: "contrast(2.15) brightness(1.12)", blendMode: "soft-light" },
  osm: { opacity: 0.92, filter: "contrast(2.45) brightness(1.10)", blendMode: "multiply" },
  topo: { opacity: 0.84, filter: "contrast(2.30) brightness(1.10)", blendMode: "multiply" },
};

function normalize(value, width) {
  if (value === undefined || value === null || value === "") return "";
  return String(value).padStart(width, "0");
}

function featureCode(feature, level) {
  const props = feature?.properties || {};
  return level === "municipio"
    ? normalize(props.cvegeo ?? props.CVEGEO, 5)
    : normalize(props.cve_ent ?? props.CVE_ENT ?? props.cvegeo ?? props.CVEGEO, 2);
}

const PLACE_OPTIONS = (() => {
  const states = new Map();
  const municipalities = [];

  GEO_CATALOG.forEach((row) => {
    const cveEnt = normalize(row.CVE_ENT, 2);
    const cvegeo = normalize(row.CVEGEO, 5);
    if (cveEnt && !states.has(cveEnt)) {
      states.set(cveEnt, {
        id: `e-${cveEnt}`,
        label: row.NOM_ENT,
        type: "Estado",
        cveEnt,
      });
    }
    if (cvegeo) {
      municipalities.push({
        id: `m-${cvegeo}`,
        label: `${row.NOM_MUN}, ${row.NOM_ENT}`,
        type: "Municipio",
        cveEnt,
        cvegeo,
      });
    }
  });

  return [
    { id: "mx", label: "México", type: "Vista nacional" },
    ...states.values(),
    ...municipalities,
  ];
})();

export default function MapControls({
  defaultView = DEFAULT_VIEW,
  baseLayerId,
  onChangeLayer,
  layers,
  estadosGeojson,
  rightPanelOpen = false,
}) {
  const map = useMap();
  const controlsRef = useRef(null);
  const mdeLayerRef = useRef(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [boxZoomHint, setBoxZoomHint] = useState(false);

  const suggestions = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("es-MX");
    if (!normalizedQuery) return [];
    return PLACE_OPTIONS.filter((place) =>
      place.label.toLocaleLowerCase("es-MX").includes(normalizedQuery)
    ).slice(0, 8);
  }, [query]);

  const closeFloatingControls = () => {
    setLayersOpen(false);
    setSearchOpen(false);
    setBoxZoomHint(false);
  };

  const announceControlOverlay = () => {
    window.dispatchEvent(new CustomEvent("map:controls-overlay-open"));
  };

  const toggleSearch = () => {
    setSearchOpen((value) => {
      const next = !value;
      if (next) announceControlOverlay();
      return next;
    });
    setLayersOpen(false);
    setBoxZoomHint(false);
  };

  const fitGeojson = (geojson, maxZoom = 11) => {
    if (!geojson?.features?.length) return false;
    const bounds = L.geoJSON(geojson).getBounds();
    if (!bounds.isValid()) return false;
    map.fitBounds(bounds, { padding: [36, 36], maxZoom });
    return true;
  };

  const goToPlace = async (place) => {
    if (place.id === "mx") {
      map.setView(defaultView.center, defaultView.zoom, { animate: false });
    } else if (place.type === "Estado") {
      const feature = estadosGeojson?.features?.find((item) => featureCode(item, "entidad") === place.cveEnt);
      if (feature) fitGeojson({ type: "FeatureCollection", features: [feature] }, 9);
    } else if (place.type === "Municipio") {
      try {
        const municipios = await obtenerGeometriasMunicipios(place.cveEnt);
        const feature = municipios?.features?.find((item) => featureCode(item, "municipio") === place.cvegeo);
        if (feature) fitGeojson({ type: "FeatureCollection", features: [feature] }, 12);
      } catch {
        // La búsqueda cartográfica no modifica la consulta si la geometría no está disponible.
      }
    }

    setSearchOpen(false);
    setQuery("");
    window.setTimeout(() => map.invalidateSize(), 220);
  };

  const resetView = () => {
    map.setView(defaultView.center, defaultView.zoom, { animate: false });
    closeFloatingControls();
  };

  const stop = (event) => event.stopPropagation();

  useEffect(() => {
    let pane = map.getPane(MDE_PANE);
    if (!pane) pane = map.createPane(MDE_PANE);
    pane.style.zIndex = "250";
    pane.style.pointerEvents = "none";
  }, [map]);

  useEffect(() => {
    const appearance = MDE_APPEARANCE[baseLayerId] || MDE_APPEARANCE.osm;
    const pane = map.getPane(MDE_PANE);
    if (pane) {
      pane.style.filter = appearance.filter;
      pane.style.mixBlendMode = appearance.blendMode;
    }
    mdeLayerRef.current?.setOpacity(appearance.opacity);
  }, [map, baseLayerId]);

  useEffect(() => {
    const onRelieveMdeChange = (event) => {
      const active = Boolean(event.detail?.active);

      if (active && !mdeLayerRef.current) {
        const appearance = MDE_APPEARANCE[baseLayerId] || MDE_APPEARANCE.osm;
        const pane = map.getPane(MDE_PANE);
        if (pane) {
          pane.style.filter = appearance.filter;
          pane.style.mixBlendMode = appearance.blendMode;
        }

        mdeLayerRef.current = L.tileLayer(MDE_TILE_URL, {
          minZoom: 4,
          maxNativeZoom: 10,
          maxZoom: 18,
          opacity: appearance.opacity,
          pane: MDE_PANE,
          attribution: "Relieve derivado del MDE INEGI",
          updateWhenIdle: true,
          keepBuffer: 1,
        }).addTo(map);
        return;
      }

      if (!active && mdeLayerRef.current) {
        map.removeLayer(mdeLayerRef.current);
        mdeLayerRef.current = null;
      }
    };

    window.addEventListener("map:relieve-mde-change", onRelieveMdeChange);
    return () => {
      window.removeEventListener("map:relieve-mde-change", onRelieveMdeChange);
      if (mdeLayerRef.current) {
        map.removeLayer(mdeLayerRef.current);
        mdeLayerRef.current = null;
      }
    };
  }, [map, baseLayerId]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") closeFloatingControls();
    };
    const onPointerDown = (event) => {
      if (controlsRef.current?.contains(event.target)) return;
      closeFloatingControls();
    };
    const onLegendOrPopupOpen = () => closeFloatingControls();

    window.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("map:legend-open", onLegendOrPopupOpen);
    window.addEventListener("map:feature-popup-open", onLegendOrPopupOpen);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("map:legend-open", onLegendOrPopupOpen);
      window.removeEventListener("map:feature-popup-open", onLegendOrPopupOpen);
    };
  }, []);

  return (
    <div
      ref={controlsRef}
      className={`mapControls ${rightPanelOpen ? "rightPanelOpen" : ""}`}
      aria-label="Controles del mapa"
      onMouseDown={stop}
      onDoubleClick={stop}
      onTouchStart={stop}
    >
      <button className="ctl hasTooltip" data-tooltip="Buscar territorio" type="button" aria-label="Buscar territorio" aria-expanded={searchOpen} onClick={toggleSearch}>
        <Search size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Acercar" type="button" aria-label="Acercar" onClick={() => map.zoomIn()}>
        <ZoomIn size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Alejar" type="button" aria-label="Alejar" onClick={() => map.zoomOut()}>
        <ZoomOut size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Vista nacional" type="button" aria-label="Restablecer vista nacional" onClick={resetView}>
        <Home size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button
        className="ctl hasTooltip"
        data-tooltip="Zoom por área"
        type="button"
        aria-label="Zoom por área"
        aria-expanded={boxZoomHint}
        onClick={() => {
          setBoxZoomHint((value) => {
            const next = !value;
            if (next) announceControlOverlay();
            return next;
          });
          setLayersOpen(false);
          setSearchOpen(false);
        }}
      >
        <ScanSearch size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Mapa base" type="button" aria-label="Mapa base" aria-expanded={layersOpen} onClick={() => {
        setLayersOpen((value) => {
          const next = !value;
          if (next) announceControlOverlay();
          return next;
        });
        setSearchOpen(false);
        setBoxZoomHint(false);
      }}>
        <Layers size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      {searchOpen ? (
        <div className="searchPanel" role="dialog" aria-label="Búsqueda en el marco geoestadístico">
          <input
            className="searchInput"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Estado o municipio..."
            autoFocus
          />
          <div className="searchList" role="listbox" aria-label="Resultados de búsqueda">
            {query.trim() ? suggestions.map((place) => (
              <button key={place.id} className="searchItem" type="button" onClick={() => goToPlace(place)}>
                <span className="searchItemTitle">{place.label}</span>
                <span className="searchItemMeta">{place.type}</span>
              </button>
            )) : <div className="searchEmpty">Escribe un estado o municipio.</div>}
            {query.trim() && !suggestions.length ? <div className="searchEmpty">Sin coincidencias.</div> : null}
          </div>
        </div>
      ) : null}

      {boxZoomHint ? (
        <div className="boxZoomHint" role="status">
          Mantén <strong>Shift</strong> y arrastra un rectángulo sobre el mapa para acercarte a un área.
        </div>
      ) : null}

      {layersOpen ? (
        <div className="layersMenu" role="dialog" aria-label="Mapa base">
          {Object.entries(layers).map(([id, layer]) => (
            <button
              key={id}
              className={`layersItem ${baseLayerId === id ? "isActive" : ""}`}
              type="button"
              aria-pressed={baseLayerId === id}
              onClick={() => {
                onChangeLayer?.(id);
                setLayersOpen(false);
              }}
            >
              {layer.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
