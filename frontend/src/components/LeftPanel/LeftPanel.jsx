import { useMemo } from "react";
import { LAYER_GROUPS, INITIAL_ACTIVE_LAYERS, INITIAL_SMN_FILTERS } from "../../data/dashboardMock";
import "./LeftPanel.css";

const MESES = [
  { value: "", label: "Selecciona mes" },
  { value: "01", label: "Enero" },
  { value: "02", label: "Febrero" },
  { value: "03", label: "Marzo" },
  { value: "04", label: "Abril" },
  { value: "05", label: "Mayo" },
  { value: "06", label: "Junio" },
  { value: "07", label: "Julio" },
  { value: "08", label: "Agosto" },
  { value: "09", label: "Septiembre" },
  { value: "10", label: "Octubre" },
  { value: "11", label: "Noviembre" },
  { value: "12", label: "Diciembre" },
];

const MIN_YEAR = 2001;
const MAX_YEAR = 2025;
const YEAR_OPTIONS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, index) =>
  String(MIN_YEAR + index)
).reverse();

const getLayerDisabled = (layer, nivelAgregacion) => {
  if (!layer.nivel) return false;
  return layer.nivel !== nivelAgregacion;
};

const SMN_FILTERS = [
  { id: "operando", label: "Operando" },
  { id: "suspendida", label: "Suspendida" },
];

const SMN_SCOPE_OPTIONS = [
  { value: "todas", label: "Todas las estaciones" },
  { value: "periodo", label: "Con datos del período" },
];

