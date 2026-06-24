import { useState } from "react";
import "./RightPanel.css";
import {
  Activity,
  CalendarDays,
  Layers3,
  MapPin,
  BarChart3,
  Download,
} from "lucide-react";
import ExportModal from "../Modals/ExportModal";
import ChartsModal from "../Modals/ChartsModal";
import { PENDING_INTERPRETATION, getNivelUiLabel } from "../../data/dashboardMock";

const fallbackResumen = {
  territorio: "México",
  periodo: "",
  nivelAgregacion: "",
  nivelAnalisisMl: "",
  observaciones: 0,
  firmsTotal: 0,
  diasConFirms: 0,
  diasConConafor: 0,
  diasConSmn: 0,
  clusterAsignado: "",
  clusterName: "",
  patronIdentificado: "",
  modelo: "SOM + K-Means",
  activeVisualContext: [],
};

const formatNumber = (value) => Number(value || 0).toLocaleString("es-MX");

export default function RightPanel({
  open,
  onToggle,
  consultaEjecutada = false,
  consultaActiva = null,
  resumenConsulta = null,
  totalRecords = 0,
  availableFormats = ["csv", "json"],
  isExporting = false,
  error = null,
  onPreviewExport,
  onDownloadExport,
  selectedMlCluster = null,
  onSelectedMlClusterChange,
}) {
  const [openExport, setOpenExport] = useState(false);
  const [openCharts, setOpenCharts] = useState(false);
  const hasResults = Boolean(consultaEjecutada && resumenConsulta);
  const resumen = resumenConsulta ?? fallbackResumen;
  const territorio = resumenConsulta?.territorio || consultaActiva?.municipio || consultaActiva?.estado || "México";
  const interpretation = resumen.descripcionCorta || resumen.interpretacionTecnica || resumen.patronIdentificado || PENDING_INTERPRETATION;
  const activeVisualContext = resumen.activeVisualContext ?? [];

  return (
    <>
      <aside className={`rightPanel ${open ? "open" : "closed"}`} aria-label="Panel de resultados de consulta">
        <button
          className="toggleBtn"
          type="button"
          onClick={onToggle}
          aria-label={open ? "Ocultar panel de resultados" : "Mostrar panel de resultados"}
          aria-expanded={open}
        >
          {open ? "⟩" : "⟨"}
        </button>

        <div className="kpiCard">
          <div className="kpiHeader">
            <span className="kpiHeaderIcon" aria-hidden="true">
              <MapPin size={18} />
            </span>
            <span>{territorio}</span>
          </div>

          <div className="kpiBody">
            {!hasResults ? (
              <div className="emptyState">
                Selecciona filtros y ejecuta una consulta para visualizar resultados.
              </div>
            ) : (
              <>
                <div className="metaGrid">
                  <div className="metaBox">
                    <span className="metaIcon metaIconPeriod" aria-hidden="true">
                      <CalendarDays size={15} />
                    </span>
                    <div>
                      <span>Período</span>
                      <strong>{resumen.periodo || "Sin período"}</strong>
                    </div>
                  </div>

                  <div className="metaBox">
                    <span className="metaIcon metaIconLevel" aria-hidden="true">
                      <Layers3 size={15} />
                    </span>
                    <div>
                      <span>Nivel de análisis</span>
                      <strong>{getNivelUiLabel(resumen.nivelAgregacion)}</strong>
                    </div>
                  </div>
                </div>

                <div className="kpiBox">
                  <div className="kpiTopRow">
                    <span className="kpiIcon" aria-hidden="true">
                      <Activity size={16} />
                    </span>
                    <div className="kpiLabel">Observaciones evaluadas</div>
                  </div>
                  <div className="kpiValue">{formatNumber(resumen.observaciones)}</div>
                </div>

                <div className="kpiBox">
                  <div className="kpiTopRow">
                    <span className="kpiIcon" aria-hidden="true">
                      <Activity size={16} />
                    </span>
                    <div className="kpiLabel">Hotspots acumulados</div>
                  </div>
                  <div className="kpiValue">{formatNumber(resumen.firmsTotal)}</div>
                </div>

                <div className="kpiBox">
                  <div className="kpiTopRow">
                    <span className="kpiIcon" aria-hidden="true">
                      <Activity size={16} />
                    </span>
                    <div className="kpiLabel">Días con cobertura meteorológica</div>
                  </div>
                  <div className="kpiValue">{formatNumber(resumen.diasConSmn)}</div>
                </div>

                <div className="miniGrid">
                  <div className="miniMetric">
                    <span>Días con hotspots</span>
                    <strong>{formatNumber(resumen.diasConFirms)}</strong>
                  </div>
                  <div className="miniMetric">
                    <span>Días con registro histórico</span>
                    <strong>{formatNumber(resumen.diasConConafor)}</strong>
                  </div>
                  <div className="miniMetric">
                    <span>Patrón</span>
                    <strong>{resumen.clusterAsignado || "Sin datos"}</strong>
                  </div>
                </div>

                <div className="mlBox">
                  <div className="mlTitle">Resultado ML</div>
                  <div className="mlCluster">
                    <span>Modelo</span>
                    <strong>{resumen.modelo}</strong>
                  </div>
                  <div className="mlCluster">
                    <span>Nivel</span>
                    <strong>{resumen.nivelAnalisisMl}</strong>
                  </div>
                  <div className="mlCluster">
                    <span>Patrón seleccionado</span>
                    <strong>{resumen.clusterAsignado || "Sin datos"}</strong>
                  </div>
                  <div className="mlCluster">
                    <span>Nombre del patrón</span>
                    <strong>{resumen.clusterName || "Sin datos"}</strong>
                  </div>
                  <p>{interpretation}</p>
                </div>

                <div className="visualContextBox">
                  <div className="visualContextTitle">Contexto visual activo</div>
                  {activeVisualContext.length === 0 ? (
                    <p className="visualContextEmpty">No hay capas visibles adicionales para esta consulta.</p>
                  ) : (
                    <ul className="visualContextList">
                      {activeVisualContext.slice(0, 5).map((layer) => (
                        <li key={layer.id}>
                          <strong>{layer.label}</strong>
                          <span>{getTemporalLabel(layer.temporal)} · {layer.mapType}</span>
                          {layer.detail && <em>{layer.detail}</em>}
                        </li>
                      ))}
                    </ul>
                  )}
                  {activeVisualContext.length > 5 && (
                    <p className="visualContextMore">+{activeVisualContext.length - 5} capas visibles más</p>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="kpiActions">
            <button type="button" className="primaryBtn" onClick={() => setOpenCharts(true)} disabled={!hasResults}>
              <BarChart3 size={18} />
              Ver resultados
            </button>
            <button type="button" className="secondaryBtn" onClick={() => setOpenExport(true)} disabled={!hasResults}>
              <Download size={18} />
              Exportar datos
            </button>
          </div>
        </div>
      </aside>

      <ExportModal
        open={openExport}
        onClose={() => setOpenExport(false)}
        consultaActiva={consultaActiva}
        resumenConsulta={resumenConsulta}
        totalRecords={totalRecords}
        availableFormats={availableFormats}
        isExporting={isExporting}
        error={error}
        onPreviewExport={onPreviewExport}
        onDownloadExport={onDownloadExport}
        selectedMlCluster={selectedMlCluster}
      />

      <ChartsModal
        open={openCharts}
        onClose={() => setOpenCharts(false)}
        consultaActiva={consultaActiva}
        resumenConsulta={resumenConsulta}
        selectedMlCluster={selectedMlCluster}
        onSelectedMlClusterChange={onSelectedMlClusterChange}
        onDownloadExport={onDownloadExport}
      />
    </>
  );
}

function getTemporalLabel(temporal) {
  if (temporal === true) return "Filtrada por consulta";
  if (temporal === false) return "No temporal";
  return "Depende del alcance";
}
