import { useMemo } from "react";
import SearchableSelect from "../Common/SearchableSelect";
import { LAYER_GROUPS, INITIAL_ACTIVE_LAYERS, INITIAL_SMN_FILTERS } from "../../data/dashboardMock";
import "./LeftPanel.css";

const MESES = [
  { value: "01", label: "Enero" }, { value: "02", label: "Febrero" }, { value: "03", label: "Marzo" },
  { value: "04", label: "Abril" }, { value: "05", label: "Mayo" }, { value: "06", label: "Junio" },
  { value: "07", label: "Julio" }, { value: "08", label: "Agosto" }, { value: "09", label: "Septiembre" },
  { value: "10", label: "Octubre" }, { value: "11", label: "Noviembre" }, { value: "12", label: "Diciembre" },
];

const MIN_YEAR = 2001;
const MAX_YEAR = 2025;
const YEAR_OPTIONS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, index) => ({ value: String(MAX_YEAR - index), label: String(MAX_YEAR - index) }));

const PERIOD_OPTIONS = [
  { value: "", label: "Selecciona tipo de período" },
  { value: "anio", label: "Año" },
  { value: "anio_mes", label: "Año y mes" },
  { value: "comparar_anios", label: "Comparar años" },
  { value: "fecha", label: "Fecha" },
  { value: "rango_fechas", label: "Rango de fechas" },
];

const getLayerDisabled = (layer, nivelAgregacion) => Boolean(layer.nivel && layer.nivel !== nivelAgregacion);
const SMN_FILTERS = [{ id: "operando", label: "Operando" }, { id: "suspendida", label: "Suspendida" }];

function buildPeriodLabel(consulta) {
  if (consulta?.tipoPeriodo === "anio" && consulta.anio) return consulta.anio;
  if (consulta?.tipoPeriodo === "anio_mes" && consulta.anio && consulta.mes) return `${consulta.anio}-${consulta.mes}`;
  if (consulta?.tipoPeriodo === "comparar_anios" && consulta.anioInicio && consulta.anioFin) return `${consulta.anioInicio} vs ${consulta.anioFin}`;
  if (consulta?.tipoPeriodo === "fecha" && consulta.fechaInicio) return consulta.fechaInicio;
  if (consulta?.tipoPeriodo === "rango_fechas" && consulta.fechaInicio && consulta.fechaFin) return `${consulta.fechaInicio} a ${consulta.fechaFin}`;
  return "período seleccionado";
}

function consultaCompleta(consulta) {
  if (!consulta?.nivelAgregacion || !consulta?.tipoPeriodo) return false;
  if (consulta.nivelAgregacion === "municipio" && !consulta.cveEnt) return false;
  if (consulta.tipoPeriodo === "anio") return Boolean(consulta.anio);
  if (consulta.tipoPeriodo === "anio_mes") return Boolean(consulta.anio && consulta.mes);
  if (consulta.tipoPeriodo === "comparar_anios") return Boolean(consulta.anioInicio && consulta.anioFin && consulta.anioInicio !== consulta.anioFin);
  return false;
}

