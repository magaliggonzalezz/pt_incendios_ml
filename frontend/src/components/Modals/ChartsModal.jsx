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
import { Bar, Line } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

const TABS = [
  { key: "summary", label: "Resumen", icon: LayoutDashboard },
  { key: "charts", label: "Graficas", icon: BarChart3 },
  { key: "data", label: "Datos", icon: FileText },
  { key: "model", label: "Modelo ML", icon: Brain },
];

const BADGE_STYLES = {
  Alta: { background: "#FCEBEB", color: "#791F1F" },
  Media: { background: "#FAEEDA", color: "#633806" },
  Baja: { background: "#EAF3DE", color: "#27500A" },
};

const MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

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
  const [temporalRange, setTemporalRange] = useState({ start: 0, end: 999 });
  const model = useMemo(() => buildModel(resumenConsulta, selectedMlCluster), [resumenConsulta, selectedMlCluster]);
  const visibleTemporalModel = useMemo(
    () => ({
      ...model,
      temporalRows: sliceRowsByRange(model.temporalRows, temporalRange),
    }),
    [model, temporalRange]
  );
  const activeTabIndex = TABS.findIndex((item) => item.key === tab);

  const chartOptions = useMemo(
    () => ({
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: { x: { beginAtZero: true }, y: { ticks: { autoSkip: false } } },
    }),
    []
  );

  const lineOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: { y: { beginAtZero: true } },
    }),
    []
  );
  const topChartOptions = useMemo(
    () => ({
      ...chartOptions,
      plugins: {
        ...chartOptions.plugins,
        tooltip: {
          enabled: true,
          callbacks: {
            label: (context) => {
              const row = model.topRows[context.dataIndex] ?? {};
              const clave = row.cvegeo || row.cve_ent || "";
              const name = getTerritoryName(row, model.levelKey);
              return `${name} · clave: ${clave} · FIRMS: ${formatNumber(row.firms_total)}`;
            },
          },
        },
      },
    }),
    [chartOptions, model.topRows, model.levelKey]
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

  return (
    <ModalShell open={open} onClose={onClose} title="Resultados ML" width={1040} footer={null} allowOverlayClose={true}>
      <div className="cmSub">
        Resultados finales para {model.levelLabel.toLowerCase()} en el periodo consultado.
      </div>

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
            <SummaryItem label="Actividad satelital acumulada" value={formatNumber(model.totals.firms)} />
            <SummaryItem label="Dias con focos FIRMS" value={formatNumber(model.totals.firmsDays)} />
            <SummaryItem label="Dias con registro CONAFOR" value={formatNumber(model.totals.conaforDays)} />
            <SummaryItem label="Dias con cobertura SMN" value={formatNumber(model.totals.smnDays)} />
          </div>

          <div className="cmDominant" style={{ borderLeftColor: model.dominant?.color_sugerido || "#0F766E" }}>
            <div className="cmPanelTitle">Patron dominante</div>
            <strong>{model.dominant?.cluster_name || "Sin datos"}</strong>
            <p>{model.dominant?.descripcion_corta || "No hay resultados para la consulta activa."}</p>
            {model.dominant?.interpretacion_tecnica ? (
              <details>
                <summary>Ver detalle tecnico</summary>
                <p>{model.dominant.interpretacion_tecnica}</p>
              </details>
            ) : null}
          </div>
        </div>
      )}

      {tab === "charts" && (
        <div className="cmChartsStack" role="tabpanel" aria-labelledby="results-tab-charts">
          <div className="cmChartsHeader">
            <div className="cmPanelTitle">Perfil de clusters</div>
            {selectedMlCluster ? (
              <button type="button" className="cmClearBtn" onClick={() => onSelectedMlClusterChange?.(null)}>
                Quitar filtro
              </button>
            ) : null}
          </div>

          <div className="cmClusterCards">
            {model.clusterCards.map((cluster) => (
              <ClusterCard
                key={cluster.cluster_id}
                cluster={cluster}
                active={Number(selectedMlCluster) === Number(cluster.cluster_id)}
                dimmed={Boolean(selectedMlCluster) && Number(selectedMlCluster) !== Number(cluster.cluster_id)}
                onClick={() => toggleCluster(cluster.cluster_id)}
              />
            ))}
          </div>

          <div className={`cmChartsGrid ${model.showTemporal ? "" : "isSingle"}`}>
            <ChartCard title="Distribucion de clusters">
              <Bar data={buildClusterChart(model)} options={chartOptions} />
            </ChartCard>

            {model.showTemporal ? (
              <ChartCard
                title="Serie temporal de actividad"
                subtitle={selectedMlCluster ? "La serie temporal muestra el total nacional, no se filtra por cluster." : ""}
                control={
                  <TemporalRangeControl
                    rows={model.temporalRows}
                    range={temporalRange}
                    onChange={setTemporalRange}
                  />
                }
              >
                <Line data={buildTemporalChart(visibleTemporalModel)} options={lineOptions} />
              </ChartCard>
            ) : (
              <div className="cmChartCard isUnavailable">
                <div className="cmChartTitle">Serie temporal de actividad</div>
                <p className="cmUnavailableText">
                  La serie temporal esta disponible solo a nivel nacional (Estado = Todos los estados)
                </p>
              </div>
            )}
          </div>

          {model.showTop ? (
            <ChartCard title={model.topTitle}>
              <Bar data={buildTopChart(model)} options={topChartOptions} />
            </ChartCard>
          ) : null}
        </div>
      )}

      {tab === "data" && (
        <div className="cmDataPanel" role="tabpanel" aria-labelledby="results-tab-data">
          <div>
            <div className="cmPanelTitle">Vista previa de exportacion</div>
            <p className="cmDataSubtitle">
              Mostrando las primeras 50 filas del resultado filtrado. El archivo completo se descarga con
              "Exportar datos".
            </p>
          </div>

          <div className="cmTableWrap isPreview">
            <table className="cmTable">
              <thead>
                <tr>
                  <th>fecha</th>
                  <th>{model.levelKey === "municipio" ? "Municipio" : "Entidad"}</th>
                  <th>cluster_id</th>
                  <th>cluster_name</th>
                  <th>nivel_actividad_firms</th>
                  <th>nivel_confirmacion_conafor</th>
                  <th>nivel_cobertura_smn</th>
                  <th>firms_count</th>
                  <th>has_conafor</th>
                </tr>
              </thead>
              <tbody>
                {model.previewRows.map((row) => {
                  const territoryName = getTerritoryName(row, model.levelKey);
                  const territoryKey = model.levelKey === "municipio" ? row.cvegeo : row.cve_ent;
                  return (
                    <tr key={row.id_observacion || `${row.fecha}-${territoryKey}-${row.cluster_id}`}>
                      <td>{formatDate(row.fecha)}</td>
                      <td title={`${territoryName} · clave: ${territoryKey}`}>{territoryName}</td>
                      <td>{row.cluster_id}</td>
                      <td>{row.cluster_name}</td>
                      <td><Badge label={row.nivel_actividad_firms} level={row.nivel_actividad_firms} /></td>
                      <td><Badge label={row.nivel_confirmacion_conafor} level={row.nivel_confirmacion_conafor} /></td>
                      <td><Badge label={row.nivel_cobertura_smn} level={row.nivel_cobertura_smn} /></td>
                      <td>{formatNumber(row.firms_count)}</td>
                      <td>{Number(row.has_conafor) ? "Sí" : "No"}</td>
                    </tr>
                  );
                })}
                {model.previewRows.length === 0 ? (
                  <tr>
                    <td colSpan={9}>No hay filas disponibles para la consulta activa.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="cmDataActions">
            <button
              type="button"
              className="cmExportBtn"
              onClick={() => onDownloadExport?.({ format: "csv", consultaActiva, resumenConsulta })}
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
            <SummaryItem label="Flujo modelo" value={model.flow} />
            <SummaryItem label="Modelo final" value={model.modelName} />
            <SummaryItem label="Unidad de analisis" value={model.analysisUnit} />
            <SummaryItem label="Patron dominante" value={model.dominant?.cluster_label} />
            <SummaryItem label="Nombre del patron" value={model.dominant?.cluster_name} />
            <SummaryItem label="Clusters presentes" value={model.clusterCards.length} />
          </div>
          <div className="cmMlSummary">
            <div className="cmPanelTitle">Interpretacion tecnica</div>
            <p>{model.dominant?.interpretacion_tecnica || "Sin interpretacion disponible."}</p>
            <p>{model.note}</p>
          </div>
        </div>
      )}

      <div className="cmFixedFooter">{model.note}</div>
    </ModalShell>
  );
}

