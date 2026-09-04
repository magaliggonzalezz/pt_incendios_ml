import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Download, FileText, ImageDown, LayoutDashboard } from "lucide-react";
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";
import "./RealResultsModal.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const TABS = [
  { key: "summary", label: "Resumen", icon: LayoutDashboard },
  { key: "charts", label: "Gráficas", icon: BarChart3 },
  { key: "data", label: "Datos", icon: FileText },
];
const SINGLE_GRAPH_OPTIONS = [
  { key: "activity", label: "Actividad" },
  { key: "sources", label: "Fuentes" },
  { key: "climate", label: "Clima" },
];
const MULTI_GRAPH_OPTIONS = [
  { key: "clusters", label: "Clusters" },
  { key: "firms", label: "Top FIRMS" },
  { key: "conafor", label: "Top CONAFOR" },
  { key: "hectares", label: "Top hectáreas" },
];
const TEMPORAL_GRAPH_OPTIONS = [
  { key: "compareActivity", label: "Observaciones" },
  { key: "compareFirms", label: "FIRMS" },
  { key: "compareConafor", label: "CONAFOR" },
  { key: "compareHectares", label: "Hectáreas" },
];

const PAGE_SIZE = 50;
const formatNumber = (value, digits = 0) => Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });
const territoryName = (row) => row.nombre_municipio || row.nombre_entidad || row.cvegeo || row.cve_ent || "N/D";
const sum = (rows, field) => rows.reduce((total, row) => total + Number(row?.[field] || 0), 0);
const average = (rows, field) => {
  const values = rows.map((row) => Number(row?.[field])).filter(Number.isFinite);
  if (!values.length) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
};

const horizontalOptions = (xTitle = "") => ({
  indexAxis: "y",
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: {
    x: { beginAtZero: true, title: { display: Boolean(xTitle), text: xTitle } },
    y: { grid: { display: false } },
  },
});

function safeFilePart(value) {
  return String(value || "grafica").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase();
}

