import { useMemo, useState } from "react";
import { BarChart3, Download, FileText, LayoutDashboard } from "lucide-react";
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";

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

const formatNumber = (value, digits = 0) => Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });
const territoryName = (row) => row.nombre_municipio || row.nombre_entidad || row.cvegeo || row.cve_ent || "N/D";
const horizontalOptions = (xTitle = "") => ({
  indexAxis: "y",
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: { x: { beginAtZero: true, title: { display: Boolean(xTitle), text: xTitle } } },
});

export default function RealResultsModal({ open, onClose, resumenConsulta = null, onOpenExport }) {
  const [tab, setTab] = useState("summary");
  const [graphView, setGraphView] = useState("activity");
  const rows = resumenConsulta?.rows ?? [];
  const summaryRows = resumenConsulta?.summaryRows ?? [];
  const temporalRows = resumenConsulta?.temporalRows ?? [];
  const isTemporalComparison = temporalRows.length > 1;
  const isSingleTerritory = !isTemporalComparison && rows.length <= 1;
  const graphOptions = isTemporalComparison ? TEMPORAL_GRAPH_OPTIONS : (isSingleTerritory ? SINGLE_GRAPH_OPTIONS : MULTI_GRAPH_OPTIONS);
  const activeGraph = graphOptions.some((option) => option.key === graphView) ? graphView : graphOptions[0]?.key;
  const chartModel = useMemo(() => buildChartModel({ activeGraph, rows, summaryRows, temporalRows }), [activeGraph, rows, summaryRows, temporalRows]);
  const ml = resumenConsulta?.resultadoMl ?? {};

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
              <div className="cmPanelTitle">{isTemporalComparison ? "Comparación entre años" : (isSingleTerritory ? "Perfil del territorio" : "Comparación territorial")}</div>
              <p className="cmChartCaption">
                {isTemporalComparison ? `Contraste temporal para ${resumenConsulta?.territorio || "el territorio seleccionado"}.` : (isSingleTerritory ? "Las gráficas cambian de métrica porque la consulta contiene un solo territorio agregado." : `Comparación de ${rows.length} territorios devueltos por la consulta.`)}
              </p>
            </div>
            <div className="cmInnerSelector cmGraphSelector" role="tablist" aria-label="Tipo de gráfica">
              {graphOptions.map((option) => <button key={option.key} type="button" className={activeGraph === option.key ? "isActive" : ""} onClick={() => setGraphView(option.key)}>{option.label}</button>)}
            </div>
          </div>
          {chartModel ? <div className="cmChartCard"><div className="cmChartTitle">{chartModel.title}</div><p className="cmChartCaption">{chartModel.caption}</p><div className="cmChartCanvas"><Bar data={chartModel.data} options={horizontalOptions(chartModel.xTitle)} /></div></div> : <div className="cmChartEmpty">No hay datos suficientes para mostrar esta gráfica.</div>}
        </div>
      ) : null}

      {tab === "data" ? (
        <div className="cmDataPanel">
          <div><div className="cmPanelTitle">Datos de la consulta</div><p className="cmDataSubtitle">Mostrando hasta 50 filas devueltas para la consulta ejecutada.</p></div>
          <div className="cmTableWrap isPreview"><table className="cmTable"><thead><tr>{isTemporalComparison ? <th>Año</th> : null}<th>Territorio</th><th>Clave</th><th>Cluster</th><th>Observaciones</th><th>FIRMS</th><th>CONAFOR</th><th>Hectáreas</th></tr></thead><tbody>
            {rows.slice(0, 50).map((row, index) => <tr key={`${row.cvegeo || row.cve_ent}-${row.anio_comparacion || row.anio}-${row.mes || "anio"}-${index}`}>{isTemporalComparison ? <td>{row.anio_comparacion}</td> : null}<td>{territoryName(row)}</td><td>{row.cvegeo || row.cve_ent}</td><td>{row.cluster}</td><td>{formatNumber(row.observaciones)}</td><td>{formatNumber(row.firms_detecciones)}</td><td>{formatNumber(row.conafor_eventos)}</td><td>{formatNumber(row.conafor_ha, 2)}</td></tr>)}
            {!rows.length ? <tr><td colSpan={isTemporalComparison ? 8 : 7}>No hay filas disponibles para esta consulta.</td></tr> : null}
          </tbody></table></div>
        </div>
      ) : null}
    </ModalShell>
  );
}