export default function LeftPanel({ open, onToggle, consultaActiva, consultaEjecutada = false, onConsultaChange, onConsultar, onResetConsulta, estados = [], municipios = [], isLoading = false }) {
  const selectedState = consultaActiva?.cveEnt || "";
  const selectedMunicipality = consultaActiva?.cvegeo || "";
  const showMunicipality = consultaActiva?.nivelAgregacion === "municipio";
  const municipalityEnabled = showMunicipality && selectedState !== "";
  const tipoPeriodo = consultaActiva?.tipoPeriodo || "";
  const canQuery = consultaCompleta(consultaActiva);
  const datePending = tipoPeriodo === "fecha" || tipoPeriodo === "rango_fechas";

  const stateOptions = useMemo(() => estados.map((state) => ({ value: state.cve_ent, label: state.nombre, meta: `Entidad ${state.cve_ent}` })), [estados]);
  const municipalityOptions = useMemo(() => municipios.map((municipality) => ({ value: municipality.cvegeo, label: municipality.nombre, meta: `CVEGEO ${municipality.cvegeo}` })), [municipios]);

  const isDirty = useMemo(() => {
    const currentLayers = consultaActiva?.capasActivas ?? {};
    const layersChanged = Object.entries(INITIAL_ACTIVE_LAYERS).some(([key, value]) => currentLayers[key] !== value);
    const currentSmnFilters = consultaActiva?.filtrosSmn ?? {};
    const smnFiltersChanged = Object.entries(INITIAL_SMN_FILTERS).some(([key, value]) => currentSmnFilters[key] !== value);
    const consultaChanged = ["nivelAgregacion", "tipoPeriodo", "anio", "mes", "anioInicio", "anioFin", "fechaInicio", "fechaFin", "estado", "municipio", "cveEnt", "cveMun", "cvegeo"].some((key) => Boolean(consultaActiva?.[key]));
    return layersChanged || smnFiltersChanged || consultaChanged;
  }, [consultaActiva]);

  const onChangeState = (cveEnt) => {
    const state = estados.find((item) => item.cve_ent === cveEnt);
    onConsultaChange?.("consultaPatch", { cveEnt, estado: state?.nombre || "", municipio: "", cveMun: "", cvegeo: "" });
  };

  const onChangeMunicipio = (cvegeo) => {
    const municipality = municipios.find((item) => item.cvegeo === cvegeo);
    onConsultaChange?.("consultaPatch", { cvegeo, cveMun: municipality?.cve_mun || "", municipio: municipality?.nombre || "" });
  };

  const periodScopeLabel = buildPeriodLabel(consultaActiva);

  return (
    <aside className={`leftPanel ${open ? "open" : "closed"}`} aria-label="Panel de filtros de consulta">
      <button className="toggleBtn" type="button" onClick={onToggle} aria-label={open ? "Ocultar panel de filtros" : "Mostrar panel de filtros"} aria-expanded={open}>{open ? "⟨" : "⟩"}</button>
      <div className="panelContent">
        <div className="panelCard">
          <div className="panelTitle">Consulta</div>
          <div className="field">
            <label htmlFor="aggregationLevel">Nivel de análisis</label>
            <select id="aggregationLevel" className="selectInput" value={consultaActiva?.nivelAgregacion ?? ""} onChange={(event) => onConsultaChange?.("nivelAgregacion", event.target.value)}>
              <option value="">Selecciona nivel de análisis</option><option value="entidad">Estatal</option><option value="municipio">Municipal</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="periodType">Tipo de período</label>
            <select id="periodType" className="selectInput" value={tipoPeriodo} onChange={(event) => onConsultaChange?.("consultaPatch", { tipoPeriodo: event.target.value, anio: "", mes: "", anioInicio: "", anioFin: "", fechaInicio: "", fechaFin: "" })}>
              {PERIOD_OPTIONS.map((option) => <option key={option.value || "empty"} value={option.value}>{option.label}</option>)}
            </select>
          </div>

          {(tipoPeriodo === "anio" || tipoPeriodo === "anio_mes") ? <SearchableSelect id="yearInput" label="Año" value={consultaActiva?.anio || ""} options={YEAR_OPTIONS} placeholder="Selecciona año" searchPlaceholder="Escribe un año..." maxVisible={7} onChange={(value) => onConsultaChange?.("anio", value)} /> : null}
          {tipoPeriodo === "anio_mes" ? <SearchableSelect id="monthSelect" label="Mes" value={consultaActiva?.mes || ""} options={MESES} placeholder="Selecciona mes" searchPlaceholder="Escribe un mes..." maxVisible={6} onChange={(value) => onConsultaChange?.("mes", value)} /> : null}
          {tipoPeriodo === "comparar_anios" ? (
            <div className="comparisonGrid">
              <SearchableSelect id="yearA" label="Año A" value={consultaActiva?.anioInicio || ""} options={YEAR_OPTIONS} placeholder="Selecciona año" searchPlaceholder="Buscar año..." maxVisible={6} onChange={(value) => onConsultaChange?.("anioInicio", value)} />
              <SearchableSelect id="yearB" label="Año B" value={consultaActiva?.anioFin || ""} options={YEAR_OPTIONS} placeholder="Selecciona año" searchPlaceholder="Buscar año..." maxVisible={6} onChange={(value) => onConsultaChange?.("anioFin", value)} />
            </div>
          ) : null}
          {datePending ? (
            <>
              <div className="dateGrid">
                <div className="field"><label htmlFor="dateStart">{tipoPeriodo === "fecha" ? "Fecha" : "Fecha inicial"}</label><input id="dateStart" type="date" value={consultaActiva?.fechaInicio || ""} onChange={(event) => onConsultaChange?.("fechaInicio", event.target.value)} /></div>
                {tipoPeriodo === "rango_fechas" ? <div className="field"><label htmlFor="dateEnd">Fecha final</label><input id="dateEnd" type="date" value={consultaActiva?.fechaFin || ""} min={consultaActiva?.fechaInicio || undefined} onChange={(event) => onConsultaChange?.("fechaFin", event.target.value)} /></div> : null}
              </div>
              <div className="helperText pendingNote">El selector de fecha ya está preparado. La ejecución diaria se habilitará al conectar las rutas día; municipio-día se mantiene para la etapa final.</div>
            </>
          ) : null}

          <SearchableSelect id="stateSelect" label="Estado" value={selectedState} options={stateOptions} placeholder={showMunicipality ? "Selecciona estado" : "Todos los estados"} searchPlaceholder="Buscar estado..." maxVisible={7} onChange={onChangeState} />
          {showMunicipality ? <SearchableSelect id="municipalitySelect" label="Municipio" value={selectedMunicipality} options={municipalityOptions} placeholder={selectedState ? "Todos los municipios" : "Selecciona estado primero"} searchPlaceholder="Buscar municipio..." disabled={!municipalityEnabled} maxVisible={7} onChange={onChangeMunicipio} /> : null}

          <button type="button" className="primaryBtn" onClick={() => onConsultar?.()} disabled={!canQuery || isLoading}>{isLoading ? "Consultando..." : "Consultar"}</button>
          <button type="button" className="ghostBtn" disabled={isLoading || (!consultaEjecutada && !isDirty)} onClick={onResetConsulta}>Limpiar filtros</button>
        </div>

        <div className="panelCard layersCard">
          <div className="panelTitle">Capas disponibles</div>
          <div className="layerGroups">
            {LAYER_GROUPS.map((group) => (
              <section className="layerGroup" key={group.id} aria-label={group.title}>
                <div className="layerGroupTitle">{group.title}</div>
                {group.layers.map((layer) => {
                  const disabled = getLayerDisabled(layer, consultaActiva?.nivelAgregacion);
                  return <label className={`row layerRow ${disabled ? "isDisabled" : ""}`} key={layer.id}><input type="checkbox" aria-label={layer.label} checked={consultaActiva?.capasActivas?.[layer.id] ?? false} disabled={disabled} onChange={(event) => onConsultaChange?.("capasActivas", { capa: layer.id, activo: event.target.checked })} /><span>{layer.label}{layer.helper ? <small>{layer.helper}</small> : null}</span></label>;
                })}
                {group.id === "smn" ? (
                  <div className={`smnFilters ${consultaActiva?.capasActivas?.estacionesSmn ? "" : "isDisabled"}`} aria-label="Filtros de estaciones meteorológicas SMN-CONAGUA">
                    <div className="smnFilterBlock" role="radiogroup" aria-label="Alcance de estaciones meteorológicas">
                      <div className="smnFiltersTitle">Alcance</div>
                      <label className="row smnFilterRow"><input name="smn-scope" type="radio" value="todas" checked={(consultaActiva?.filtrosSmn?.alcance ?? "todas") === "todas"} disabled={!consultaActiva?.capasActivas?.estacionesSmn} onChange={(event) => onConsultaChange?.("filtrosSmn", { alcance: event.target.value })} /><span>Todas las estaciones</span></label>
                      <label className="row smnFilterRow"><input name="smn-scope" type="radio" value="periodo" checked={consultaActiva?.filtrosSmn?.alcance === "periodo"} disabled={!consultaActiva?.capasActivas?.estacionesSmn} onChange={(event) => onConsultaChange?.("filtrosSmn", { alcance: event.target.value })} /><span>Con datos del período seleccionado <small>{periodScopeLabel}</small></span></label>
                    </div>
                    <div className="smnFilterBlock" aria-label="Situación operativa de estaciones meteorológicas">
                      <div className="smnFiltersTitle">Situación operativa</div>
                      {SMN_FILTERS.map((filter) => <label className="row smnFilterRow" key={filter.id}><input type="checkbox" checked={consultaActiva?.filtrosSmn?.[filter.id] ?? false} disabled={!consultaActiva?.capasActivas?.estacionesSmn} onChange={(event) => onConsultaChange?.("filtrosSmn", { [filter.id]: event.target.checked })} /><span>{filter.label}</span></label>)}
                    </div>
                  </div>
                ) : null}
              </section>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
