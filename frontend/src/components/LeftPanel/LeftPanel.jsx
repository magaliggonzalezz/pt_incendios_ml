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

    // Demo: municipios
    const MUNICIPIOS_POR_ESTADO = {
    Aguascalientes: ["Aguascalientes", "Jesús María", "Calvillo"],
    Jalisco: ["Guadalajara", "Zapopan", "Tlaquepaque"],
    "Estado de México": ["Toluca", "Naucalpan de Juárez", "Ecatepec"],
    };

    export default function LeftPanel({ open, onToggle }) {
        const [layers, setLayers] = useState({
            hotspots: false,
            veg: false,
            ndvi: false,
    });

    const [filters, setFilters] = useState({
        startDate: "",
        endDate: "",
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
            startDate: "",
            endDate: "",
            state: "Todos los estados",
            municipality: "Todos los municipios",
        };

        const layersChanged =
        layers.hotspots !== defaultLayers.hotspots ||
        layers.veg !== defaultLayers.veg ||
        layers.ndvi !== defaultLayers.ndvi;

        const filtersChanged =
        filters.startDate !== defaultFilters.startDate ||
        filters.endDate !== defaultFilters.endDate ||
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

    const clearAll = () => {
        setLayers({ hotspots: false, veg: false, ndvi: false });
        setFilters({
            startDate: "",
            endDate: "",
            state: "Todos los estados",
            municipality: "Todos los municipios",
        });
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
                    <span>Fecha inicio</span>
                    <input
                    id="startDate"
                    name="startDate" 
                    type="date"
                    value={filters.startDate}
                    onChange={(e) => setFilters((p) => ({ ...p, startDate: e.target.value }))}
                    />
                </div>

                <div className="field">
                    <span>Fecha fin</span>
                    <input
                    id="endDate"
                    name="endDate" 
                    type="date"
                    value={filters.endDate}
                    onChange={(e) => setFilters((p) => ({ ...p, endDate: e.target.value }))}
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

                <button className="primaryBtn">Consultar</button>
                <button className="ghostBtn" disabled={!isDirty} onClick={clearAll}>Limpiar filtros</button>
            </div>
        </aside>
    );
}