import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Download, FileText, ImageDown, LayoutDashboard } from "lucide-react";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";
import "./RealResultsModal.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend);

const TABS = [
  { key: "summary", label: "Resumen", icon: LayoutDashboard },
  { key: "charts", label: "Gráficas", icon: BarChart3 },
  { key: "data", label: "Datos", icon: FileText },
];

const SNAPSHOT_GRAPH_OPTIONS = [
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
  { key: "trendFirms", label: "FIRMS" },
  { key: "trendConafor", label: "CONAFOR" },
  { key: "trendHectares", label: "Hectáreas" },
  { key: "trendTemperature", label: "Temperatura" },
  { key: "trendRain", label: "Precipitación" },
];

const LAYERS_GRAPH_OPTION = { key: "layers", label: "Capas activas" };
const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const SERIES_COLORS = ["#0F766E", "#7C3AED", "#2563EB", "#D97706"];
const PAGE_SIZE = 50;

const formatNumber = (value, digits = 0) => Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });
const territoryName = (row) => row.nombre_municipio || row.nombre_entidad || row.cvegeo || row.cve_ent || "N/D";

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

const verticalOptions = (yTitle = "") => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: true,
      callbacks: {
        label: (context) => `${context.dataset.label}: ${Number(context.raw || 0).toLocaleString("es-MX")}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxRotation: 0, minRotation: 0 },
      title: { display: true, text: "Tipo de dato" },
    },
    y: { beginAtZero: true, title: { display: Boolean(yTitle), text: yTitle } },
  },
});

const lineOptions = (yTitle = "", beginAtZero = true) => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: "index", intersect: false },
  plugins: { legend: { display: true, position: "top" }, tooltip: { enabled: true } },
  scales: {
    x: { grid: { display: false }, title: { display: true, text: "Período" } },
    y: { beginAtZero, title: { display: Boolean(yTitle), text: yTitle } },
  },
});

function safeFilePart(value) {
  return String(value || "grafica").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase();
}

function withLineStyle(dataset, color) {
  return {
    ...dataset,
    borderColor: color,
    backgroundColor: color,
    pointBackgroundColor: color,
    pointBorderColor: "#FFFFFF",
    pointBorderWidth: 1,
    borderWidth: 2.5,
    tension: 0.28,
    pointRadius: 3,
    pointHoverRadius: 5,
    spanGaps: true,
    fill: false,
  };
}

function buildTemporalChartModel(activeGraph, rows, tipoPeriodo) {
  if (!rows.length) return null;
  const isComparison = tipoPeriodo === "comparar_anios";
  const seriesNames = [...new Set(rows.map((row) => row.series || "Periodo"))];
  const labels = isComparison
    ? [...new Set(rows.map((row) => row.periodKey.slice(5, 7)))].sort().map((month) => MONTHS[Number(month) - 1])
    : rows.filter((row) => (row.series || "Periodo") === seriesNames[0]).map((row) => row.label);

  const metricConfig = {
    trendFirms: { field: "firms_detecciones", title: "Evolución de detecciones FIRMS", yTitle: "Detecciones", beginAtZero: true, color: "#F97316" },
    trendConafor: { field: "conafor_eventos", title: "Evolución de eventos CONAFOR", yTitle: "Eventos", beginAtZero: true, color: "#DC2626" },
    trendHectares: { field: "conafor_ha", title: "Evolución de hectáreas CONAFOR", yTitle: "Hectáreas", beginAtZero: true, color: "#B45309" },
    trendRain: { field: "precip_mm", title: "Evolución de precipitación", yTitle: "Precipitación (mm)", beginAtZero: true, color: "#0891B2" },
  }[activeGraph];

  if (activeGraph === "trendTemperature") {
    const baseSeries = isComparison ? seriesNames : [seriesNames[0]];
    const datasets = [];
    baseSeries.forEach((series, seriesIndex) => {
      const serieRows = rows.filter((row) => (row.series || "Periodo") === series);
      const valueFor = (monthOrLabel, field) => {
        if (isComparison) {
          const month = String(MONTHS.indexOf(monthOrLabel) + 1).padStart(2, "0");
          return serieRows.find((row) => row.periodKey.slice(5, 7) === month)?.[field] ?? null;
        }
        return serieRows.find((row) => row.label === monthOrLabel)?.[field] ?? null;
      };
      const minColor = isComparison ? SERIES_COLORS[seriesIndex % SERIES_COLORS.length] : "#2563EB";
      const maxColor = isComparison ? SERIES_COLORS[(seriesIndex + 2) % SERIES_COLORS.length] : "#F97316";
      datasets.push(withLineStyle({
        label: `${seriesNames.length > 1 ? `${series} · ` : ""}Mínima`,
        data: labels.map((label) => valueFor(label, "temp_min_c")),
      }, minColor));
      datasets.push(withLineStyle({
        label: `${seriesNames.length > 1 ? `${series} · ` : ""}Máxima`,
        data: labels.map((label) => valueFor(label, "temp_max_c")),
      }, maxColor));
    });
    return {
      type: "line",
      title: "Evolución de temperatura",
      caption: isComparison ? "Temperaturas mínima y máxima comparadas por mes para ambos años." : "Temperaturas mínima y máxima a lo largo del período consultado.",
      yTitle: "Temperatura (°C)",
      beginAtZero: false,
      data: { labels, datasets },
    };
  }

  if (!metricConfig) return null;
  const datasets = seriesNames.map((series, index) => {
    const serieRows = rows.filter((row) => (row.series || "Periodo") === series);
    const data = labels.map((label) => {
      if (isComparison) {
        const month = String(MONTHS.indexOf(label) + 1).padStart(2, "0");
        return serieRows.find((row) => row.periodKey.slice(5, 7) === month)?.[metricConfig.field] ?? null;
      }
      return serieRows.find((row) => row.label === label)?.[metricConfig.field] ?? null;
    });
    const color = seriesNames.length > 1 ? SERIES_COLORS[index % SERIES_COLORS.length] : metricConfig.color;
    return withLineStyle({ label: seriesNames.length > 1 ? series : metricConfig.yTitle, data }, color);
  });

  return {
    type: "line",
    title: metricConfig.title,
    caption: isComparison ? "Comparación mensual de los dos años seleccionados." : "Serie temporal construida con la granularidad real disponible para la consulta.",
    yTitle: metricConfig.yTitle,
    beginAtZero: metricConfig.beginAtZero,
    data: { labels, datasets },
  };
}

function buildLayerChartModel(layerSummary, capasActivas = {}) {
  const labels = [];
  const values = [];
  const colors = [];
  const inegi = layerSummary?.inegi || {};

  const addLayer = (active, source, type, value, color) => {
    if (!active) return;
    labels.push([source, type]);
    values.push(Number(value || 0));
    colors.push(color);
  };

  addLayer(capasActivas.puntosCalorFirms, "FIRMS", "Anomalías térmicas", layerSummary?.firms?.count, "#F97316");
  addLayer(capasActivas.incendiosConafor, "CONAFOR", "Incendios", layerSummary?.conafor?.count, "#DC2626");
  addLayer(capasActivas.estacionesSmn, "SMN-CONAGUA", "Estaciones", layerSummary?.smn?.count, "#0F766E");
  addLayer(capasActivas.fisiografiaInegi, "INEGI", "Provincias fisiográficas", inegi.fisiografia, "#7C3AED");
  addLayer(capasActivas.edafologiaInegi, "INEGI", "Unidades edafológicas", inegi.edafologia, "#A16207");
  addLayer(capasActivas.usoSueloVegetacionInegi, "INEGI", "Uso de suelo y vegetación", inegi.usoSueloVegetacion, "#4D7C0F");
  addLayer(capasActivas.corrientesAguaInegi, "INEGI", "Corrientes de agua", inegi.hidrografia, "#0284C7");

  if (!labels.length) return null;
  return {
    type: "bar",
    orientation: "vertical",
    title: "Registros visibles por capa activa",
    caption: "Conteos del área visible del mapa, separados por fuente y tipo de dato.",
    yTitle: "Cantidad visible",
    data: {
      labels,
      datasets: [{ label: "Cantidad visible", data: values, backgroundColor: colors, borderRadius: 5 }],
    },
  };
}

function sliceChartModel(model, start, end) {
  if (!model || model.type !== "line") return model;
  const labels = model.data.labels || [];
  if (!labels.length) return model;
  const safeStart = Math.max(0, Math.min(start, labels.length - 1));
  const safeEnd = Math.max(safeStart, Math.min(end, labels.length - 1));
  return {
    ...model,
    data: {
      labels: labels.slice(safeStart, safeEnd + 1),
      datasets: model.data.datasets.map((dataset) => ({
        ...dataset,
        data: dataset.data.slice(safeStart, safeEnd + 1),
      })),
    },
  };
}

export default function RealResultsModal({ open, onClose, resumenConsulta = null, layerSummary = null, capasActivas = {}, onOpenExport }) {
  const [tab, setTab] = useState("summary");
  const [graphView, setGraphView] = useState("sources");
  const [page, setPage] = useState(1);
  const [focusStart, setFocusStart] = useState(0);
  const [focusEnd, setFocusEnd] = useState(0);
  const chartRef = useRef(null);

  const rows = resumenConsulta?.rows ?? [];
  const summaryRows = resumenConsulta?.summaryRows ?? [];
  const temporalRows = resumenConsulta?.temporalRows ?? [];
  const hasTemporalSeries = temporalRows.length > 1;
  const isSingleSnapshot = !hasTemporalSeries && rows.length <= 1;
  const layerChart = useMemo(() => buildLayerChartModel(layerSummary, capasActivas), [layerSummary, capasActivas]);
  const baseGraphOptions = hasTemporalSeries ? TEMPORAL_GRAPH_OPTIONS : (isSingleSnapshot ? SNAPSHOT_GRAPH_OPTIONS : MULTI_GRAPH_OPTIONS);
  const graphOptions = layerChart ? [...baseGraphOptions, LAYERS_GRAPH_OPTION] : baseGraphOptions;
  const activeGraph = graphOptions.some((option) => option.key === graphView) ? graphView : graphOptions[0]?.key;

  const fullChartModel = useMemo(() => {
    if (activeGraph === "layers") return layerChart;
    if (hasTemporalSeries) return buildTemporalChartModel(activeGraph, temporalRows, resumenConsulta?.tipoPeriodo);
    return buildBarChartModel({ activeGraph, rows, summaryRows });
  }, [activeGraph, layerChart, hasTemporalSeries, temporalRows, resumenConsulta?.tipoPeriodo, rows, summaryRows]);

  const temporalPointCount = fullChartModel?.type === "line" ? (fullChartModel.data.labels?.length || 0) : 0;
  const focusMax = Math.max(1, temporalPointCount - 1);
  const focusStartPercent = (focusStart / focusMax) * 100;
  const focusEndPercent = (focusEnd / focusMax) * 100;
  const chartModel = useMemo(
    () => sliceChartModel(fullChartModel, focusStart, focusEnd),
    [fullChartModel, focusStart, focusEnd]
  );

  const ml = resumenConsulta?.resultadoMl ?? {};
  const shouldPaginate = rows.length > 100;
  const totalPages = shouldPaginate ? Math.max(1, Math.ceil(rows.length / PAGE_SIZE)) : 1;
  const visibleRows = shouldPaginate ? rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : rows;
  const showDateColumn = rows.some((row) => Boolean(row.fecha));

  useEffect(() => { setPage(1); }, [resumenConsulta?.periodo, rows.length]);
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [page, totalPages]);
  useEffect(() => {
    const max = Math.max(0, temporalPointCount - 1);
    setFocusStart(0);
    setFocusEnd(max);
  }, [temporalPointCount, activeGraph, resumenConsulta?.periodo]);

  const downloadChart = () => {
    const chart = chartRef.current;
    if (!chart) return;
    const anchor = document.createElement("a");
    anchor.href = chart.toBase64Image("image/png", 1);
    anchor.download = `grafica_${safeFilePart(resumenConsulta?.territorio)}_${safeFilePart(resumenConsulta?.periodo)}_${safeFilePart(activeGraph)}.png`;
    anchor.click();
  };

  const footer = onOpenExport ? (
    <button type="button" className="cmClearBtn cmResultsExportBtn" onClick={onOpenExport} title="Descargar los datos de la consulta ejecutada">
      <Download size={15} /> Exportar datos de la consulta
    </button>
  ) : null;

  return (
    <ModalShell open={open} onClose={onClose} title="Resultados" width={1040} footer={footer} allowOverlayClose className="cmResultsDialog">
      <div className="cmTabs" role="tablist" aria-label="Resultados">
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
            {resumenConsulta?.dias_incendio !== null && resumenConsulta?.dias_incendio !== undefined ? <SummaryItem label="Días con incendio" value={formatNumber(resumenConsulta.dias_incendio)} /> : null}
            {resumenConsulta?.dias_extremo !== null && resumenConsulta?.dias_extremo !== undefined ? <SummaryItem label="Días con patrón extremo" value={formatNumber(resumenConsulta.dias_extremo)} /> : null}
          </div>
          <div className="cmDominant" style={ml.color_sugerido_app ? { borderLeftColor: ml.color_sugerido_app } : undefined}>
            <div className="cmPanelTitle">Patrón ML dominante</div>
            <strong>{ml.estado_app || "Sin clasificación disponible"}</strong>
            <p>{ml.etiqueta_final || "Sin etiqueta disponible"}</p>
          </div>
        </div>
      ) : null}

      {tab === "charts" ? (
        <div className="cmChartsStack">
          <div className="cmChartsHeader">
            <div className="cmChartsHeading">
              <div className="cmPanelTitle">{activeGraph === "layers" ? "Capas activas" : (hasTemporalSeries ? (resumenConsulta?.tipoPeriodo === "comparar_anios" ? "Comparación temporal" : "Evolución temporal") : (isSingleSnapshot ? "Perfil del territorio" : "Comparación territorial"))}</div>
              <p className="cmChartCaption cmHeaderCaption">{activeGraph === "layers" ? "Capas activas visibles en el mapa." : (hasTemporalSeries ? "Resolución temporal real de la consulta." : (isSingleSnapshot ? "Vista del período seleccionado." : `Comparación de ${rows.length} territorios.`))}</p>
            </div>
            <div className="cmChartsTools">
              <div className="cmInnerSelector cmGraphSelector" role="tablist" aria-label="Tipo de gráfica">
                {graphOptions.map((option) => <button key={option.key} type="button" className={activeGraph === option.key ? "isActive" : ""} onClick={() => setGraphView(option.key)}>{option.label}</button>)}
              </div>
              <button type="button" className="cmImageBtn" onClick={downloadChart} disabled={!chartModel} title="Descargar gráfica actual como PNG"><ImageDown size={16} /> PNG</button>
            </div>
          </div>

          {chartModel ? (
            <div className="cmChartCard">
              <div className="cmChartTitle">{chartModel.title}</div>
              <p className="cmChartCaption">{chartModel.caption}</p>
              <div className="cmChartCanvas">
                {chartModel.type === "line"
                  ? <Line ref={chartRef} data={chartModel.data} options={lineOptions(chartModel.yTitle, chartModel.beginAtZero)} />
                  : <Bar ref={chartRef} data={chartModel.data} options={chartModel.orientation === "vertical" ? verticalOptions(chartModel.yTitle) : horizontalOptions(chartModel.xTitle)} />}
              </div>
              {fullChartModel?.type === "line" && temporalPointCount > 2 ? (
                <div className="cmFocusControl">
                  <div className="cmFocusHeader">
                    <strong>Énfasis temporal</strong>
                    <span>{fullChartModel.data.labels[focusStart]} → {fullChartModel.data.labels[focusEnd]}</span>
                  </div>
                  <div className="cmFocusRange" style={{ "--focus-start": `${focusStartPercent}%`, "--focus-end": `${focusEndPercent}%` }}>
                    <div className="cmFocusTrack" aria-hidden="true" />
                    <input className="cmFocusThumb cmFocusThumbStart" type="range" min="0" max={temporalPointCount - 1} value={focusStart} onChange={(event) => setFocusStart(Math.min(Number(event.target.value), focusEnd))} aria-label="Inicio del énfasis temporal" />
                    <input className="cmFocusThumb cmFocusThumbEnd" type="range" min="0" max={temporalPointCount - 1} value={focusEnd} onChange={(event) => setFocusEnd(Math.max(Number(event.target.value), focusStart))} aria-label="Fin del énfasis temporal" />
                  </div>
                  <small>El control solo cambia la ventana visible de la gráfica; la consulta y la exportación conservan todos los datos.</small>
                </div>
              ) : null}
            </div>
          ) : <div className="cmChartEmpty">No hay datos suficientes para mostrar esta gráfica.</div>}
        </div>
      ) : null}

      {tab === "data" ? (
        <div className="cmDataPanel">
          <div>
            <div className="cmPanelTitle">Datos de la consulta</div>
            <p className="cmDataSubtitle">{shouldPaginate ? `Mostrando ${PAGE_SIZE} filas por página de ${formatNumber(rows.length)} registros.` : `Mostrando ${formatNumber(rows.length)} registros en una vista con desplazamiento.`}</p>
          </div>
          <div className="cmTableWrap isPreview">
            <table className="cmTable">
              <thead><tr>{showDateColumn ? <th>Fecha</th> : null}<th>Territorio</th><th>Clave</th><th>Cluster</th><th>Observaciones</th><th>FIRMS</th><th>CONAFOR</th><th>Hectáreas</th></tr></thead>
              <tbody>
                {visibleRows.map((row, index) => <tr key={`${row.cvegeo || row.cve_ent}-${row.fecha || row.anio_comparacion || row.anio}-${row.mes || "periodo"}-${index}`}>{showDateColumn ? <td>{row.fecha || ""}</td> : null}<td>{territoryName(row)}</td><td>{row.cvegeo || row.cve_ent}</td><td>{row.cluster}</td><td>{formatNumber(row.observaciones ?? 1)}</td><td>{formatNumber(row.firms_detecciones)}</td><td>{formatNumber(row.conafor_eventos)}</td><td>{formatNumber(row.conafor_ha, 2)}</td></tr>)}
                {!rows.length ? <tr><td colSpan={(showDateColumn ? 1 : 0) + 7}>No hay filas disponibles para esta consulta.</td></tr> : null}
              </tbody>
            </table>
          </div>
          {shouldPaginate ? <div className="cmPagination"><button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>Anterior</button><span>Página {page} de {totalPages}</span><button type="button" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={page >= totalPages}>Siguiente</button></div> : null}
        </div>
      ) : null}
    </ModalShell>
  );
}

function buildBarChartModel({ activeGraph, rows, summaryRows }) {
  if (!rows.length) return null;
  if (rows.length === 1) {
    const row = rows[0];
    if (activeGraph === "climate") {
      return {
        type: "bar",
        title: "Condiciones climáticas",
        caption: "Valores correspondientes al período consultado.",
        xTitle: "Valor",
        data: {
          labels: ["Temperatura mínima (°C)", "Temperatura máxima (°C)", "Precipitación (mm)"],
          datasets: [{ label: "Valor", data: [row.temp_min_c ?? 0, row.temp_max_c ?? 0, row.precip_mm ?? 0], backgroundColor: ["#2563EB", "#F97316", "#0891B2"], borderRadius: 5 }],
        },
      };
    }
    return {
      type: "bar",
      title: "Fuentes de detección y registro",
      caption: "Conteos FIRMS y CONAFOR para el período consultado.",
      xTitle: "Conteo",
      data: { labels: ["Detecciones FIRMS", "Eventos CONAFOR"], datasets: [{ label: "Conteo", data: [Number(row.firms_detecciones || 0), Number(row.conafor_eventos || 0)], backgroundColor: ["#F97316", "#DC2626"], borderRadius: 5 }] },
    };
  }

  if (activeGraph === "clusters") {
    return {
      type: "bar",
      title: "Distribución de observaciones por cluster",
      caption: "Observaciones acumuladas agrupadas por patrón ML.",
      xTitle: "Observaciones",
      data: { labels: summaryRows.map((row) => row.estado_app || `Cluster ${row.cluster_id}`), datasets: [{ label: "Observaciones", data: summaryRows.map((row) => Number(row.n_observaciones || 0)), backgroundColor: summaryRows.map((row) => row.color_sugerido_app || "#0F766E"), borderRadius: 5 }] },
    };
  }

  const metric = {
    firms: { field: "firms_detecciones", title: "Top territorios por detecciones FIRMS", xTitle: "Detecciones FIRMS", color: "#F97316" },
    conafor: { field: "conafor_eventos", title: "Top territorios por eventos CONAFOR", xTitle: "Eventos CONAFOR", color: "#DC2626" },
    hectares: { field: "conafor_ha", title: "Top territorios por hectáreas CONAFOR", xTitle: "Hectáreas", color: "#B45309" },
  }[activeGraph];
  if (!metric) return null;
  const topRows = [...rows].sort((a, b) => Number(b[metric.field] || 0) - Number(a[metric.field] || 0)).slice(0, 12);
  return {
    type: "bar",
    title: metric.title,
    caption: "Comparación territorial para la consulta activa.",
    xTitle: metric.xTitle,
    data: { labels: topRows.map(territoryName), datasets: [{ label: metric.xTitle, data: topRows.map((row) => Number(row[metric.field] || 0)), backgroundColor: metric.color, borderRadius: 5 }] },
  };
}

function SummaryItem({ label, value }) {
  return <div className="cmSummaryItem"><span>{label}</span><strong>{value === 0 || value ? value : "N/D"}</strong></div>;
}