export default function LeftPanel({
  open,
  onToggle,
  consultaActiva,
  consultaEjecutada = false,
  onConsultaChange,
  onConsultar,
  onResetConsulta,
  estados = [],
  municipios = [],
  isLoading = false,
}) {
  const selectedState = consultaActiva?.cveEnt || "";
  const selectedMunicipality = consultaActiva?.cvegeo || "";
  const showMunicipality = consultaActiva?.nivelAgregacion === "municipio";
  const municipalityEnabled = showMunicipality && selectedState !== "";
  const tipoPeriodo = consultaActiva?.tipoPeriodo || "";

  const consultaCompleta =
    Boolean(consultaActiva?.nivelAgregacion) &&
    Boolean(tipoPeriodo) &&
    (!showMunicipality || Boolean(selectedState)) &&
    Boolean(consultaActiva?.anio) &&
    (tipoPeriodo !== "anio_mes" || Boolean(consultaActiva?.mes));

  const isDirty = useMemo(() => {
    const currentLayers = consultaActiva?.capasActivas ?? {};
    const layersChanged = Object.entries(INITIAL_ACTIVE_LAYERS).some(
      ([key, value]) => currentLayers[key] !== value
    );
    const currentSmnFilters = consultaActiva?.filtrosSmn ?? {};
    const smnFiltersChanged = Object.entries(INITIAL_SMN_FILTERS).some(
      ([key, value]) => currentSmnFilters[key] !== value
    );

    const consultaChanged =
      consultaActiva?.nivelAgregacion !== "" ||
      consultaActiva?.tipoPeriodo !== "" ||
      consultaActiva?.anio !== "" ||
      consultaActiva?.mes !== "" ||
      consultaActiva?.estado !== "" ||
      consultaActiva?.municipio !== "" ||
      consultaActiva?.cveEnt !== "" ||
      consultaActiva?.cveMun !== "" ||
      consultaActiva?.cvegeo !== "";

    return layersChanged || smnFiltersChanged || consultaChanged;
  }, [consultaActiva]);

  const onChangeNivelAgregacion = (value) => {
    onConsultaChange?.("nivelAgregacion", value);
  };

  const onChangeState = (cveEnt) => {
    const state = estados.find((item) => item.cve_ent === cveEnt);
    onConsultaChange?.("consultaPatch", {
      cveEnt,
      estado: state?.nombre || "",
      municipio: "",
      cveMun: "",
      cvegeo: "",
    });
  };

  const onChangeMunicipio = (cvegeo) => {
    const municipality = municipios.find((item) => item.cvegeo === cvegeo);
    onConsultaChange?.("consultaPatch", {
      cvegeo,
      cveMun: municipality?.cve_mun || "",
      municipio: municipality?.nombre || "",
    });
  };

  return (
    <aside className={`leftPanel ${open ? "open" : "closed"}`} aria-label="Panel de filtros de consulta">
      <button
        className="toggleBtn"
        type="button"
        onClick={onToggle}
        aria-label={open ? "Ocultar panel de filtros" : "Mostrar panel de filtros"}
        aria-expanded={open}
      >
        {open ? "⟨" : "⟩"}
      </button>

      <div className="panelContent">
        <div className="panelCard">
          <div className="panelTitle">Consulta</div>

          <div className="field">
            <label htmlFor="aggregationLevel">Nivel de análisis</label>
            <select
              id="aggregationLevel"
              className="selectInput"
              value={consultaActiva?.nivelAgregacion ?? ""}
              onChange={(e) => onChangeNivelAgregacion(e.target.value)}
            >
              <option value="">Selecciona nivel de análisis</option>
              <option value="entidad">Estatal</option>
              <option value="municipio">Municipal</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="periodType">Tipo de período</label>
            <select
              id="periodType"
              className="selectInput"
              value={tipoPeriodo}
              onChange={(e) => onConsultaChange?.("tipoPeriodo", e.target.value)}
            >
              <option value="">Selecciona tipo de período</option>
              <option value="anio">Año</option>
              <option value="anio_mes">Año y mes</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="yearInput">Año</label>
            <select
              id="yearInput"
              className="selectInput"
              value={consultaActiva?.anio ?? ""}
              onChange={(e) => onConsultaChange?.("anio", e.target.value)}
            >
              <option value="">Selecciona año</option>
              {YEAR_OPTIONS.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>

          {tipoPeriodo === "anio_mes" && (
            <div className="field">
              <label htmlFor="monthSelect">Mes</label>
              <select
                id="monthSelect"
                className="selectInput"
                value={consultaActiva?.mes ?? ""}
                onChange={(e) => onConsultaChange?.("mes", e.target.value)}
              >
                {MESES.map((month) => (
                  <option key={month.value || "empty"} value={month.value}>{month.label}</option>
                ))}
              </select>
            </div>
          )}

          <div className="field">
            <label htmlFor="stateSelect">Estado</label>
            <select
              id="stateSelect"
              className="selectInput"
              value={selectedState}
              onChange={(e) => onChangeState(e.target.value)}
            >
              <option value="">
                {showMunicipality ? "Selecciona estado" : "Todos los estados"}
              </option>
              {estados.map((state) => (
                <option key={state.cve_ent} value={state.cve_ent}>
                  {state.nombre}
                </option>
              ))}
            </select>
          </div>

          {showMunicipality && (
            <div className="field">
              <label htmlFor="municipalitySelect">Municipio</label>
              <select
                id="municipalitySelect"
                className="selectInput"
                value={selectedMunicipality}
                onChange={(e) => onChangeMunicipio(e.target.value)}
                disabled={!municipalityEnabled}
              >
                {!selectedState ? (
                  <option value="">Selecciona estado primero</option>
                ) : (
                  <option value="">Todos los municipios</option>
                )}
                {municipios.map((municipality) => (
                  <option key={municipality.cvegeo} value={municipality.cvegeo}>
                    {municipality.nombre}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            className="primaryBtn"
            onClick={() => onConsultar?.()}
            disabled={!consultaCompleta || isLoading}
          >
            {isLoading ? "Consultando..." : "Consultar"}
          </button>
          <button
            type="button"
            className="ghostBtn"
            disabled={isLoading || (!consultaEjecutada && !isDirty)}
            onClick={onResetConsulta}
          >
            Limpiar filtros
          </button>
        </div>

        <div className="panelCard layersCard">
          <div className="panelTitle">Capas disponibles</div>
          <div className="layerGroups">
            {LAYER_GROUPS.map((group) => (
              <section className="layerGroup" key={group.id} aria-label={group.title}>
                <div className="layerGroupTitle">{group.title}</div>
                {group.layers.map((layer) => {
                  const disabled = getLayerDisabled(layer, consultaActiva?.nivelAgregacion);
                  return (
                    <label className={`row layerRow ${disabled ? "isDisabled" : ""}`} key={layer.id}>
                      <input
                        type="checkbox"
                        aria-label={layer.label}
                        checked={consultaActiva?.capasActivas?.[layer.id] ?? false}
                        disabled={disabled}
                        onChange={(e) =>
                          onConsultaChange?.("capasActivas", {
                            capa: layer.id,
                            activo: e.target.checked,
                          })
                        }
                      />
                      <span>
                        {layer.label}
                        {layer.helper && <small>{layer.helper}</small>}
                      </span>
                    </label>
                  );
                })}

                {group.id === "smn" && (
                  <div
                    className={`smnFilters ${consultaActiva?.capasActivas?.estacionesSmn ? "" : "isDisabled"}`}
                    aria-label="Filtros de estaciones SMN-CONAGUA"
                  >
                    <div className="smnFilterBlock" role="radiogroup" aria-label="Alcance de estaciones SMN-CONAGUA">
                      <div className="smnFiltersTitle">Alcance</div>
                      {SMN_SCOPE_OPTIONS.map((option) => (
                        <label className="row smnFilterRow" key={option.value}>
                          <input
                            name="smn-scope"
                            type="radio"
                            value={option.value}
                            checked={(consultaActiva?.filtrosSmn?.alcance ?? "todas") === option.value}
                            disabled={!consultaActiva?.capasActivas?.estacionesSmn}
                            onChange={(e) => onConsultaChange?.("filtrosSmn", { alcance: e.target.value })}
                          />
                          <span>{option.label}</span>
                        </label>
                      ))}
                    </div>

                    <div className="smnFilterBlock" aria-label="Situación operativa de estaciones SMN-CONAGUA">
                      <div className="smnFiltersTitle">Situación operativa</div>
                      {SMN_FILTERS.map((filter) => (
                        <label className="row smnFilterRow" key={filter.id}>
                          <input
                            type="checkbox"
                            checked={consultaActiva?.filtrosSmn?.[filter.id] ?? false}
                            disabled={!consultaActiva?.capasActivas?.estacionesSmn}
                            onChange={(e) => onConsultaChange?.("filtrosSmn", { [filter.id]: e.target.checked })}
                          />
                          <span>{filter.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