export default function RealResultsModal({ open, onClose, resumenConsulta = null, onOpenExport }) {
  const [tab, setTab] = useState("summary");
  const [graphView, setGraphView] = useState("activity");
  const [page, setPage] = useState(1);
  const chartRef = useRef(null);
  const rows = resumenConsulta?.rows ?? [];
  const summaryRows = resumenConsulta?.summaryRows ?? [];
  const temporalRows = resumenConsulta?.temporalRows ?? [];
  const isTemporalComparison = temporalRows.length > 1;
  const isDateRange = resumenConsulta?.tipoPeriodo === "rango_fechas";
  const isSingleTerritory = isDateRange || (!isTemporalComparison && rows.length <= 1);
  const graphOptions = isTemporalComparison ? TEMPORAL_GRAPH_OPTIONS : (isSingleTerritory ? SINGLE_GRAPH_OPTIONS : MULTI_GRAPH_OPTIONS);
  const activeGraph = graphOptions.some((option) => option.key === graphView) ? graphView : graphOptions[0]?.key;
  const chartModel = useMemo(() => buildChartModel({ activeGraph, rows, summaryRows, temporalRows, isDateRange }), [activeGraph, rows, summaryRows, temporalRows, isDateRange]);
  const ml = resumenConsulta?.resultadoMl ?? {};
  const shouldPaginate = rows.length > 100;
  const totalPages = shouldPaginate ? Math.max(1, Math.ceil(rows.length / PAGE_SIZE)) : 1;
  const visibleRows = shouldPaginate ? rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : rows;
  const showDateColumn = rows.some((row) => Boolean(row.fecha));

  useEffect(() => { setPage(1); }, [resumenConsulta?.periodo, rows.length]);
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [page, totalPages]);

  const downloadChart = () => {
    const chart = chartRef.current;
    if (!chart) return;
    const anchor = document.createElement("a");
    anchor.href = chart.toBase64Image("image/png", 1);
    anchor.download = `grafica_ml_${safeFilePart(resumenConsulta?.territorio)}_${safeFilePart(resumenConsulta?.periodo)}_${safeFilePart(activeGraph)}.png`;
    anchor.click();
  };

  const footer = onOpenExport ? (
    <button type="button" className="cmClearBtn" onClick={onOpenExport} title="Descargar los datos de la consulta ejecutada">
      <Download size={15} /> Exportar datos de la consulta
    </button>
  ) : null;

  return (
    <ModalShell open={open} onClose={onClose} title="Resultados ML" width={1040} footer={footer} allowOverlayClose className="cmResultsDialog">
      <div className="cmTabs" role="tablist" aria-label="Resultados ML">
        {TABS.map((item) => {
          const Icon = item.icon;
          return <button key={item.key} type="button" className={`cmTab ${tab === item.key ? "isActive" : ""}`} onClick={() => setTab(item.key)} role="tab" aria-selected={tab === item.key}><Icon size={16} />{item.label}</button>;
        })}
      </div>

      {tab === "summary" ? (
        <div className="cmPanel">
          <div className="cmSummaryGrid">
            <SummaryItem label="Territorio" value={resumenConsulta?.territorio} />
            <SummaryItem label="Período" value={resumenConsulta?.periodo} />
            <SummaryItem label="Nivel de análisis" value={resumenConsulta?.nivelAgregacion === "municipio" ? "Municipal" : "Estatal"} />
            <SummaryItem label="Observaciones evaluadas" value={formatNumber(resumenConsulta?.observaciones)} />
            <SummaryItem label="Detecciones FIRMS" value={formatNumber(resumenConsulta?.firms_detecciones)} />
            <SummaryItem label="Eventos CONAFOR" value={formatNumber(resumenConsulta?.conafor_eventos)} />
            <SummaryItem label="Hectáreas CONAFOR" value={formatNumber(resumenConsulta?.conafor_ha, 2)} />
            <SummaryItem label="Días con incendio" value={formatNumber(resumenConsulta?.dias_incendio)} />
            <SummaryItem label="Días con patrón extremo" value={formatNumber(resumenConsulta?.dias_extremo)} />
          </div>
          {isTemporalComparison ? (
            <div className="cmDominant">
              <div className="cmPanelTitle">Comparación temporal</div>
              <p>La consulta compara {temporalRows.map((row) => row.label).join(" vs ")}. Usa la pestaña “Gráficas” para contrastar observaciones, FIRMS, CONAFOR y hectáreas entre ambos años.</p>
            </div>
          ) : (
            <div className="cmDominant" style={ml.color_sugerido_app ? { borderLeftColor: ml.color_sugerido_app } : undefined}>
              <div className="cmPanelTitle">Patrón ML dominante</div>
              <strong>{ml.estado_app || "Sin clasificación disponible"}</strong>
              <p>{ml.etiqueta_final || "Sin etiqueta disponible"}</p>
            </div>
          )}
        </div>
      ) : null}

      {tab === "charts" ? (
        <div className="cmChartsStack">
          <div className="cmChartsHeader">
            <div>
              <div className="cmPanelTitle">{isTemporalComparison ? "Comparación entre años" : (isDateRange ? "Resumen del rango" : (isSingleTerritory ? "Perfil del territorio" : "Comparación territorial"))}</div>
              <p className="cmChartCaption">
                {isTemporalComparison ? `Contraste temporal para ${resumenConsulta?.territorio || "el territorio seleccionado"}.` : (isDateRange ? `Agregado de los registros diarios entre ${resumenConsulta?.periodo || "las fechas seleccionadas"}.` : (isSingleTerritory ? "Las gráficas cambian de métrica porque la consulta contiene un solo territorio agregado." : `Comparación de ${rows.length} territorios devueltos por la consulta.`))}
              </p>
            </div>
            <div className="cmChartsTools">
              <div className="cmInnerSelector cmGraphSelector" role="tablist" aria-label="Tipo de gráfica">
                {graphOptions.map((option) => <button key={option.key} type="button" className={activeGraph === option.key ? "isActive" : ""} onClick={() => setGraphView(option.key)}>{option.label}</button>)}
              </div>
              <button type="button" className="cmImageBtn" onClick={downloadChart} disabled={!chartModel} title="Descargar gráfica actual como PNG"><ImageDown size={16} /> PNG</button>
            </div>
          </div>
          {chartModel ? <div className="cmChartCard"><div className="cmChartTitle">{chartModel.title}</div><p className="cmChartCaption">{chartModel.caption}</p><div className="cmChartCanvas"><Bar ref={chartRef} data={chartModel.data} options={horizontalOptions(chartModel.xTitle)} /></div></div> : <div className="cmChartEmpty">No hay datos suficientes para mostrar esta gráfica.</div>}
        </div>
      ) : null}

      {tab === "data" ? (
        <div className="cmDataPanel">
          <div>
            <div className="cmPanelTitle">Datos de la consulta</div>
            <p className="cmDataSubtitle">{shouldPaginate ? `Mostrando ${PAGE_SIZE} filas por página de ${formatNumber(rows.length)} registros.` : `Mostrando ${formatNumber(rows.length)} registros en una vista con desplazamiento.`}</p>
          </div>
          <div className="cmTableWrap isPreview"><table className="cmTable"><thead><tr>{isTemporalComparison ? <th>Año</th> : null}{showDateColumn ? <th>Fecha</th> : null}<th>Territorio</th><th>Clave</th><th>Cluster</th><th>Observaciones</th><th>FIRMS</th><th>CONAFOR</th><th>Hectáreas</th></tr></thead><tbody>
            {visibleRows.map((row, index) => <tr key={`${row.cvegeo || row.cve_ent}-${row.fecha || row.anio_comparacion || row.anio}-${row.mes || "periodo"}-${index}`}>{isTemporalComparison ? <td>{row.anio_comparacion}</td> : null}{showDateColumn ? <td>{row.fecha || ""}</td> : null}<td>{territoryName(row)}</td><td>{row.cvegeo || row.cve_ent}</td><td>{row.cluster}</td><td>{formatNumber(row.observaciones ?? 1)}</td><td>{formatNumber(row.firms_detecciones)}</td><td>{formatNumber(row.conafor_eventos)}</td><td>{formatNumber(row.conafor_ha, 2)}</td></tr>)}
            {!rows.length ? <tr><td colSpan={(isTemporalComparison ? 1 : 0) + (showDateColumn ? 1 : 0) + 7}>No hay filas disponibles para esta consulta.</td></tr> : null}
          </tbody></table></div>
          {shouldPaginate ? <div className="cmPagination"><button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>Anterior</button><span>Página {page} de {totalPages}</span><button type="button" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={page >= totalPages}>Siguiente</button></div> : null}
        </div>
      ) : null}
    </ModalShell>
  );
}

