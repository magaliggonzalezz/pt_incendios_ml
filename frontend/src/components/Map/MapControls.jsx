import { useEffect, useMemo, useRef, useState } from "react";
import { useMap } from "react-leaflet";
import { Search, ZoomIn, ZoomOut, Home, Layers, ScanSearch } from "lucide-react";
import { GEO_CATALOG } from "../../data/geoCatalog";
import "./MapControls.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const ICON_COLOR = "#0B4F4A";
const ICON_SIZE = 18;

function normalize(value, width) {
  if (value === undefined || value === null || value === "") return "";
  return String(value).padStart(width, "0");
}

const PLACE_OPTIONS = (() => {
  const states = new Map();
  const municipalities = [];

  GEO_CATALOG.forEach((row) => {
    const cveEnt = normalize(row.CVE_ENT, 2);
    const cveMun = normalize(row.CVE_MUN, 3);
    const cvegeo = normalize(row.CVEGEO, 5);
    if (cveEnt && !states.has(cveEnt)) {
      states.set(cveEnt, {
        id: `e-${cveEnt}`,
        label: row.NOM_ENT,
        type: "Estado",
        cveEnt,
        estado: row.NOM_ENT,
        municipio: "",
        cveMun: "",
        cvegeo: "",
        nivelAgregacion: "entidad",
      });
    }
    if (cvegeo) {
      municipalities.push({
        id: `m-${cvegeo}`,
        label: `${row.NOM_MUN}, ${row.NOM_ENT}`,
        type: "Municipio",
        cveEnt,
        estado: row.NOM_ENT,
        municipio: row.NOM_MUN,
        cveMun,
        cvegeo,
        nivelAgregacion: "municipio",
      });
    }
  });

  return [
    { id: "mx", label: "México", type: "Vista nacional", nivelAgregacion: "entidad", cveEnt: "", estado: "", municipio: "", cveMun: "", cvegeo: "" },
    ...states.values(),
    ...municipalities,
  ];
})();

export default function MapControls({
  defaultView = DEFAULT_VIEW,
  baseLayerId,
  onChangeLayer,
  layers,
  consultaActiva = null,
  onConsultaChange,
  rightPanelOpen = false,
}) {
  const map = useMap();
  const previousTerritoryRef = useRef(consultaActiva?.cveEnt || "");
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

  useEffect(() => {
    const currentTerritory = consultaActiva?.cveEnt || "";
    if (previousTerritoryRef.current && !currentTerritory) {
      map?.setView(defaultView.center, defaultView.zoom, { animate: false });
    }
    previousTerritoryRef.current = currentTerritory;
  }, [consultaActiva?.cveEnt, defaultView.center, defaultView.zoom, map]);

  const toggleSearch = () => {
    setSearchOpen((value) => !value);
    setLayersOpen(false);
    setBoxZoomHint(false);
  };

  const goToPlace = (place) => {
    if (place.id === "mx") map?.setView(defaultView.center, defaultView.zoom, { animate: false });

    onConsultaChange?.("consultaPatch", {
      nivelAgregacion: place.nivelAgregacion,
      cveEnt: place.cveEnt,
      estado: place.estado,
      municipio: place.municipio,
      cveMun: place.cveMun,
      cvegeo: place.cvegeo,
    });

    setSearchOpen(false);
    setQuery("");
    window.setTimeout(() => map?.invalidateSize(), 220);
  };

  const resetView = () => {
    map?.setView(defaultView.center, defaultView.zoom, { animate: false });
    onConsultaChange?.("consultaPatch", {
      nivelAgregacion: consultaActiva?.nivelAgregacion || "entidad",
      cveEnt: "",
      estado: "",
      municipio: "",
      cveMun: "",
      cvegeo: "",
    });
  };

  const stop = (event) => event.stopPropagation();

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setLayersOpen(false);
        setSearchOpen(false);
        setBoxZoomHint(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div
      className={`mapControls ${rightPanelOpen ? "rightPanelOpen" : ""}`}
      aria-label="Controles del mapa"
      onMouseDown={stop}
      onDoubleClick={stop}
      onTouchStart={stop}
    >
      <button className="ctl hasTooltip" data-tooltip="Buscar territorio" type="button" aria-label="Buscar territorio" aria-expanded={searchOpen} onClick={toggleSearch}>
        <Search size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Acercar" type="button" aria-label="Acercar" onClick={() => map?.zoomIn()}>
        <ZoomIn size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Alejar" type="button" aria-label="Alejar" onClick={() => map?.zoomOut()}>
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
          setBoxZoomHint((value) => !value);
          setLayersOpen(false);
          setSearchOpen(false);
        }}
      >
        <ScanSearch size={ICON_SIZE} color={ICON_COLOR} />
      </button>
      <button className="ctl hasTooltip" data-tooltip="Mapa base" type="button" aria-label="Mapa base" aria-expanded={layersOpen} onClick={() => {
        setLayersOpen((value) => !value);
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