function buildModel(resumen, selectedCluster) {
  const summaryRows = resumen?.summaryRows ?? [];
  const catalogRows = resumen?.catalogRows ?? [];
  const selectedRows = selectedCluster
    ? summaryRows.filter((row) => Number(row.cluster_id) === Number(selectedCluster))
    : summaryRows;
  const dominant =
    catalogRows.find((row) => Number(row.cluster_id) === Number(resumen?.clusterId)) ??
    [...summaryRows].sort((a, b) => Number(b.n_observaciones || 0) - Number(a.n_observaciones || 0))[0];
  const visibleClusterIds = new Set(summaryRows.map((row) => Number(row.cluster_id)));
  const clusterCards = catalogRows
    .filter((row) => visibleClusterIds.has(Number(row.cluster_id)))
    .sort((a, b) => Number(a.orden_visualizacion || 0) - Number(b.orden_visualizacion || 0));
  const totals = {
    observations: sumRows(selectedRows, "n_observaciones"),
    firms: sumRows(selectedRows, "firms_total"),
    firmsDays: sumRows(selectedRows, "dias_con_firms"),
    conaforDays: sumRows(selectedRows, "dias_con_conafor"),
    smnDays: sumRows(selectedRows, "dias_con_smn"),
  };
  const showTemporal =
    resumen?.nivelAgregacion === "entidad" &&
    resumen?.territorio === "Mexico" &&
    resumen?.tipoPeriodo !== "anio_mes";
  const showTop =
    (resumen?.nivelAgregacion === "entidad" && resumen?.territorio === "Mexico") ||
    resumen?.nivelAgregacion === "municipio";
  const topRows = selectedCluster
    ? (resumen?.topRows ?? []).filter((row) => Number(row.cluster_id || String(row.cluster_label || "").replace(/\D/g, "")) === Number(selectedCluster))
    : resumen?.topRows ?? [];
  const previewRows = selectedCluster
    ? (resumen?.exportRows ?? []).filter((row) => Number(row.cluster_id) === Number(selectedCluster)).slice(0, 50)
    : (resumen?.exportRows ?? []).slice(0, 50);
  const levelKey = resumen?.nivelAgregacion === "municipio" ? "municipio" : "entidad";

  return {
    territory: resumen?.territorio || "Mexico",
    periodLabel: resumen?.periodo || "Sin periodo",
    levelLabel: resumen?.nivelAgregacion === "municipio" ? "Municipal" : "Estatal",
    levelKey,
    analysisUnit: resumen?.nivelAgregacion === "municipio" ? "Municipio-dia" : "Entidad-dia",
    flow: resumen?.flujoModelo || "entidad_dia",
    modelName: resumen?.modeloFinal || resumen?.modelo || "PCA + SOM + KMeans",
    note: resumen?.notaInterpretacion || "Cluster interpretativo no supervisado (PCA + SOM + KMeans); no representa prediccion ni confirmacion individual de incendio.",
    dominant,
    clusterCards,
    summaryRows,
    selectedRows,
    temporalRows: resumen?.temporalRows ?? [],
    topRows,
    previewRows,
    topTitle: resumen?.nivelAgregacion === "municipio" ? "Top municipios por actividad" : "Top entidades por actividad",
    showTemporal,
    showTop,
    totals,
  };
}