function buildChartModel({ activeGraph, rows, summaryRows, temporalRows }) {
  if (temporalRows.length > 1 && activeGraph?.startsWith("compare")) {
    const metric = {
      compareActivity: { field: "observaciones", title: "Observaciones por año", xTitle: "Observaciones" },
      compareFirms: { field: "firms_detection_count_total", title: "Detecciones FIRMS por año", xTitle: "Detecciones FIRMS" },
      compareConafor: { field: "conafor_event_count_total", title: "Incendios CONAFOR por año", xTitle: "Eventos CONAFOR" },
      compareHectares: { field: "conafor_total_hectareas_total", title: "Hectáreas CONAFOR por año", xTitle: "Hectáreas" },
    }[activeGraph];
    return {
      title: metric.title,
      caption: "Comparación directa de los dos años seleccionados para el mismo alcance territorial.",
      xTitle: metric.xTitle,
      data: { labels: temporalRows.map((row) => row.label), datasets: [{ label: metric.xTitle, data: temporalRows.map((row) => Number(row[metric.field] || 0)), borderRadius: 5 }] },
    };
  }

  if (!rows.length) return null;
  if (rows.length === 1) {
    const row = rows[0];
    if (activeGraph === "sources") return { title: "Fuentes de detección y registro", caption: "Conteos FIRMS y CONAFOR para el período consultado.", xTitle: "Conteo", data: { labels: ["Detecciones FIRMS", "Eventos CONAFOR"], datasets: [{ label: "Conteo", data: [Number(row.firms_detecciones || 0), Number(row.conafor_eventos || 0)], borderRadius: 5 }] } };
    if (activeGraph === "climate") return { title: "Condiciones climáticas promedio", caption: "Temperatura mínima, máxima y precipitación promedio.", xTitle: "Valor", data: { labels: ["Temperatura mínima (°C)", "Temperatura máxima (°C)", "Precipitación (mm)"], datasets: [{ label: "Promedio", data: [Number(row.temp_min_c || 0), Number(row.temp_max_c || 0), Number(row.precip_mm || 0)], borderRadius: 5 }] } };
    return { title: "Actividad observada durante el período", caption: "Días con señales de incendio y cobertura de las fuentes disponibles.", xTitle: "Días", data: { labels: ["Incendio activo", "Patrón extremo", "Con CONAFOR", "Con FIRMS", "Con SMN"], datasets: [{ label: "Días", data: [Number(row.dias_incendio || 0), Number(row.dias_extremo || 0), Number(row.dias_conafor || 0), Number(row.dias_firms || 0), Number(row.dias_smn || 0)], borderRadius: 5 }] } };
  }

  if (activeGraph === "clusters") return { title: "Distribución de observaciones por cluster", caption: "Observaciones acumuladas agrupadas por patrón ML.", xTitle: "Observaciones", data: { labels: summaryRows.map((row) => row.estado_app || `Cluster ${row.cluster_id}`), datasets: [{ label: "Observaciones", data: summaryRows.map((row) => Number(row.n_observaciones || 0)), borderRadius: 5 }] } };

  const metric = {
    firms: { field: "firms_detecciones", title: "Top territorios por detecciones FIRMS", xTitle: "Detecciones FIRMS" },
    conafor: { field: "conafor_eventos", title: "Top territorios por eventos CONAFOR", xTitle: "Eventos CONAFOR" },
    hectares: { field: "conafor_ha", title: "Top territorios por hectáreas CONAFOR", xTitle: "Hectáreas" },
  }[activeGraph];
  if (!metric) return null;
  const topRows = [...rows].sort((a, b) => Number(b[metric.field] || 0) - Number(a[metric.field] || 0)).slice(0, 12);
  return { title: metric.title, caption: "Comparación territorial para la consulta activa.", xTitle: metric.xTitle, data: { labels: topRows.map(territoryName), datasets: [{ label: metric.xTitle, data: topRows.map((row) => Number(row[metric.field] || 0)), borderRadius: 5 }] } };
}

function SummaryItem({ label, value }) {
  return <div className="cmSummaryItem"><span>{label}</span><strong>{value === 0 || value ? value : "N/D"}</strong></div>;
}
