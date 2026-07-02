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
import { getNivelUiLabel } from "../../data/dashboardMock";

const fallbackResumen = {
  periodo: "",
  nivelAgregacion: "",
  observaciones: 0,
};

const formatNumber = (value) => Number(value || 0).toLocaleString("es-MX");

const pickMlSource = (resumen) => {
  if (!resumen) return {};

  return (
    resumen.resultadoMl ||
    resumen.resultadoML ||
    resumen.resultado_ml ||
    resumen.resultadoModelo ||
    resumen.resultadoConsulta ||
    resumen.selectedFeature?.properties ||
    resumen
  );
};

const normalizeMlResult = (resumen) => {
  const result = pickMlSource(resumen);

  return {
    estado_app: result.estado_app || "Sin clasificaci\u00f3n disponible",
    etiqueta_final: result.etiqueta_final || "Sin etiqueta disponible",
    descripcion_app: result.descripcion_app || "Sin descripci\u00f3n disponible",
    explicacion_app: result.explicacion_app || "",
    color_sugerido_app: result.color_sugerido_app || null,
  };
};

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
  const territorio = resumenConsulta?.territorio || consultaActiva?.municipio || consultaActiva?.estado || "M\u00e9xico";
  const mlResult = normalizeMlResult(resumenConsulta);

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
          {open ? "\u27e9" : "\u27e8"}
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
                      <span>Per&iacute;odo</span>
                      <strong>{resumen.periodo || "Sin per\u00edodo"}</strong>
                    </div>
                  </div>

                  <div className="metaBox">
                    <span className="metaIcon metaIconLevel" aria-hidden="true">
                      <Layers3 size={15} />
                    </span>
                    <div>
                      <span>Nivel de an&aacute;lisis</span>
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

                <div
                  className={`mlBox ${mlResult.color_sugerido_app ? "hasMlColor" : ""}`}
                  style={mlResult.color_sugerido_app ? { borderLeftColor: mlResult.color_sugerido_app } : undefined}
                >
                  <div className="mlTitle">Resultado ML</div>
                  <div className="mlField">
                    <span>Patr&oacute;n seleccionado</span>
                    <strong>{mlResult.estado_app}</strong>
                  </div>
                  <div className="mlField">
                    <span>Nombre del patr&oacute;n</span>
                    <strong>{mlResult.etiqueta_final}</strong>
                  </div>
                  <p className="mlDescription">{mlResult.descripcion_app}</p>
                  {mlResult.explicacion_app ? (
                    <details className="mlDetail">
                      <summary>Ver detalle</summary>
                      <p>{mlResult.explicacion_app}</p>
                    </details>
                  ) : null}
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