function buildClusterChart(model) {
  const selectedIds = new Set(model.selectedRows.map((row) => Number(row.cluster_id)));
  const rows = model.summaryRows;
  return {
    labels: rows.map((row) => row.cluster_label),
    datasets: [
      {
        label: "Observaciones",
        data: rows.map((row) => row.n_observaciones),
        backgroundColor: rows.map((row) => (selectedIds.has(Number(row.cluster_id)) ? row.color_sugerido : "#E5E7EB")),
        borderRadius: 5,
      },
    ],
  };
}

function buildTemporalChart(model) {
  return {
    labels: model.temporalRows.map((row) => row.label || `${MONTH_LABELS[Number(row.mes) - 1]} ${row.anio}`),
    datasets: [
      {
        label: "FIRMS total",
        data: model.temporalRows.map((row) => row.firms_total),
        borderColor: "#334155",
        backgroundColor: "#334155",
        pointRadius: 2,
        tension: 0.28,
      },
    ],
  };
}

function buildTopChart(model) {
  return {
    labels: model.topRows.map((row) => getTerritoryName(row, model.levelKey)),
    datasets: [
      {
        label: "FIRMS total",
        data: model.topRows.map((row) => row.firms_total),
        backgroundColor: model.topRows.map((row) => row.color_sugerido || "#64748B"),
        borderRadius: 5,
      },
    ],
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
      className={`cmClusterCard ${active ? "isActive" : ""} ${dimmed ? "isDimmed" : ""}`}
      style={{
        borderLeftColor: cluster.color_sugerido,
        background: active ? hexToRgba(cluster.color_sugerido, 0.1) : undefined,
      }}
      onClick={onClick}
    >
      <strong>{cluster.cluster_name}</strong>
      <span>{cluster.descripcion_corta}</span>
      <div className="cmBadges">
        <Badge label={`FIRMS: ${cluster.nivel_actividad_firms}`} level={cluster.nivel_actividad_firms} />
        <Badge label={`CONAFOR: ${cluster.nivel_confirmacion_conafor}`} level={cluster.nivel_confirmacion_conafor} />
        <Badge label={`SMN: ${cluster.nivel_cobertura_smn}`} level={cluster.nivel_cobertura_smn} />
      </div>
    </button>
  );
}

function Badge({ label, level }) {
  return (
    <span className="cmBadge" style={BADGE_STYLES[level] || BADGE_STYLES.Media}>
      {label}
    </span>
  );
}

function ChartCard({ title, subtitle = "", control = null, children }) {
  return (
    <div className="cmChartCard">
      <div className="cmChartTitle">{title}</div>
      {subtitle ? <p className="cmChartSubtitle">{subtitle}</p> : null}
      {control}
      <div className="cmChartCanvas">{children}</div>
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
  const value = String(hex || "#000000").replace("#", "");
  const r = parseInt(value.slice(0, 2), 16) || 0;
  const g = parseInt(value.slice(2, 4), 16) || 0;
  const b = parseInt(value.slice(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
