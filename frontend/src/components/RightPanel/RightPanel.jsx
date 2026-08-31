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

function formatCoverage(coverage) {
  if (!coverage?.from && !coverage?.to) return null;
  if (coverage.from && coverage.to) return `${coverage.from} → ${coverage.to}`;
  return coverage.from || coverage.to;
}

function activeLayerCards(consulta, layerSummary) {
  const active = consulta?.capasActivas || {};
  const cards = [];
  const summary = layerSummary || {};

  if (active.puntosCalorFirms) {
    const firms = summary.firms || {};
    const instrument = firms.satelliteInstrument?.value;
    cards.push({
      id: "firms",
      icon: Satellite,
      title: "FIRMS · área visible",
      value: `${formatNumber(firms.count)} detecciones`,
      details: [
        `${formatNumber(firms.day)} diurnas · ${formatNumber(firms.night)} nocturnas`,
        instrument ? `Satélite / instrumento predominante: ${instrument}` : null,
      ].filter(Boolean),
    });
  }

  if (active.incendiosConafor) {
    const conafor = summary.conafor || {};
    cards.push({
      id: "conafor",
      icon: Flame,
      title: "CONAFOR · área visible",
      value: `${formatNumber(conafor.count)} incendios`,
      details: [
        `${formatNumber(conafor.hectares, 2)} ha registradas`,
        conafor.vegetation?.value ? `Vegetación más frecuente: ${conafor.vegetation.value}` : null,
        conafor.cause?.value ? `Causa más frecuente: ${conafor.cause.value}` : null,
      ].filter(Boolean),
    });
  }

  if (active.estacionesSmn) {
    const smn = summary.smn || {};
    cards.push({
      id: "smn",
      icon: CloudSun,
      title: "SMN-CONAGUA",
      value: `${formatNumber(smn.count)} estaciones meteorológicas`,
      details: [
        `${formatNumber(smn.operando)} operando · ${formatNumber(smn.suspendida)} suspendidas`,
        formatCoverage(smn.coverage) ? `Cobertura disponible: ${formatCoverage(smn.coverage)}` : null,
        consulta?.filtrosSmn?.alcance === "periodo" ? "Conteo filtrado por el período seleccionado." : "Conteo según territorio y situación operativa seleccionados.",
      ].filter(Boolean),
    });
  }

  const inegi = summary.inegi || {};
  const inegiDetails = [];
  if (active.fisiografiaInegi) inegiDetails.push(`Provincias fisiográficas: ${formatNumber(inegi.fisiografia)} features visibles`);
  if (active.edafologiaInegi) inegiDetails.push(`Edafología: ${formatNumber(inegi.edafologia)} features visibles`);
  if (active.usoSueloVegetacionInegi) inegiDetails.push(`Uso de suelo y vegetación: ${formatNumber(inegi.usoSueloVegetacion)} features visibles`);
  if (active.corrientesAguaInegi) inegiDetails.push(`Corrientes de agua: ${formatNumber(inegi.hidrografia)} features visibles`);
  if (active.limitesEstatales) inegiDetails.push("Límites estatales activos");
  if (active.limitesMunicipales) inegiDetails.push("Límites municipales activos");
  if (inegiDetails.length) {
    cards.push({
      id: "inegi",
      icon: Map,
      title: "INEGI",
      value: "Capas geográficas activas",
      details: inegiDetails,
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
  layerSummary = null,
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
  const layerCards = useMemo(() => activeLayerCards(consultaActiva, layerSummary), [consultaActiva, layerSummary]);

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
              <div className="mapSummaryScope">Las métricas de FIRMS, CONAFOR e INEGI corresponden a los registros/features actualmente cargados en el área visible del mapa.</div>
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
                          {card.details.map((detail) => <small key={detail}>{detail}</small>)}
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
                <small>El detalle, las gráficas y los datos de la consulta se muestran en “Ver resultados”.</small>
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
