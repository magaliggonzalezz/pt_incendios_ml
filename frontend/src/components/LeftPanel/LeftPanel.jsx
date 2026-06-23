import { useMemo, useState } from "react";
import "./LeftPanel.css";

const ESTADOS = [
    "Todos los estados",
    "Aguascalientes",
    "Baja California",
    "Baja California Sur",
    "Campeche",
    "Chiapas",
    "Chihuahua",
    "Ciudad de México",
    "Coahuila",
    "Colima",
    "Durango",
    "Estado de México",
    "Guanajuato",
    "Guerrero",
    "Hidalgo",
    "Jalisco",
    "Michoacán",
    "Morelos",
    "Nayarit",
    "Nuevo León",
    "Oaxaca",
    "Puebla",
    "Querétaro",
    "Quintana Roo",
    "San Luis Potosí",
    "Sinaloa",
    "Sonora",
    "Tabasco",
    "Tamaulipas",
    "Tlaxcala",
    "Veracruz",
    "Yucatán",
    "Zacatecas",
    ];

const CENTROS_ESTADO = {
  "Aguascalientes": { center: [21.8853, -102.2916], zoom: 9 },
  "Baja California": { center: [30.8406, -115.2838], zoom: 7 },
  "Baja California Sur": { center: [26.0444, -111.6661], zoom: 7 },
  "Campeche": { center: [19.8301, -90.5349], zoom: 8 },
  "Chiapas": { center: [16.7569, -93.1292], zoom: 8 },
  "Chihuahua": { center: [28.6329, -106.0691], zoom: 7 },
  "Ciudad de México": { center: [19.4326, -99.1332], zoom: 10 },
  "Coahuila": { center: [27.0587, -101.7068], zoom: 7 },
  "Colima": { center: [19.2452, -103.7241], zoom: 9 },
  "Durango": { center: [24.0277, -104.6532], zoom: 7 },
  "Estado de México": { center: [19.4969, -99.7233], zoom: 8 },
  "Guanajuato": { center: [21.019, -101.2574], zoom: 8 },
  "Guerrero": { center: [17.4392, -99.5451], zoom: 8 },
  "Hidalgo": { center: [20.0911, -98.7624], zoom: 8 },
  "Jalisco": { center: [20.6597, -103.3496], zoom: 8 },
  "Michoacán": { center: [19.5665, -101.7068], zoom: 8 },
  "Morelos": { center: [18.6813, -99.1013], zoom: 9 },
  "Nayarit": { center: [21.7514, -104.8455], zoom: 8 },
  "Nuevo León": { center: [25.6866, -100.3161], zoom: 8 },
  "Oaxaca": { center: [17.0732, -96.7266], zoom: 8 },
  "Puebla": { center: [19.0414, -98.2063], zoom: 8 },
  "Querétaro": { center: [20.5888, -100.3899], zoom: 9 },
  "Quintana Roo": { center: [19.1817, -88.4791], zoom: 8 },
  "San Luis Potosí": { center: [22.1565, -100.9855], zoom: 8 },
  "Sinaloa": { center: [25.1721, -107.4795], zoom: 8 },
  "Sonora": { center: [29.2972, -110.3309], zoom: 7 },
  "Tabasco": { center: [17.8409, -92.6189], zoom: 8 },
  "Tamaulipas": { center: [24.2669, -98.8363], zoom: 7 },
  "Tlaxcala": { center: [19.3182, -98.2375], zoom: 9 },
  "Veracruz": { center: [19.1738, -96.1342], zoom: 7 },
  "Yucatán": { center: [20.7099, -89.0943], zoom: 8 },
  "Zacatecas": { center: [22.7709, -102.5832], zoom: 8 },
};

    // Demo: municipios
    const MUNICIPIOS_POR_ESTADO = {
    Aguascalientes: ["Aguascalientes", "Jesús María", "Calvillo"],
    Jalisco: ["Guadalajara", "Zapopan", "Tlaquepaque"],
    "Estado de México": ["Toluca", "Naucalpan de Juárez", "Ecatepec"],
    };

    export default function LeftPanel({ open, onToggle, onApplyFilters, onClearFilters }) {
        const [layers, setLayers] = useState({
            hotspots: false,
            veg: false,
            ndvi: false,
    });

    const [filters, setFilters] = useState({
        year: "",
        startDate: "",
        state: "Todos los estados",
        municipality: "Todos los municipios",
    });

    const municipalityEnabled = filters.state !== "Todos los estados";

    const municipios = useMemo(() => {
        if (!municipalityEnabled) return ["Todos los municipios"];
        const list = MUNICIPIOS_POR_ESTADO[filters.state] ?? [];
        return ["Todos los municipios", ...list];
    }, [filters.state, municipalityEnabled]);

    const isDirty = useMemo(() => {
        const defaultLayers = { hotspots: false, veg: false, ndvi: false };
        const defaultFilters = {
            year: "",
            startDate: "",
            state: "Todos los estados",
            municipality: "Todos los municipios",
        };

        const layersChanged =
        layers.hotspots !== defaultLayers.hotspots ||
        layers.veg !== defaultLayers.veg ||
        layers.ndvi !== defaultLayers.ndvi;

        const filtersChanged =
        filters.year !== defaultFilters.year ||
        filters.startDate !== defaultFilters.startDate ||
        filters.state !== defaultFilters.state ||
        filters.municipality !== defaultFilters.municipality;

        return layersChanged || filtersChanged;
    }, [layers, filters]);

    const onChangeState = (value) => {
        setFilters((prev) => ({
            ...prev,
            state: value,
            // al cambiar estado, resetea municipio (y además se deshabilita si vuelve a "Todos")
            municipality: "Todos los municipios",
        }));
    };

   const cleanFilters = () => {
  const cleanLayers = { hotspots: false, veg: false, ndvi: false };
  const cleanFilters = {
    year: "",
    endDate: "",
    state: "Todos los estados",
    municipality: "Todos los municipios",
  };

  setLayers(cleanLayers);
  setFilters(cleanFilters);

  onClearFilters?.();
};

    const consultar = () => {
    const vista = CENTROS_ESTADO[filters.state];

  onApplyFilters?.({
    anio: filters.year,
    fechaInicio: filters.startDate,
    estado: filters.state === "Todos los estados" ? "" : filters.state,
    municipio:
      filters.municipality === "Todos los municipios"
        ? ""
        : filters.municipality,
        vista: vista || null,
    capas: layers
  });
};

const clearAll = () => {
  const cleanLayers = {
    hotspots: false,
    veg: false,
    ndvi: false,
  };

  const cleanFilters = {
    year: "",
    startDate: "",
    state: "Todos los estados",
    municipality: "Todos los municipios",
  };

  setLayers(cleanLayers);
  setFilters(cleanFilters);

  onClearFilters?.();
};

    return (
        <aside className={`leftPanel ${open ? "open" : "closed"}`}>
            <button className="toggleBtn" onClick={onToggle} aria-label="Toggle left panel">
                {open ? "⟨" : "⟩"}
            </button>

            <div className="panelCard">
                <div className="panelTitle">Capas temáticas</div>
                <label className="row">
                    <input
                    id="layer-hotspots"
                    name="layerHotspots"
                    type="checkbox"
                    checked={layers.hotspots}
                    onChange={(e) => setLayers((p) => ({ ...p, hotspots: e.target.checked }))}
                    />
                    Puntos de calor
                </label>

                <label className="row">
                    <input
                    id="layer-veg"
                    name="layerVeg" 
                    type="checkbox"
                    checked={layers.veg}
                    onChange={(e) => setLayers((p) => ({ ...p, veg: e.target.checked }))}
                    />
                    Vegetación
                </label>

                <label className="row">
                    <input
                    id="layer-ndvi"
                    name="layerNdvi"
                    type="checkbox"
                    checked={layers.ndvi}
                    onChange={(e) => setLayers((p) => ({ ...p, ndvi: e.target.checked }))}
                    />
                    NDVI
                </label>
            </div>

            <div className="panelCard">
                <div className="panelTitle">Filtros</div>
                <div className="field">
                    <span>Año</span>
                    <input
                    id="year"
                    name="year" 
                    type="number"
                    value={filters.year}
                    onChange={(e) => setFilters((p) => ({ ...p, year: e.target.value }))}
                    placeholder="Ej. 2025"
                    />
                </div>

                <div className="field">
                    <span>Fecha Inicio</span>
                    <input
                    id="startDate"
                    name="startDate" 
                    type="date"
                    value={filters.startDate}
                    onChange={(e) => setFilters((p) => ({ ...p, startDate: e.target.value }))}
                    />
                </div>

                <div className="field">
                    <span>Estado</span>
                    <select
                    id="stateSelect"
                    name="state" 
                    className="selectInput"
                    value={filters.state}
                    onChange={(e) => onChangeState(e.target.value)}
                    >
                        {ESTADOS.map((st) => (
                            <option key={st} value={st}>
                                {st}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="field">
                    <span>Municipio</span>
                    <select
                    id="municipalitySelect" 
                    name="municipality"    
                    className="selectInput"
                    value={filters.municipality}
                    onChange={(e) => setFilters((p) => ({ ...p, municipality: e.target.value }))}
                    disabled={!municipalityEnabled}
                    >
                        {municipios.map((m) => (
                            <option key={m} value={m}>
                                {m}
                            </option>
                        ))}
                    </select>

                    {/*
                    {!municipalityEnabled && (
                        <small className="helperText">Selecciona un estado primero</small>
                    )}*/}
                </div>

                <button className="primaryBtn" onClick={consultar}>
                Consultar
                </button>
                <button className="ghostBtn" disabled={!isDirty} onClick={clearAll}>Limpiar filtros</button>
            </div>
        </aside>
    );
}