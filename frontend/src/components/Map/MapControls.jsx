import { useState, useEffect } from "react";
import { useMap } from "react-leaflet";
import { Search, ZoomIn, ZoomOut, Home, Layers } from "lucide-react";
import "./MapControls.css";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };
const ICON_COLOR = "#0B4F4A";
const ICON_SIZE = 18;

const PLACES = [
  { id: "mx", label: "México (vista general)", type: "default", center: [23.6345, -102.5528], zoom: 5, estado: "", municipio: "" },

  { id: "cdmx", label: "Ciudad de México", type: "estado", center: [19.4326, -99.1332], zoom: 10, estado: "Ciudad de México", municipio: "" },
  { id: "jalisco", label: "Jalisco", type: "estado", center: [20.6597, -103.3496], zoom: 8, estado: "Jalisco", municipio: "" },
  { id: "nuevoleon", label: "Nuevo León", type: "estado", center: [25.6866, -100.3161], zoom: 9, estado: "Nuevo León", municipio: "" },
  { id: "chihuahua", label: "Chihuahua", type: "estado", center: [28.6329, -106.0691], zoom: 7, estado: "Chihuahua", municipio: "" },
  { id: "chiapas", label: "Chiapas", type: "estado", center: [16.7569, -93.1292], zoom: 8, estado: "Chiapas", municipio: "" },

  { id: "gdl", label: "Guadalajara, Jalisco", type: "municipio", center: [20.6736, -103.344], zoom: 12, estado: "Jalisco", municipio: "Guadalajara" },
  { id: "mty", label: "Monterrey, Nuevo León", type: "municipio", center: [25.6866, -100.3161], zoom: 12, estado: "Nuevo León", municipio: "Monterrey" },
  { id: "guachochi", label: "Guachochi, Chihuahua", type: "municipio", center: [26.8208, -107.0697], zoom: 10, estado: "Chihuahua", municipio: "Guachochi" }
];

export default function MapControls({
  defaultView = DEFAULT_VIEW,
  baseLayerId,
  onChangeLayer,
  layers,
  onBuscarIncendios,
  loading=false
}) {
  const map = useMap();

  const [layersOpen, setLayersOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [anio, setAnio] = useState("");

  const toggleSearch = () => {
    setSearchOpen((v) => !v);
    setLayersOpen(false);
  };

  const suggestions = PLACES.filter((p) =>
    p.label.toLowerCase().includes(query.trim().toLowerCase())
  ).slice(0, 6);

  const goToPlace = (place) => {
    map?.setView(place.center, place.zoom);

    onBuscarIncendios?.({
      estado: place.estado,
      municipio: place.municipio,
      anio
    });

    setSearchOpen(false);
    setQuery("");
  };

  const buscarManual = () => {
    onBuscarIncendios?.({
      estado: query,
      municipio: "",
      anio
    });
  };

  const limpiarBusqueda = () => {
    setQuery("");
    setAnio("");
    map?.setView(defaultView.center, defaultView.zoom);
    onBuscarIncendios?.({});
  };

  const zoomIn = () => map?.zoomIn();
  const zoomOut = () => map?.zoomOut();

  const resetView = () => {
    map?.setView(defaultView.center, defaultView.zoom);
    onBuscarIncendios?.({});
  };

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
    <>
      <div
        className="mapControls"
        aria-label="Controles del mapa"
        onMouseDown={stop}
        onDoubleClick={stop}
        onTouchStart={stop}
      >
        <button
          className="ctl"
          type="button"
          aria-label="Buscar"
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

            <input
              className="searchInput"
              value={anio}
              onChange={(e) => setAnio(e.target.value)}
              placeholder="Año, ejemplo 2025"
              style={{ marginTop: "8px" }}
            />

            <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
              <button type="button" onClick={buscarManual}>
                {loading ? "Buscando..." : "Buscar"}
              </button>

              <button type="button" onClick={limpiarBusqueda}>
                Limpiar
              </button>
            </div>

            {query.trim().length > 0 && (
              <div className="searchList" role="listbox" aria-label="Sugerencias">
                {suggestions.map((p) => (
                  <button
                    key={p.id}
                    className="searchItem"
                    type="button"
                    onClick={() => goToPlace(p)}
                  >
                    <span className="searchItemTitle">{p.label}</span>
                    <span className="searchItemMeta">{p.type}</span>
                  </button>
                ))}

                {suggestions.length === 0 && (
                  <div className="searchEmpty">Sin coincidencias.</div>
                )}
              </div>
            )}
          </div>
        )}

        {layersOpen && (
          <div className="layersMenu" role="dialog" aria-label="Capas del mapa">
            {Object.entries(layers).map(([id, layer]) => (
              <button
                key={id}
                className={`layersItem ${baseLayerId === id ? "isActive" : ""}`}
                type="button"
                onClick={() => selectLayer(id)}
              >
                {layer.name}
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );
}