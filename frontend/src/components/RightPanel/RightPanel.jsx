import { useMemo, useState } from "react";
import "./RightPanel.css";
import {
  CalendarDays,
  Layers3,
  MapPin,
  BarChart3,
  Download,
  Flame,
  Satellite,
  CloudSun,
  Map,
} from "lucide-react";
import ExportModal from "../Modals/ExportModal";
import RealResultsModal from "../Modals/RealResultsModal";
import { getNivelUiLabel } from "../../data/dashboardMock";

const fallbackResumen = { periodo: "", nivelAgregacion: "", observaciones: 0 };
const formatNumber = (value, digits = 0) => Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });

function buildPeriodoLabel(consulta) {
  if (!consulta) return "Sin período";
  if (consulta.tipoPeriodo === "anio" && consulta.anio) return String(consulta.anio);
  if (consulta.tipoPeriodo === "anio_mes" && consulta.anio && consulta.mes) return `${consulta.anio}-${String(consulta.mes).padStart(2, "0")}`;
  if (consulta.tipoPeriodo === "comparar_anios" && consulta.anioInicio && consulta.anioFin) return `${consulta.anioInicio} vs ${consulta.anioFin}`;
  if (consulta.tipoPeriodo === "fecha" && consulta.fechaInicio) return consulta.fechaInicio;
  if (consulta.tipoPeriodo === "rango_fechas" && consulta.fechaInicio && consulta.fechaFin) return `${consulta.fechaInicio} a ${consulta.fechaFin}`;
  return "Sin período";
}

function buildTerritorioLabel(consulta, resumen) {
  const estado = consulta?.estado || resumen?.estado || "";
  const municipio = consulta?.municipio || resumen?.municipio || "";
  const nivel = consulta?.nivelAgregacion || resumen?.nivelAgregacion;
  if (nivel === "municipio" && municipio) return estado ? `${estado} · ${municipio}` : municipio;
  return estado || resumen?.territorio || "México";
}

function activeLayerCards(consulta, resumen, hasResults) {
  const active = consulta?.capasActivas || {};
  const cards = [];
  if (active.puntosCalorFirms) {
    cards.push({
      id: "firms",
      icon: Satellite,
      title: "FIRMS",
      value: hasResults ? `${formatNumber(resumen?.firms_detecciones)} detecciones` : "Capa activa",
      detail: hasResults ? `FRP acumulado: ${formatNumber(resumen?.firms_frp, 2)}` : "Detecciones originales del período y territorio visibles en el mapa.",
    });
  }
  if (active.incendiosConafor) {
    cards.push({
      id: "conafor",
      icon: Flame,
      title: "CONAFOR",
      value: hasResults ? `${formatNumber(resumen?.conafor_eventos)} incendios` : "Capa activa",
      detail: hasResults ? `${formatNumber(resumen?.conafor_ha, 2)} ha registradas` : "Registros originales de incendios disponibles para la selección.",
    });
  }
  if (active.estacionesSmn) {
    cards.push({
      id: "smn",
      icon: CloudSun,
      title: "SMN-CONAGUA",
      value: "Estaciones meteorológicas",
      detail: consulta?.filtrosSmn?.alcance === "periodo" ? "Filtradas por cobertura del período seleccionado." : "Inventario filtrado por territorio y situación operativa.",
    });
  }
  const thematicCount = [
    active.fisiografiaInegi,
    active.edafologiaInegi,
    active.usoSueloVegetacionInegi,
    active.corrientesAguaInegi,
    active.limitesEstatales,
    active.limitesMunicipales,
  ].filter(Boolean).length;
  if (thematicCount) {
    cards.push({
      id: "inegi",
      icon: Map,
      title: "INEGI",
      value: `${thematicCount} capa${thematicCount === 1 ? "" : "s"} activa${thematicCount === 1 ? "" : "s"}`,
      detail: "Límites y capas temáticas del marco geoestadístico visibles según la selección.",
    });
  }
  return cards;
}

