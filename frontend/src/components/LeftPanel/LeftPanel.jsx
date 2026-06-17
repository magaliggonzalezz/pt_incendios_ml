import { useMemo } from "react";
import { LAYER_GROUPS, INITIAL_ACTIVE_LAYERS, INITIAL_SMN_FILTERS } from "../../data/dashboardMock";
import "./LeftPanel.css";

const ESTADOS = [
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

const MUNICIPIOS_POR_ESTADO = {
  Aguascalientes: ["Aguascalientes", "Jesús María", "Calvillo"],
  Jalisco: ["Guadalajara", "Zapopan", "Tlaquepaque"],
  "Estado de México": ["Toluca", "Naucalpan de Juárez", "Ecatepec"],
};

const MESES = [
  { value: "", label: "Todos los meses" },
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
const MIN_DATE = "2001-01-01";
const MAX_DATE = "2025-12-31";

const YEAR_OPTIONS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, index) =>
  String(MIN_YEAR + index)
).reverse();

const clampDate = (value) => {
  if (!value) return "";
  if (value < MIN_DATE) return MIN_DATE;
  if (value > MAX_DATE) return MAX_DATE;
  return value;
};

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
}) {
  const selectedState = consultaActiva?.estado || "";
  const selectedMunicipality = consultaActiva?.municipio || "";
  const showMunicipality = consultaActiva?.nivelAgregacion === "municipio";
  const municipalityEnabled = showMunicipality && selectedState !== "";
  const tipoPeriodo = consultaActiva?.tipoPeriodo || "anio";

  const municipios = useMemo(() => {
    if (!selectedState) return [];
    return MUNICIPIOS_POR_ESTADO[selectedState] ?? [];
  }, [selectedState]);

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
      consultaActiva?.nivelAgregacion !== "entidad" ||
      consultaActiva?.tipoPeriodo !== "anio" ||
      consultaActiva?.anio !== "2025" ||
      consultaActiva?.mes !== "" ||
      consultaActiva?.anioInicio !== "" ||
      consultaActiva?.anioFin !== "" ||
      consultaActiva?.fechaInicio !== "" ||
      consultaActiva?.fechaFin !== "" ||
      consultaActiva?.estado !== "" ||
      consultaActiva?.municipio !== "" ||
      consultaActiva?.cveEnt !== "" ||
      consultaActiva?.cveMun !== "" ||
      consultaActiva?.cvegeo !== "";

    return layersChanged || smnFiltersChanged || consultaChanged;
  }, [consultaActiva]);

  const onChangeYear = (value) => onConsultaChange?.("anio", value);

  const onChangeAnioInicio = (value) => {
    const nextStart = value;
    onConsultaChange?.("anioInicio", nextStart);
    if (consultaActiva?.anioFin && nextStart && Number(nextStart) > Number(consultaActiva.anioFin)) {
      onConsultaChange?.("anioFin", nextStart);
    }
  };

  const onChangeAnioFin = (value) => {
    const nextEnd = value;
    onConsultaChange?.("anioFin", nextEnd);
    if (consultaActiva?.anioInicio && nextEnd && Number(nextEnd) < Number(consultaActiva.anioInicio)) {
      onConsultaChange?.("anioInicio", nextEnd);
    }
  };

  const onChangeFechaInicio = (value) => {
    const nextStart = clampDate(value);
    onConsultaChange?.("fechaInicio", nextStart);
    if (consultaActiva?.fechaFin && nextStart && nextStart > consultaActiva.fechaFin) {
      onConsultaChange?.("fechaFin", nextStart);
    }
  };

  const onChangeFechaFin = (value) => {
    const nextEnd = clampDate(value);
    onConsultaChange?.("fechaFin", nextEnd);
    if (consultaActiva?.fechaInicio && nextEnd && nextEnd < consultaActiva.fechaInicio) {
      onConsultaChange?.("fechaInicio", nextEnd);
    }
  };

  const onChangeState = (value) => {
    onConsultaChange?.("estado", value);
    onConsultaChange?.("municipio", "");
    onConsultaChange?.("cveMun", "");
    onConsultaChange?.("cvegeo", "");
  };

  const onChangeNivelAgregacion = (value) => {
    onConsultaChange?.("nivelAgregacion", value);
    onConsultaChange?.("municipio", "");
    onConsultaChange?.("cveMun", "");
    onConsultaChange?.("cvegeo", "");
  };

  const onChangeMunicipio = (value) => {
    onConsultaChange?.("municipio", value);
    onConsultaChange?.("cveMun", "");
    onConsultaChange?.("cvegeo", "");
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
              name="nivelAgregacion"
              className="selectInput"
              value={consultaActiva?.nivelAgregacion ?? "entidad"}
              onChange={(e) => onChangeNivelAgregacion(e.target.value)}
            >
              <option value="entidad">Estatal</option>
              <option value="municipio">Municipal</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="periodType">Tipo de período</label>
            <select
              id="periodType"
              name="tipoPeriodo"
              className="selectInput"
              value={tipoPeriodo}
              onChange={(e) => onConsultaChange?.("tipoPeriodo", e.target.value)}
            >
              <option value="anio">Año</option>
              <option value="anio_mes">Año y mes</option>
              <option value="rango">Rango de fechas</option>
              <option value="rango_anios">Rango de años</option>
            </select>
          </div>

          {(tipoPeriodo === "anio" || tipoPeriodo === "anio_mes") && (
            <div className="field">
              <label htmlFor="yearInput">Año</label>
              <select
                id="yearInput"
                name="anio"
                className="selectInput"
                value={consultaActiva?.anio ?? "2025"}
                onChange={(e) => onChangeYear(e.target.value)}
              >
                {YEAR_OPTIONS.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
          )}

          {tipoPeriodo === "anio_mes" && (
            <div className="field">
              <label htmlFor="monthSelect">Mes</label>
              <select
                id="monthSelect"
                name="mes"
                className="selectInput"
                value={consultaActiva?.mes ?? ""}
                onChange={(e) => onConsultaChange?.("mes", e.target.value)}
              >
                {MESES.map((month) => (
                  <option key={month.value || "all"} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {tipoPeriodo === "rango" && (
            <>
              <div className="field">
                <label htmlFor="startDate">Fecha inicio</label>
                <input
                  id="startDate"
                  name="startDate"
                  type="date"
                  min={MIN_DATE}
                  max={MAX_DATE}
                  value={consultaActiva?.fechaInicio ?? ""}
                  onChange={(e) => onChangeFechaInicio(e.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="endDate">Fecha fin</label>
                <input
                  id="endDate"
                  name="endDate"
                  type="date"
                  min={MIN_DATE}
                  max={MAX_DATE}
                  value={consultaActiva?.fechaFin ?? ""}
                  onChange={(e) => onChangeFechaFin(e.target.value)}
                />
              </div>
            </>
          )}

          {tipoPeriodo === "rango_anios" && (
            <>
              <div className="field">
                <label htmlFor="startYearInput">Año inicio</label>
                <select
                  id="startYearInput"
                  name="anioInicio"
                  className="selectInput"
                  value={consultaActiva?.anioInicio ?? ""}
                  onChange={(e) => onChangeAnioInicio(e.target.value)}
                >
                  <option value="">Selecciona ano inicio</option>
                  {YEAR_OPTIONS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="endYearInput">Año fin</label>
                <select
                  id="endYearInput"
                  name="anioFin"
                  className="selectInput"
                  value={consultaActiva?.anioFin ?? ""}
                  onChange={(e) => onChangeAnioFin(e.target.value)}
                >
                  <option value="">Selecciona ano fin</option>
                  {YEAR_OPTIONS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className="field">
            <label htmlFor="stateSelect">Estado</label>
            <select
              id="stateSelect"
              name="state"
              className="selectInput"
              value={selectedState}
              onChange={(e) => onChangeState(e.target.value)}
            >
              <option value="">{showMunicipality ? "Selecciona un estado" : "Todos los estados"}</option>
              {ESTADOS.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          {showMunicipality && (
            <div className="field">
              <label htmlFor="municipalitySelect">Municipio</label>
              <select
                id="municipalitySelect"
                name="municipality"
                className="selectInput"
                value={selectedMunicipality}
                onChange={(e) => onChangeMunicipio(e.target.value)}
                disabled={!municipalityEnabled}
              >
                {!selectedState ? (
                  <option value="">Selecciona un estado primero</option>
                ) : (
                  <option value="">Todos los municipios</option>
                )}
                {municipios.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            className="primaryBtn"
            onClick={() => onConsultar?.()}
            disabled={showMunicipality && !selectedState}
          >
            Consultar
          </button>
          <button
            type="button"
            className="ghostBtn"
            disabled={!consultaEjecutada && !isDirty}
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
                        id={`layer-${layer.id}`}
                        name={`layer-${layer.id}`}
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
                            id={`smn-scope-${option.value}`}
                            name="smn-scope"
                            type="radio"
                            value={option.value}
                            aria-label={option.label}
                            checked={(consultaActiva?.filtrosSmn?.alcance ?? "todas") === option.value}
                            disabled={!consultaActiva?.capasActivas?.estacionesSmn}
                            onChange={(e) =>
                              onConsultaChange?.("filtrosSmn", {
                                alcance: e.target.value,
                              })
                            }
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
                          id={`smn-filter-${filter.id}`}
                          name={`smn-filter-${filter.id}`}
                          type="checkbox"
                          aria-label={filter.label}
                          checked={consultaActiva?.filtrosSmn?.[filter.id] ?? false}
                          disabled={!consultaActiva?.capasActivas?.estacionesSmn}
                          onChange={(e) =>
                            onConsultaChange?.("filtrosSmn", {
                              [filter.id]: e.target.checked,
                            })
                          }
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
