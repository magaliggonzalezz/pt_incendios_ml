import { useEffect, useState } from "react";
import { useMap } from "react-leaflet";
import { Search, ZoomIn, ZoomOut, Home, Layers } from "lucide-react";
import "./MapControls.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const ICON_COLOR = "#0B4F4A";
const ICON_SIZE = 18;

const PLACES = [
  { id: "mx", label: "México (vista general)", type: "default", center: [23.6345, -102.5528], zoom: 5 },
  { id: "cdmx", label: "Ciudad de México", type: "estado", center: [19.4326, -99.1332], zoom: 10 },
  { id: "jalisco", label: "Jalisco", type: "estado", center: [20.6597, -103.3496], zoom: 8 },
  { id: "nuevoleon", label: "Nuevo León", type: "estado", center: [25.6866, -100.3161], zoom: 9 },
  { id: "gdl", label: "Guadalajara, Jalisco", type: "municipio", center: [20.6736, -103.344], zoom: 12 },
  { id: "mty", label: "Monterrey, Nuevo León", type: "municipio", center: [25.6866, -100.3161], zoom: 12 },
];

const PLACE_QUERY = {
  mx: { nivelAgregacion: "entidad", estado: "", municipio: "" },
  cdmx: { nivelAgregacion: "entidad", estado: "Ciudad de México", municipio: "" },
  jalisco: { nivelAgregacion: "entidad", estado: "Jalisco", municipio: "" },
  nuevoleon: { nivelAgregacion: "entidad", estado: "Nuevo León", municipio: "" },
  gdl: { nivelAgregacion: "municipio", estado: "Jalisco", municipio: "Guadalajara" },
  mty: { nivelAgregacion: "municipio", estado: "Nuevo León", municipio: "Monterrey" },
};

export default function MapControls({
  defaultView = DEFAULT_VIEW,
  baseLayerId,
  onChangeLayer,
  layers,
  consultaActiva = null,
  onConsultaChange,
  onConsultar,
  rightPanelOpen = false,
}) {
  const map = useMap();
  const [layersOpen, setLayersOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");

  const toggleSearch = () => {
    setSearchOpen((v) => !v);
    setLayersOpen(false);
  };

  const suggestions = PLACES.filter((p) =>
    p.label.toLowerCase().includes(query.trim().toLowerCase())
  ).slice(0, 6);

  const buildConsultaForPlace = (place) => {
    const placeQuery = PLACE_QUERY[place.id] ?? PLACE_QUERY.mx;
    return {
      ...(consultaActiva ?? {}),
      ...placeQuery,
      cveEnt: "",
      cveMun: "",
      cvegeo: "",
    };
  };

  const updateConsultaForPlace = (place) => {
    const nextConsulta = buildConsultaForPlace(place);
    onConsultaChange?.("nivelAgregacion", nextConsulta.nivelAgregacion);
    onConsultaChange?.("estado", nextConsulta.estado);
    onConsultaChange?.("municipio", nextConsulta.municipio);
    onConsultaChange?.("cveEnt", "");
    onConsultaChange?.("cveMun", "");
    onConsultaChange?.("cvegeo", "");
    onConsultar?.(nextConsulta);
  };

  const goToPlace = (place) => {
    map?.setView(place.center, place.zoom);
    window.setTimeout(() => map?.invalidateSize(), 220);
    updateConsultaForPlace(place);
    setSearchOpen(false);
    setQuery("");
  };

  const zoomIn = () => map?.zoomIn();
  const zoomOut = () => map?.zoomOut();
  const resetView = () => map?.setView(defaultView.center, defaultView.zoom);
  const toggleLayers = () => setLayersOpen((v) => !v);

  const selectLayer = (layerId) => {
    if (typeof onChangeLayer === "function") onChangeLayer(layerId);
    setLayersOpen(false);
  };

  const stop = (e) => {
    e.stopPropagation();
  };

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        setLayersOpen(false);
        setSearchOpen(false);
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
      <button
        className="ctl"
        type="button"
        aria-label="Buscar"
        aria-expanded={searchOpen}
        aria-controls="map-search-panel"
        onClick={toggleSearch}
      >
        <Search size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      <button className="ctl" type="button" aria-label="Acercar" onClick={zoomIn}>
        <ZoomIn size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      <button className="ctl" type="button" aria-label="Alejar" onClick={zoomOut}>
        <ZoomOut size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      <button className="ctl" type="button" aria-label="Restablecer vista" onClick={resetView}>
        <Home size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      <button
        className="ctl"
        type="button"
        aria-label="Capas"
        aria-expanded={layersOpen}
        aria-controls="map-layers-menu"
        onClick={toggleLayers}
      >
        <Layers size={ICON_SIZE} color={ICON_COLOR} />
      </button>

      {searchOpen && (
        <div className="searchPanel" role="dialog" aria-label="Búsqueda por estado o municipio">
          <input
            className="searchInput"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar estado o municipio..."
            autoFocus
          />

          {query.trim().length > 0 && (
            <div className="searchList" role="listbox" aria-label="Sugerencias">
              {suggestions.map((p) => (
                <button key={p.id} className="searchItem" type="button" onClick={() => goToPlace(p)}>
                  <span className="searchItemTitle">{p.label}</span>
                  <span className="searchItemMeta">{p.type}</span>
                </button>
              ))}

              {suggestions.length === 0 && <div className="searchEmpty">Sin coincidencias.</div>}
            </div>
          )}
        </div>
      )}

      {layersOpen && (
        <div id="map-layers-menu" className="layersMenu" role="dialog" aria-label="Capas del mapa">
          {Object.entries(layers).map(([id, layer]) => (
            <button
              key={id}
              className={`layersItem ${baseLayerId === id ? "isActive" : ""}`}
              type="button"
              aria-pressed={baseLayerId === id}
              onClick={() => selectLayer(id)}
            >
              {layer.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