export default function RightPanel({
  open,
  onToggle,
  consultaEjecutada = false,
  consultaActiva = null,
  consultaResultado = null,
  resumenConsulta = null,
  totalRecords = 0,
  availableFormats = ["csv", "json"],
  isExporting = false,
  isLoading = false,
  error = null,
  onPreviewExport,
  onDownloadExport,
  selectedMlCluster = null,
}) {
  const [openExport, setOpenExport] = useState(false);
  const [openCharts, setOpenCharts] = useState(false);
  const hasResults = Boolean(consultaEjecutada && resumenConsulta);
  const resumen = resumenConsulta ?? fallbackResumen;
  const territorio = buildTerritorioLabel(consultaActiva, resumenConsulta);
  const periodoActivo = buildPeriodoLabel(consultaActiva);
  const nivelActivo = getNivelUiLabel(consultaActiva?.nivelAgregacion);
  const layerCards = useMemo(() => activeLayerCards(consultaActiva, resumenConsulta, hasResults), [consultaActiva, resumenConsulta, hasResults]);

  return (
    <>
      <aside className={`rightPanel ${open ? "open" : "closed"}`} aria-label="Panel de resumen del mapa">
        <button className="toggleBtn" type="button" onClick={onToggle} aria-label={open ? "Ocultar panel de resumen" : "Mostrar panel de resumen"} aria-expanded={open}>
          {open ? "⟩" : "⟨"}
        </button>

        <div className="kpiCard">
          <div className="kpiHeader">
            <span className="kpiHeaderIcon" aria-hidden="true"><MapPin size={18} /></span>
            <span>{territorio}</span>
          </div>

          <div className="kpiBody">
            <div className="metaGrid">
              <div className="metaBox">
                <span className="metaIcon" aria-hidden="true"><CalendarDays size={16} /></span>
                <div><span>Período</span><strong>{hasResults ? (resumen.periodo || periodoActivo) : periodoActivo}</strong></div>
              </div>
              <div className="metaBox">
                <span className="metaIcon" aria-hidden="true"><Layers3 size={16} /></span>
                <div><span>Nivel de análisis</span><strong>{hasResults ? getNivelUiLabel(resumen.nivelAgregacion) : nivelActivo}</strong></div>
              </div>
            </div>

            <section className="mapSummarySection">
              <div className="mapSummaryTitle">Resumen de capas activas</div>
              {layerCards.length ? (
                <div className="layerSummaryList">
                  {layerCards.map((card) => {
                    const Icon = card.icon;
                    return (
                      <div className="layerSummaryCard" key={card.id}>
                        <span className="layerSummaryIcon" aria-hidden="true"><Icon size={16} /></span>
                        <div>
                          <span>{card.title}</span>
                          <strong>{card.value}</strong>
                          <small>{card.detail}</small>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : <div className="emptyState compact">Activa una o más capas para ver su resumen.</div>}
            </section>

            {isLoading ? <div className="emptyState">Consultando resultados...</div> : null}
            {error ? <div className="emptyState">No fue posible ejecutar la consulta: {error}</div> : null}
            {!isLoading && !error && hasResults ? (
              <div className="querySummaryBox">
                <span>Consulta ML disponible</span>
                <strong>{formatNumber(resumen.observaciones)} observaciones evaluadas</strong>
                <small>El detalle, gráficas y datos de la consulta se muestran en “Ver resultados”.</small>
              </div>
            ) : null}
            {!isLoading && !error && !hasResults ? (
              <div className="emptyState compact">Configura los filtros y ejecuta la consulta para habilitar el análisis ML y la exportación.</div>
            ) : null}
          </div>

          <div className="kpiActions">
            <button type="button" className="primaryBtn" onClick={() => setOpenCharts(true)} disabled={!hasResults || isLoading}>
              <BarChart3 size={18} /> Ver resultados
            </button>
            <button type="button" className="secondaryBtn" onClick={() => setOpenExport(true)} disabled={!hasResults || isLoading}>
              <Download size={18} /> Exportar datos
            </button>
          </div>
        </div>
      </aside>

      <ExportModal open={openExport} onClose={() => setOpenExport(false)} consultaActiva={consultaResultado} resumenConsulta={resumenConsulta} totalRecords={totalRecords} availableFormats={availableFormats} isExporting={isExporting} error={error} onPreviewExport={onPreviewExport} onDownloadExport={onDownloadExport} selectedMlCluster={selectedMlCluster} />
      <RealResultsModal open={openCharts} onClose={() => setOpenCharts(false)} resumenConsulta={resumenConsulta} />
    </>
  );
}