function buildChartModel({ activeGraph, rows, summaryRows, temporalRows, isDateRange }) {
  if (temporalRows.length > 1 && activeGraph?.startsWith("compare")) {
    const metric = {
      compareActivity: { field: "observaciones", title: "Observaciones por año", xTitle: "Observaciones", color: "#0F766E" },
      compareFirms: { field: "firms_detection_count_total", title: "Detecciones FIRMS por año", xTitle: "Detecciones FIRMS", color: "#F97316" },
      compareConafor: { field: "conafor_event_count_total", title: "Incendios CONAFOR por año", xTitle: "Eventos CONAFOR", color: "#DC2626" },
      compareHectares: { field: "conafor_total_hectareas_total", title: "Hectáreas CONAFOR por año", xTitle: "Hectáreas", color: "#B45309" },
    }[activeGraph];
    return {
      title: metric.title,
      caption: "Comparación directa de los dos años seleccionados para el mismo alcance territorial.",
      xTitle: metric.xTitle,
      data: { labels: temporalRows.map((row) => row.label), datasets: [{ label: metric.xTitle, data: temporalRows.map((row) => Number(row[metric.field] || 0)), backgroundColor: metric.color, borderRadius: 5 }] },
    };
  }

  if (!rows.length) return null;
  if (rows.length === 1 || isDateRange) {
    const row = rows[0] || {};
    if (activeGraph === "sources") return { title: "Fuentes de detección y registro", caption: isDateRange ? "Conteos acumulados FIRMS y CONAFOR para el rango consultado." : "Conteos FIRMS y CONAFOR para el período consultado.", xTitle: "Conteo", data: { labels: ["Detecciones FIRMS", "Eventos CONAFOR"], datasets: [{ label: "Conteo", data: [isDateRange ? sum(rows, "firms_detecciones") : Number(row.firms_detecciones || 0), isDateRange ? sum(rows, "conafor_eventos") : Number(row.conafor_eventos || 0)], backgroundColor: ["#F97316", "#DC2626"], borderRadius: 5 }] } };
    if (activeGraph === "climate") return { title: "Condiciones climáticas promedio", caption: isDateRange ? "Promedios calculados a partir de los registros diarios del rango." : "Temperatura mínima, máxima y precipitación promedio.", xTitle: "Valor", data: { labels: ["Temperatura mínima (°C)", "Temperatura máxima (°C)", "Precipitación (mm)"], datasets: [{ label: "Promedio", data: [isDateRange ? average(rows, "temp_min_c") : Number(row.temp_min_c || 0), isDateRange ? average(rows, "temp_max_c") : Number(row.temp_max_c || 0), isDateRange ? average(rows, "precip_mm") : Number(row.precip_mm || 0)], backgroundColor: ["#0EA5E9", "#F97316", "#14B8A6"], borderRadius: 5 }] } };
    return { title: "Actividad observada durante el período", caption: isDateRange ? "Días con señales de incendio y cobertura de las fuentes dentro del rango." : "Días con señales de incendio y cobertura de las fuentes disponibles.", xTitle: "Días", data: { labels: ["Incendio activo", "Patrón extremo", "Con CONAFOR", "Con FIRMS", "Con SMN"], datasets: [{ label: "Días", data: [isDateRange ? sum(rows, "dias_incendio") : Number(row.dias_incendio || 0), isDateRange ? sum(rows, "dias_extremo") : Number(row.dias_extremo || 0), isDateRange ? rows.filter((item) => Number(item.conafor_eventos || 0) > 0).length : Number(row.dias_conafor || 0), isDateRange ? rows.filter((item) => Number(item.firms_detecciones || 0) > 0).length : Number(row.dias_firms || 0), isDateRange ? rows.filter((item) => Number(item.smn_obs || 0) > 0).length : Number(row.dias_smn || 0)], backgroundColor: ["#DC2626", "#7C3AED", "#B91C1C", "#F97316", "#0F766E"], borderRadius: 5 }] } };
  }

  if (activeGraph === "clusters") return { title: "Distribución de observaciones por cluster", caption: "Observaciones acumuladas agrupadas por patrón ML.", xTitle: "Observaciones", data: { labels: summaryRows.map((row) => row.estado_app || `Cluster ${row.cluster_id}`), datasets: [{ label: "Observaciones", data: summaryRows.map((row) => Number(row.n_observaciones || 0)), backgroundColor: summaryRows.map((row) => row.color_sugerido_app || "#0F766E"), borderRadius: 5 }] } };

  const metric = {
    firms: { field: "firms_detecciones", title: "Top territorios por detecciones FIRMS", xTitle: "Detecciones FIRMS", color: "#F97316" },
    conafor: { field: "conafor_eventos", title: "Top territorios por eventos CONAFOR", xTitle: "Eventos CONAFOR", color: "#DC2626" },
    hectares: { field: "conafor_ha", title: "Top territorios por hectáreas CONAFOR", xTitle: "Hectáreas", color: "#B45309" },
  }[activeGraph];
  if (!metric) return null;
  const topRows = [...rows].sort((a, b) => Number(b[metric.field] || 0) - Number(a[metric.field] || 0)).slice(0, 12);
  return { title: metric.title, caption: "Comparación territorial para la consulta activa.", xTitle: metric.xTitle, data: { labels: topRows.map(territoryName), datasets: [{ label: metric.xTitle, data: topRows.map((row) => Number(row[metric.field] || 0)), backgroundColor: metric.color, borderRadius: 5 }] } };
}

function SummaryItem({ label, value }) {
  return <div className="cmSummaryItem"><span>{label}</span><strong>{value === 0 || value ? value : "N/D"}</strong></div>;
}
