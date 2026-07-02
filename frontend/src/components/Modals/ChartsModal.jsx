import { useMemo, useState } from "react";
import { BarChart3, Brain, Download, FileText, LayoutDashboard } from "lucide-react";
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
import { Bar, Line, Scatter } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import { CLUSTER_APP_COLORS, MOCK_CHARTS_DATA } from "./mockChartsData";
import "./ChartsModal.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

const TABS = [
  { key: "summary", label: "Resumen", icon: LayoutDashboard },
  { key: "charts", label: "Graficas", icon: BarChart3 },
  { key: "data", label: "Datos", icon: FileText },
  { key: "model", label: "Modelo ML", icon: Brain },
];

const GRAPH_VIEWS = [
  { key: "clusters", label: "Clusters" },
  { key: "activity", label: "Actividad" },
  { key: "temporal", label: "Temporal" },
  { key: "top", label: "Top territorios" },
  { key: "scatter", label: "Dispersion" },
];

const TOP_METRICS = [
  {
    key: "firms",
    label: "Detecciones FIRMS",
    field: "firms_detection_count_total",
    title: "Top territorios por detecciones FIRMS",
    subtitle: "Territorios ordenados por detecciones satelitales.",
    xTitle: "Detecciones FIRMS",
  },
  {
    key: "conafor",
    label: "Incendios CONAFOR",
    field: "conafor_event_count_total",
    title: "Top territorios por incendios CONAFOR",
    subtitle: "Territorios ordenados por incendios registrados.",
    xTitle: "Incendios CONAFOR",
  },
  {
    key: "hectares",
    label: "Hectareas CONAFOR",
    field: "conafor_total_hectareas_total",
    title: "Top territorios por hectareas CONAFOR",
    subtitle: "Territorios ordenados por superficie registrada.",
    xTitle: "Hectareas CONAFOR",
  },
];

const SCATTER_VIEWS = [
  {
    key: "clima",
    label: "Temperatura vs FIRMS",
    title: "Temperatura vs Detecciones FIRMS",
    xField: "temperatura_maxima_c_promedio",
    yField: "firms_detection_count_total",
    xTitle: "Temperatura maxima promedio (°C)",
    yTitle: "Detecciones FIRMS",
    subtitle: "Relacion entre temperatura maxima promedio y detecciones satelitales.",
  },
  {
    key: "oficial",
    label: "FIRMS vs CONAFOR",
    title: "Detecciones FIRMS vs Hectareas CONAFOR",
    xField: "firms_detection_count_total",
    yField: "conafor_total_hectareas_total",
    xTitle: "Detecciones FIRMS",
    yTitle: "Hectareas afectadas (CONAFOR)",
    subtitle: "Relacion entre detecciones satelitales y superficie registrada por CONAFOR.",
  },
];

const NEUTRAL_CLUSTER_COLOR = "#64748B";
const MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const TEMPORAL_SERIES_COLORS = ["#1D4ED8", "#DC2626", "#D97706", "#0D9488", "#7C3AED", "#059669", "#B45309"];

// Mock temporal para validar el modal mientras la API todavía no entrega resultados.
const USE_CHARTS_MOCK = true;

const formatNumber = (value, digits = 0) =>
  Number(value || 0).toLocaleString("es-MX", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });

const formatDate = (value) => {
  if (!value) return "N/D";
  const [year, month = "01", day = "01"] = String(value).split("-");
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}/${year}`;
};

const getTerritoryName = (row, levelKey) =>
  levelKey === "municipio"
    ? row.nombre_municipio || row.nombre_entidad || row.cvegeo || "N/D"
    : row.nombre_entidad || row.cve_ent || "N/D";

const sumRows = (rows, field) => rows.reduce((total, row) => total + Number(row[field] || 0), 0);

const getClusterIdFromRow = (row) => {
  const id = Number(row?.cluster_som_k07 ?? row?.cluster_id ?? row?.clusterId);
  return Number.isFinite(id) ? id : null;
};

const getMetricValue = (row, field) => Number(row?.[field] ?? 0);

const hasPositiveData = (values) => values.some((value) => Number(value || 0) > 0);

const normalizeMlResult = (row = {}, stats = {}) => {
  const clusterId =
    row.cluster_som_k07 ??
    row.cluster_id ??
    stats.cluster_som_k07 ??
    stats.cluster_id ??
    getClusterIdFromRow(row) ??
    getClusterIdFromRow(stats);

  const rawColor = row.color_sugerido_app ?? stats.color_sugerido_app;

  return {
    ...row,
    ...stats,
    cluster_som_k07: clusterId,
    cluster_id: clusterId,
    estado_app: row.estado_app || stats.estado_app || "Sin clasificacion disponible",
    etiqueta_final: row.etiqueta_final || stats.etiqueta_final || "Sin etiqueta disponible",
    descripcion_app: row.descripcion_app || stats.descripcion_app || "Sin descripcion disponible",
    explicacion_app: row.explicacion_app || stats.explicacion_app || "Sin explicacion tecnica disponible",
    color_sugerido_app: rawColor || NEUTRAL_CLUSTER_COLOR,
    has_color_sugerido_app: Boolean(rawColor),
    prioridad_visual_app: row.prioridad_visual_app ?? stats.prioridad_visual_app ?? Number.MAX_SAFE_INTEGER,
    dias: row.dias ?? stats.dias ?? row.n_observaciones ?? stats.n_observaciones ?? 0,
  };
};

function buildBarOptions({ legend, xTitle = "", yTitle = "" }) {
  return {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 2, right: 8, bottom: 0, left: 0 } },
    plugins: {
      legend: {
        display: legend,
        position: "bottom",
        labels: { boxWidth: 10, boxHeight: 10, padding: 10, font: { size: 11 } },
      },
      tooltip: { enabled: true },
    },
    scales: {
      x: {
        beginAtZero: true,
        title: { display: Boolean(xTitle), text: xTitle },
        ticks: { color: "#344054" },
      },
      y: {
        ticks: { autoSkip: false, color: "#344054" },
        title: { display: Boolean(yTitle), text: yTitle },
      },
    },
  };
}

export default function ChartsModal({
  open,
  onClose,
  consultaActiva = null,
  resumenConsulta = null,
  selectedMlCluster = null,
  onSelectedMlClusterChange,
  onDownloadExport,
}) {
  const [tab, setTab] = useState("summary");
  const [graphView, setGraphView] = useState("clusters");
  const [topMetric, setTopMetric] = useState("firms");
  const [scatterView, setScatterView] = useState("clima");
  const [temporalRange, setTemporalRange] = useState({ start: 0, end: 999 });

  const activeResumenConsulta = USE_CHARTS_MOCK ? MOCK_CHARTS_DATA : resumenConsulta;
  const modelSelectedCluster = selectedMlCluster;
  const model = useMemo(() => buildModel(activeResumenConsulta, modelSelectedCluster), [activeResumenConsulta, modelSelectedCluster]);

  const visibleTemporalModel = useMemo(
    () => ({
      ...model,
      temporalRows: sliceRowsByRange(model.temporalRows, temporalRange),
    }),
    [model, temporalRange]
  );

  const activeTabIndex = TABS.findIndex((item) => item.key === tab);
  const activeTopMetric = TOP_METRICS.find((metric) => metric.key === topMetric) ?? TOP_METRICS[0];
  const activeScatter = SCATTER_VIEWS.find((item) => item.key === scatterView) ?? SCATTER_VIEWS[0];

  const activeTopRows = useMemo(
    () =>
      [...model.topRows]
        .filter((row) => Number.isFinite(getMetricValue(row, activeTopMetric.field)))
        .sort((a, b) => getMetricValue(b, activeTopMetric.field) - getMetricValue(a, activeTopMetric.field)),
    [model.topRows, activeTopMetric]
  );

  const clusterChartOptions = useMemo(() => buildBarOptions({ legend: false, xTitle: "Dias acumulados" }), []);
  const activityChartOptions = useMemo(() => buildBarOptions({ legend: false, xTitle: "Dias acumulados" }), []);

  const lineOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 2, right: 8, bottom: 0, left: 0 } },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: { boxWidth: 10, boxHeight: 10, padding: 10, font: { size: 11 } },
        },
        tooltip: { enabled: true },
      },
      scales: {
        x: { title: { display: true, text: "Mes" }, ticks: { color: "#344054" } },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Detecciones FIRMS" },
          ticks: { color: "#344054" },
        },
      },
    }),
    []
  );

  const topChartOptions = useMemo(() => {
    const baseOptions = buildBarOptions({ legend: false, xTitle: activeTopMetric.xTitle });

    return {
      ...baseOptions,
      plugins: {
        ...baseOptions.plugins,
        tooltip: {
          enabled: true,
          callbacks: {
            label: (context) => {
              const row = activeTopRows[context.dataIndex] ?? {};
              const name = getTerritoryName(row, model.levelKey);
              return `${name} - ${activeTopMetric.label}: ${formatNumber(
                row[activeTopMetric.field],
                activeTopMetric.key === "hectares" ? 2 : 0
              )}`;
            },
          },
        },
      },
    };
  }, [activeTopMetric, activeTopRows, model.levelKey]);

  const scatterOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 2, right: 8, bottom: 0, left: 0 } },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { boxWidth: 10, boxHeight: 10, padding: 10, font: { size: 11 } },
        },
        tooltip: {
          enabled: true,
          callbacks: {
            label: (context) => {
              const row = context.raw?.source ?? {};
              return [
                getTerritoryName(row, model.levelKey),
                row.estado_app,
                `${activeScatter.xTitle}: ${formatNumber(context.parsed.x, 2)}`,
                `${activeScatter.yTitle}: ${formatNumber(context.parsed.y, 2)}`,
              ];
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          title: { display: true, text: activeScatter.xTitle },
          ticks: { color: "#344054" },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: activeScatter.yTitle },
          ticks: { color: "#344054" },
        },
      },
    }),
    [activeScatter, model.levelKey]
  );

  const onTabKeyDown = (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;

    event.preventDefault();

    let nextIndex = activeTabIndex;

    if (event.key === "ArrowLeft") nextIndex = activeTabIndex <= 0 ? TABS.length - 1 : activeTabIndex - 1;
    if (event.key === "ArrowRight") nextIndex = activeTabIndex >= TABS.length - 1 ? 0 : activeTabIndex + 1;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = TABS.length - 1;

    setTab(TABS[nextIndex].key);
  };

  const toggleCluster = (clusterId) => {
    const next = Number(selectedMlCluster) === Number(clusterId) ? null : clusterId;
    onSelectedMlClusterChange?.(next);
  };

  const renderSelectedChart = () => {
    if (!activeResumenConsulta) return <ChartEmpty message="Ejecuta una consulta para visualizar resultados." />;

    if (graphView === "clusters") {
      const values = model.clusterDayRows.map((row) => row.dias);

      if (!hasPositiveData(values)) return <ChartEmpty message="No hay datos suficientes para mostrar esta grafica." />;

      return (
        <ChartCard title="Distribucion de clusters" caption="Dias por patron ML">
          <Bar data={buildClusterChart(model)} options={clusterChartOptions} />
        </ChartCard>
      );
    }

    if (graphView === "activity") {
      const activityRows = buildActivityRows(model);
      const values = activityRows.map((row) => row.value);

      if (!hasPositiveData(values)) return <ChartEmpty message="No hay datos suficientes para mostrar esta grafica." />;

      return (
        <ChartCard
          title="Actividad por condicion"
          caption="Dias por tipo de actividad"
          legend={<ChartLegend items={activityRows} />}
        >
          <Bar data={buildActivityChart(model)} options={activityChartOptions} />
        </ChartCard>
      );
    }

    if (graphView === "temporal") {
      const values = visibleTemporalModel.temporalRows.map((row) => getMetricValue(row, "firms_detection_count_total"));

      if (!hasPositiveData(values)) return <ChartEmpty message="No hay datos suficientes para mostrar esta grafica." />;

      return (
        <ChartCard
          title="Serie temporal"
          caption="Detecciones FIRMS por periodo"
          control={<TemporalRangeControl rows={model.temporalRows} range={temporalRange} onChange={setTemporalRange} />}
          controlPosition="bottom"
        >
          <Line data={buildTemporalChart(visibleTemporalModel)} options={lineOptions} />
        </ChartCard>
      );
    }

    if (graphView === "top") {
      const values = activeTopRows.map((row) => getMetricValue(row, activeTopMetric.field));

      if (!hasPositiveData(values)) return <ChartEmpty message="No hay datos suficientes para mostrar esta grafica." />;

      return (
        <ChartCard
          title={activeTopMetric.title}
          caption={activeTopMetric.subtitle}
          control={<SegmentedControl options={TOP_METRICS} value={topMetric} onChange={setTopMetric} className="cmMetricSelector" />}
        >
          <Bar data={buildTopChart(activeTopRows, model.levelKey, activeTopMetric)} options={topChartOptions} />
        </ChartCard>
      );
    }

    const scatterRows = buildScatterRows(model.scatterRows, activeScatter);

    if (scatterRows.length < 2) return <ChartEmpty message="No hay datos suficientes para mostrar esta grafica." />;

    return (
      <ChartCard
        title={activeScatter.title}
        caption="Relacion entre las variables seleccionadas"
        control={<SegmentedControl options={SCATTER_VIEWS} value={scatterView} onChange={setScatterView} className="cmScatterSelector" />}
      >
        <Scatter data={buildScatterChart(scatterRows)} options={scatterOptions} />
      </ChartCard>
    );
  };

  return (
    <ModalShell open={open} onClose={onClose} title="Resultados ML" width={1040} footer={null} allowOverlayClose={true}>
      <div className="cmSub">Resultados finales para {model.levelLabel.toLowerCase()} en el periodo consultado.</div>

      <div className="cmTabs" role="tablist" aria-label="Resultados ML">
        {TABS.map((item) => {
          const TabIcon = item.icon;

          return (
            <button
              key={item.key}
              type="button"
              className={`cmTab ${tab === item.key ? "isActive" : ""}`}
              onClick={() => setTab(item.key)}
              onKeyDown={onTabKeyDown}
              role="tab"
              aria-selected={tab === item.key}
              id={`results-tab-${item.key}`}
              tabIndex={tab === item.key ? 0 : -1}
            >
              <TabIcon size={16} />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "summary" && (
        <div className="cmPanel" role="tabpanel" aria-labelledby="results-tab-summary">
          <div className="cmSummaryGrid">
            <SummaryItem label="Territorio" value={model.territory} />
            <SummaryItem label="Periodo" value={model.periodLabel} />
            <SummaryItem label="Nivel de analisis" value={model.levelLabel} />
            <SummaryItem label="Observaciones evaluadas" value={formatNumber(model.totals.observations)} />
            <SummaryItem label="Patron dominante" value={model.dominant?.estado_app} />
            <SummaryItem label="Etiqueta" value={model.dominant?.etiqueta_final} />
          </div>

          <div
            className={`cmDominant ${model.dominant?.has_color_sugerido_app ? "hasMlColor" : ""}`}
            style={model.dominant?.has_color_sugerido_app ? { borderLeftColor: model.dominant.color_sugerido_app } : undefined}
          >
            <div className="cmPanelTitle">Perfil interpretativo ML</div>
            <strong>{model.dominant?.estado_app || "Sin clasificacion disponible"}</strong>
            <p>{model.dominant?.descripcion_app || "Sin descripcion disponible"}</p>
            {model.dominant?.explicacion_app ? (
              <details>
                <summary>Ver detalle tecnico</summary>
                <p>{model.dominant.explicacion_app}</p>
              </details>
            ) : null}
          </div>

          <div className="cmClusterCards isSummary">
            {model.clusterCards.map((cluster) => (
              <ClusterCard
                key={cluster.cluster_som_k07}
                cluster={cluster}
                active={Number(selectedMlCluster) === Number(cluster.cluster_som_k07)}
                dimmed={Boolean(selectedMlCluster) && Number(selectedMlCluster) !== Number(cluster.cluster_som_k07)}
                onClick={() => toggleCluster(cluster.cluster_som_k07)}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "charts" && (
        <div className="cmChartsStack" role="tabpanel" aria-labelledby="results-tab-charts">
          <div className="cmChartsHeader">
            <div className="cmPanelTitle">Graficas de resultados</div>
            <SegmentedControl options={GRAPH_VIEWS} value={graphView} onChange={setGraphView} className="cmGraphSelector" />
          </div>
          {renderSelectedChart()}
        </div>
      )}

      {tab === "data" && (
        <div className="cmDataPanel" role="tabpanel" aria-labelledby="results-tab-data">
          <div>
            <div className="cmPanelTitle">Vista previa de exportacion</div>
            <p className="cmDataSubtitle">
              Mostrando las primeras 50 filas del resultado filtrado. El archivo completo se descarga con "Exportar datos".
            </p>
          </div>

          <div className="cmTableWrap isPreview">
            <table className="cmTable">
              <thead>
                <tr>
                  <th>fecha</th>
                  <th>{model.levelKey === "municipio" ? "Municipio" : "Entidad"}</th>
                  <th>cluster_som_k07</th>
                  <th>estado_app</th>
                  <th>etiqueta_final</th>
                  <th>descripcion_app</th>
                  <th>dias</th>
                </tr>
              </thead>
              <tbody>
                {model.previewRows.map((row) => {
                  const territoryName = getTerritoryName(row, model.levelKey);
                  const territoryKey = model.levelKey === "municipio" ? row.cvegeo : row.cve_ent;

                  return (
                    <tr key={row.id_observacion || `${row.fecha}-${territoryKey}-${row.cluster_som_k07}`}>
                      <td>{formatDate(row.fecha)}</td>
                      <td title={`${territoryName} - clave: ${territoryKey}`}>{territoryName}</td>
                      <td>{row.cluster_som_k07}</td>
                      <td>{row.estado_app}</td>
                      <td>{row.etiqueta_final}</td>
                      <td>{row.descripcion_app}</td>
                      <td>{formatNumber(row.dias)}</td>
                    </tr>
                  );
                })}
                {model.previewRows.length === 0 ? (
                  <tr>
                    <td colSpan={7}>No hay filas disponibles para la consulta activa.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="cmDataActions">
            <button
              type="button"
              className="cmExportBtn"
              onClick={() => onDownloadExport?.({ format: "csv", consultaActiva, resumenConsulta: activeResumenConsulta })}
            >
              <Download size={16} />
              Exportar datos
            </button>
          </div>
        </div>
      )}

      {tab === "model" && (
        <div className="cmPanel" role="tabpanel" aria-labelledby="results-tab-model">
          <div className="cmModelGrid">
            <SummaryItem label="Modelo aplicado" value="PCA + SOM + K-Means" />
            <SummaryItem label="Unidad de analisis" value={model.analysisUnit} />
            <SummaryItem label="Patron dominante" value={model.dominant?.estado_app} />
            <SummaryItem label="Estado" value={model.dominant?.estado_app} />
            <SummaryItem label="Etiqueta" value={model.dominant?.etiqueta_final} />
            <SummaryItem label="Resultados presentes" value={model.clusterCards.length} />
          </div>
          <div className="cmMlSummary">
            <div className="cmPanelTitle">Interpretacion tecnica</div>
            <p>{model.dominant?.descripcion_app || "Sin descripcion disponible"}</p>
            <p>{model.dominant?.explicacion_app || "Sin explicacion tecnica disponible"}</p>
          </div>
        </div>
      )}
    </ModalShell>
  );
}

function buildModel(resumen, selectedCluster) {
  const summaryRows = resumen?.summaryRows ?? [];
  const catalogRows = resumen?.catalogRows ?? [];
  const statsById = new Map(summaryRows.map((row) => [getClusterIdFromRow(row), row]));
  const normalizedCatalog = catalogRows.map((row) => normalizeMlResult(row, statsById.get(getClusterIdFromRow(row))));
  const normalizedSummary = summaryRows.map((row) =>
    normalizeMlResult(
      catalogRows.find((item) => getClusterIdFromRow(item) === getClusterIdFromRow(row)),
      row
    )
  );
  const selectedRows = selectedCluster
    ? normalizedSummary.filter((row) => Number(row.cluster_som_k07) === Number(selectedCluster))
    : normalizedSummary;

  const dominantId =
    resumen?.clusterId ??
    getClusterIdFromRow([...normalizedSummary].sort((a, b) => Number(b.dias || 0) - Number(a.dias || 0))[0]);

  const dominant =
    normalizedCatalog.find((row) => Number(row.cluster_som_k07) === Number(dominantId)) ??
    normalizedSummary.find((row) => Number(row.cluster_som_k07) === Number(dominantId)) ??
    normalizedSummary[0] ??
    normalizeMlResult();

  const visibleClusterIds = new Set(summaryRows.map((row) => getClusterIdFromRow(row)));
  const cardSource = normalizedCatalog.length ? normalizedCatalog : normalizedSummary;

  const clusterCards = cardSource
    .filter((row) => visibleClusterIds.has(Number(row.cluster_som_k07)))
    .sort(
      (a, b) =>
        Number(a.prioridad_visual_app || 0) - Number(b.prioridad_visual_app || 0) ||
        Number(a.cluster_som_k07 || 0) - Number(b.cluster_som_k07 || 0)
    );

  const totals = {
    observations: sumRows(selectedRows, "n_observaciones"),
  };

  const topRows = selectedCluster
    ? (resumen?.topRows ?? []).filter((row) => Number(row.cluster_som_k07) === Number(selectedCluster))
    : resumen?.topRows ?? [];

  const previewRows = (
    selectedCluster
      ? (resumen?.exportRows ?? []).filter((row) => Number(row.cluster_som_k07) === Number(selectedCluster))
      : resumen?.exportRows ?? []
  )
    .slice(0, 50)
    .map((row) => normalizeMlResult(row, statsById.get(getClusterIdFromRow(row))));

  const levelKey = resumen?.nivelAgregacion === "municipio" ? "municipio" : "entidad";
  const normalizedTopRows = normalizeTopRows(topRows, normalizedCatalog, statsById);

  const scatterRows = selectedCluster
    ? (resumen?.scatterRows ?? []).filter((row) => Number(row.cluster_som_k07) === Number(selectedCluster))
    : resumen?.scatterRows ?? [];

  const normalizedScatterRows = normalizeTopRows(scatterRows.length ? scatterRows : topRows, normalizedCatalog, statsById);

  return {
    hasResults: Boolean(resumen),
    territory: resumen?.territorio || "Mexico",
    periodLabel: resumen?.periodo || "Sin periodo",
    levelLabel: resumen?.nivelAgregacion === "municipio" ? "Municipal" : "Estatal",
    levelKey,
    analysisUnit: resumen?.nivelAgregacion === "municipio" ? "Municipio-dia" : "Entidad-dia",
    modelName: "PCA + SOM + KMeans",
    dominant,
    clusterCards,
    clusterDayRows: buildClusterDayRows(resumen, normalizedSummary, normalizedCatalog),
    summaryRows: normalizedSummary,
    selectedRows,
    temporalRows: resumen?.temporalRows ?? [],
    topRows: normalizedTopRows,
    scatterRows: normalizedScatterRows,
    previewRows,
    topTitle: resumen?.nivelAgregacion === "municipio" ? "Top municipios por actividad" : "Top entidades por actividad",
    totals,
  };
}

function buildClusterDayRows(resumen, summaryRows, catalogRows) {
  return Array.from({ length: 7 }, (_, clusterId) => {
    const stats = summaryRows.find((row) => Number(row.cluster_som_k07) === clusterId);
    const meta = catalogRows.find((row) => Number(row.cluster_som_k07) === clusterId);
    const normalized = normalizeMlResult(meta, stats);

    return {
      ...normalized,
      cluster_som_k07: clusterId,
      dias: getMetricValue(resumen, `dias_cluster_${clusterId}`) || Number(stats?.dias || stats?.n_observaciones || 0),
    };
  });
}

function normalizeTopRows(rows, normalizedCatalog, statsById) {
  return rows.map((row) => {
    const clusterId = getClusterIdFromRow(row);
    const meta = normalizedCatalog.find((item) => Number(item.cluster_som_k07) === Number(clusterId));

    return normalizeMlResult(meta, { ...statsById.get(clusterId), ...row });
  });
}

function getClusterColor(model, clusterId) {
  return (
    model.clusterDayRows.find((row) => Number(row.cluster_som_k07) === Number(clusterId))?.color_sugerido_app ??
    CLUSTER_APP_COLORS[clusterId] ??
    NEUTRAL_CLUSTER_COLOR
  );
}

function buildActivityRows(model) {
  const byCluster = new Map(model.clusterDayRows.map((row) => [Number(row.cluster_som_k07), Number(row.dias || 0)]));
  const sumClusters = (ids) => ids.reduce((total, id) => total + Number(byCluster.get(id) || 0), 0);

  return [
    { label: "Incendio activo extremo", value: sumClusters([2]), color: getClusterColor(model, 2) },
    { label: "Incendio activo moderado", value: sumClusters([5]), color: getClusterColor(model, 5) },
    { label: "Condicion de riesgo", value: sumClusters([4]), color: getClusterColor(model, 4) },
    { label: "Sin incendio activo", value: sumClusters([0, 1, 3, 6]), color: getClusterColor(model, 0) },
  ];
}

function buildClusterChart(model) {
  const rows = model.clusterDayRows;

  return {
    labels: rows.map((row) => row.estado_app),
    datasets: [
      {
        label: "Dias",
        data: rows.map((row) => row.dias),
        backgroundColor: rows.map((row) => row.color_sugerido_app),
        borderRadius: 5,
        barThickness: 26,
        maxBarThickness: 34,
      },
    ],
  };
}

function buildActivityChart(model) {
  const rows = buildActivityRows(model);

  return {
    labels: rows.map((row) => row.label),
    datasets: [
      {
        label: "Dias",
        data: rows.map((row) => row.value),
        backgroundColor: rows.map((row) => row.color),
        borderRadius: 5,
        barThickness: 28,
        maxBarThickness: 34,
      },
    ],
  };
}

function buildTemporalChart(model) {
  const years = Array.from(new Set(model.temporalRows.map((row) => Number(row.anio)).filter(Number.isFinite))).sort((a, b) => a - b);

  if (years.length > 1) {
    const visibleYears = years.slice(0, TEMPORAL_SERIES_COLORS.length);

    return {
      labels: MONTH_LABELS,
      datasets: visibleYears.map((year, index) => {
        const rowsByMonth = new Map(
          model.temporalRows
            .filter((row) => Number(row.anio) === year)
            .map((row) => [Number(row.mes), getMetricValue(row, "firms_detection_count_total")])
        );

        return {
          label: String(year),
          data: MONTH_LABELS.map((_, monthIndex) => rowsByMonth.get(monthIndex + 1) ?? null),
          borderColor: TEMPORAL_SERIES_COLORS[index],
          backgroundColor: TEMPORAL_SERIES_COLORS[index],
          pointRadius: 2,
          tension: 0.28,
          spanGaps: true,
        };
      }),
    };
  }

  return {
    labels: model.temporalRows.map((row) => row.label || MONTH_LABELS[Number(row.mes) - 1] || row.mes),
    datasets: [
      {
        label: "Detecciones FIRMS",
        data: model.temporalRows.map((row) => getMetricValue(row, "firms_detection_count_total")),
        borderColor: "#334155",
        backgroundColor: "#334155",
        pointRadius: 2,
        tension: 0.28,
      },
    ],
  };
}

function buildTopChart(rows, levelKey, metric) {
  return {
    labels: rows.map((row) => getTerritoryName(row, levelKey)),
    datasets: [
      {
        label: metric.label,
        data: rows.map((row) => getMetricValue(row, metric.field)),
        backgroundColor: rows.map((row) => row.color_sugerido_app || NEUTRAL_CLUSTER_COLOR),
        borderRadius: 5,
        barThickness: 24,
        maxBarThickness: 32,
      },
    ],
  };
}

function buildScatterRows(rows, scatterConfig) {
  return rows
    .map((row) => ({
      x: getMetricValue(row, scatterConfig.xField),
      y: getMetricValue(row, scatterConfig.yField),
      source: row,
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y) && (point.x !== 0 || point.y !== 0));
}

function buildScatterChart(rows) {
  const groups = new Map();

  rows.forEach((point) => {
    const key = point.source.estado_app || "Sin clasificacion disponible";

    if (!groups.has(key)) groups.set(key, { color: point.source.color_sugerido_app || NEUTRAL_CLUSTER_COLOR, points: [] });

    groups.get(key).points.push(point);
  });

  return {
    datasets: Array.from(groups.entries()).map(([label, group]) => ({
      label,
      data: group.points,
      pointRadius: 5,
      pointHoverRadius: 7,
      backgroundColor: group.color,
    })),
  };
}

function sliceRowsByRange(rows, range) {
  if (!rows.length) return [];

  const max = rows.length - 1;
  const start = Math.max(0, Math.min(Number(range.start) || 0, max));
  const end = Math.max(start, Math.min(Number(range.end) || max, max));

  return rows.slice(start, end + 1);
}

function clampRange(range, max) {
  const start = Math.max(0, Math.min(Number(range.start) || 0, max));
  const end = Math.max(start, Math.min(Number(range.end) || max, max));

  return { start, end };
}

function TemporalRangeControl({ rows, range, onChange }) {
  if (rows.length <= 1) return null;

  const max = rows.length - 1;
  const safeRange = clampRange(range, max);
  const startPercent = max > 0 ? (safeRange.start / max) * 100 : 0;
  const endPercent = max > 0 ? (safeRange.end / max) * 100 : 100;
  const startLabel = rows[safeRange.start]?.label || "Inicio";
  const endLabel = rows[safeRange.end]?.label || "Fin";

  return (
    <div className="cmTemporalRange">
      <div className="cmTemporalRangeLabels">
        <span>{startLabel}</span>
        <span>{endLabel}</span>
      </div>
      <div
        className="cmTemporalSliders"
        style={{
          "--range-start": `${startPercent}%`,
          "--range-end": `${endPercent}%`,
        }}
      >
        <input
          type="range"
          min="0"
          max={max}
          value={safeRange.start}
          aria-label="Inicio del rango temporal"
          onChange={(event) => onChange(clampRange({ ...safeRange, start: Number(event.target.value) }, max))}
        />
        <input
          type="range"
          min="0"
          max={max}
          value={safeRange.end}
          aria-label="Fin del rango temporal"
          onChange={(event) => onChange(clampRange({ ...safeRange, end: Number(event.target.value) }, max))}
        />
      </div>
    </div>
  );
}

function ClusterCard({ cluster, active, dimmed, onClick }) {
  return (
    <button
      type="button"
      className={`cmClusterCard ${active ? "isActive" : ""} ${dimmed ? "isDimmed" : ""} ${
        cluster.has_color_sugerido_app ? "hasMlColor" : ""
      }`}
      style={{
        borderLeftColor: cluster.has_color_sugerido_app ? cluster.color_sugerido_app : undefined,
        background: active ? hexToRgba(cluster.color_sugerido_app, 0.1) : undefined,
      }}
      onClick={onClick}
    >
      <strong>{cluster.estado_app}</strong>
      <span>{cluster.descripcion_app}</span>
    </button>
  );
}

function ChartCard({ title, subtitle = "", caption = "", legend = null, control = null, controlPosition = "top", children }) {
  return (
    <div className="cmChartCard">
      <div className="cmChartTitle">{title}</div>
      {subtitle ? <p className="cmChartSubtitle">{subtitle}</p> : null}
      {caption ? <p className="cmChartCaption">{caption}</p> : null}
      {control && controlPosition === "top" ? control : null}
      <div className="cmChartCanvas">{children}</div>
      {legend ? <div className="cmChartLegend">{legend}</div> : null}
      {control && controlPosition === "bottom" ? <div className="cmChartControlBelow">{control}</div> : null}
    </div>
  );
}

function SegmentedControl({ options, value, onChange, className = "" }) {
  return (
    <div className={`cmInnerSelector ${className}`} role="tablist">
      {options.map((option) => (
        <button key={option.key} type="button" className={value === option.key ? "isActive" : ""} onClick={() => onChange(option.key)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

function ChartEmpty({ message }) {
  return <div className="cmChartEmpty">{message}</div>;
}

function ChartLegend({ items }) {
  return (
    <div className="cmLegendItems">
      {items.map((item) => (
        <span key={item.label}>
          <i style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="cmSummaryItem">
      <span>{label}</span>
      <strong>{value === 0 || value ? value : "N/D"}</strong>
    </div>
  );
}

function hexToRgba(hex, alpha) {
  const value = String(hex || NEUTRAL_CLUSTER_COLOR).replace("#", "");
  const r = parseInt(value.slice(0, 2), 16) || 0;
  const g = parseInt(value.slice(2, 4), 16) || 0;
  const b = parseInt(value.slice(4, 6), 16) || 0;

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}