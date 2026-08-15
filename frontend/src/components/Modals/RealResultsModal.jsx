import { useMemo, useState } from "react";
import { BarChart3, FileText, LayoutDashboard } from "lucide-react";
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

const formatNumber = (value, digits = 0) =>
  Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });

const territoryName = (row) => row.nombre_municipio || row.nombre_entidad || row.cvegeo || row.cve_ent || "N/D";

const horizontalOptions = (xTitle = "") => ({
  indexAxis: "y",
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: {
    x: {
      beginAtZero: true,
      title: { display: Boolean(xTitle), text: xTitle },
    },
  },
});

export default function RealResultsModal({ open, onClose, resumenConsulta = null }) {
  const [tab, setTab] = useState("summary");
  const [graphView, setGraphView] = useState("activity");
  const rows = resumenConsulta?.rows ?? [];
  const summaryRows = resumenConsulta?.summaryRows ?? [];
  const isSingleTerritory = rows.length <= 1;
  const graphOptions = isSingleTerritory ? SINGLE_GRAPH_OPTIONS : MULTI_GRAPH_OPTIONS;

  const activeGraph = graphOptions.some((option) => option.key === graphView)
    ? graphView
    : graphOptions[0].key;

  const chartModel = useMemo(
    () => buildChartModel({ activeGraph, rows, summaryRows }),
    [activeGraph, rows, summaryRows]
  );

  const ml = resumenConsulta?.resultadoMl ?? {};

  return (
    <ModalShell open={open} onClose={onClose} title="Resultados ML" width={1040} footer={null} allowOverlayClose>
      <div className="cmSub">Datos reales obtenidos desde la API v2 para la consulta activa.</div>

      <div className="cmTabs" role="tablist" aria-label="Resultados ML">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              type="button"
              className={`cmTab ${tab === item.key ? "isActive" : ""}`}
              onClick={() => setTab(item.key)}
              role="tab"
              aria-selected={tab === item.key}
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "summary" && (
        <div className="cmPanel">
          <div className="cmSummaryGrid">
            <SummaryItem label="Territorio" value={resumenConsulta?.territorio} />
            <SummaryItem label="Periodo" value={resumenConsulta?.periodo} />
            <SummaryItem label="Nivel de análisis" value={resumenConsulta?.nivelAgregacion === "municipio" ? "Municipal" : "Estatal"} />
            <SummaryItem label="Observaciones evaluadas" value={formatNumber(resumenConsulta?.observaciones)} />
            <SummaryItem label="Detecciones FIRMS" value={formatNumber(resumenConsulta?.firms_detecciones)} />
            <SummaryItem label="Eventos CONAFOR" value={formatNumber(resumenConsulta?.conafor_eventos)} />
            <SummaryItem label="Hectáreas CONAFOR" value={formatNumber(resumenConsulta?.conafor_ha, 2)} />
            <SummaryItem label="Días con incendio" value={formatNumber(resumenConsulta?.dias_incendio)} />
            <SummaryItem label="Días con patrón extremo" value={formatNumber(resumenConsulta?.dias_extremo)} />
          </div>

          <div className="cmDominant" style={ml.color_sugerido_app ? { borderLeftColor: ml.color_sugerido_app } : undefined}>
            <div className="cmPanelTitle">Patrón ML dominante</div>
            <strong>{ml.estado_app || "Sin clasificación disponible"}</strong>
            <p>{ml.etiqueta_final || "Sin etiqueta disponible"}</p>
          </div>
        </div>
      )}

      {tab === "charts" && (
        <div className="cmChartsStack">
          <div className="cmChartsHeader">
            <div>
              <div className="cmPanelTitle">{isSingleTerritory ? "Perfil del territorio" : "Comparación territorial"}</div>
              <p className="cmChartCaption">
                {isSingleTerritory
                  ? "Las gráficas cambian de métrica porque la consulta contiene un solo territorio agregado."
                  : `Comparación de ${rows.length} territorios devueltos por la consulta.`}
              </p>
            </div>
            <div className="cmInnerSelector cmGraphSelector" role="tablist" aria-label="Tipo de gráfica">
              {graphOptions.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={activeGraph === option.key ? "isActive" : ""}
                  onClick={() => setGraphView(option.key)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {chartModel ? (
            <div className="cmChartCard">
              <div className="cmChartTitle">{chartModel.title}</div>
              <p className="cmChartCaption">{chartModel.caption}</p>
              <div className="cmChartCanvas">
                <Bar data={chartModel.data} options={horizontalOptions(chartModel.xTitle)} />
              </div>
            </div>
          ) : (
            <div className="cmChartEmpty">No hay datos suficientes para mostrar esta gráfica.</div>
          )}
        </div>
      )}

      {tab === "data" && (
        <div className="cmDataPanel">
          <div>
            <div className="cmPanelTitle">Datos de la consulta</div>
            <p className="cmDataSubtitle">Mostrando hasta 50 filas reales devueltas por la API v2.</p>
          </div>
          <div className="cmTableWrap isPreview">
            <table className="cmTable">
              <thead>
                <tr>
                  <th>Territorio</th>
                  <th>Clave</th>
                  <th>Cluster</th>
                  <th>Observaciones</th>
                  <th>FIRMS</th>
                  <th>CONAFOR</th>
                  <th>Hectáreas</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((row) => (
                  <tr key={`${row.cvegeo || row.cve_ent}-${row.anio}-${row.mes || "anio"}`}>
                    <td>{territoryName(row)}</td>
                    <td>{row.cvegeo || row.cve_ent}</td>
                    <td>{row.cluster}</td>
                    <td>{formatNumber(row.observaciones)}</td>
                    <td>{formatNumber(row.firms_detecciones)}</td>
                    <td>{formatNumber(row.conafor_eventos)}</td>
                    <td>{formatNumber(row.conafor_ha, 2)}</td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr><td colSpan={7}>No hay filas disponibles para esta consulta.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </ModalShell>
  );
}

function buildChartModel({ activeGraph, rows, summaryRows }) {
  if (!rows.length) return null;

  if (rows.length === 1) {
    const row = rows[0];

    if (activeGraph === "sources") {
      return {
        title: "Fuentes de detección y registro",
        caption: "Conteos agregados FIRMS y CONAFOR para el período consultado.",
        xTitle: "Conteo",
        data: {
          labels: ["Detecciones FIRMS", "Eventos CONAFOR"],
          datasets: [{
            label: "Conteo",
            data: [Number(row.firms_detecciones || 0), Number(row.conafor_eventos || 0)],
            backgroundColor: ["#D97706", "#2563EB"],
            borderRadius: 5,
          }],
        },
      };
    }

    if (activeGraph === "climate") {
      return {
        title: "Condiciones climáticas promedio",
        caption: "Temperatura mínima, temperatura máxima y precipitación promedio del registro agregado.",
        xTitle: "Valor",
        data: {
          labels: ["Temperatura mínima (°C)", "Temperatura máxima (°C)", "Precipitación (mm)"],
          datasets: [{
            label: "Promedio",
            data: [Number(row.temp_min_c || 0), Number(row.temp_max_c || 0), Number(row.precip_mm || 0)],
            backgroundColor: ["#2563EB", "#EA580C", "#0891B2"],
            borderRadius: 5,
          }],
        },
      };
    }

    return {
      title: "Actividad observada durante el período",
      caption: "Días con señales de incendio, patrón extremo y cobertura de las fuentes disponibles.",
      xTitle: "Días",
      data: {
        labels: ["Incendio activo", "Patrón extremo", "Con CONAFOR", "Con FIRMS", "Con SMN"],
        datasets: [{
          label: "Días",
          data: [
            Number(row.dias_incendio || 0),
            Number(row.dias_extremo || 0),
            Number(row.dias_conafor || 0),
            Number(row.dias_firms || 0),
            Number(row.dias_smn || 0),
          ],
          backgroundColor: ["#B91C1C", "#EA580C", "#2563EB", "#D97706", "#0891B2"],
          borderRadius: 5,
        }],
      },
    };
  }

  if (activeGraph === "clusters") {
    return {
      title: "Distribución de observaciones por cluster",
      caption: "Observaciones acumuladas de los territorios agrupadas por patrón ML.",
      xTitle: "Observaciones",
      data: {
        labels: summaryRows.map((row) => row.estado_app || `Cluster ${row.cluster_id}`),
        datasets: [{
          label: "Observaciones",
          data: summaryRows.map((row) => Number(row.n_observaciones || 0)),
          backgroundColor: summaryRows.map((row) => row.color_sugerido_app || "#64748B"),
          borderRadius: 5,
        }],
      },
    };
  }

  const metric = {
    firms: {
      field: "firms_detecciones",
      title: "Top territorios por detecciones FIRMS",
      caption: "Territorios con mayor número de detecciones satelitales.",
      xTitle: "Detecciones FIRMS",
    },
    conafor: {
      field: "conafor_eventos",
      title: "Top territorios por eventos CONAFOR",
      caption: "Territorios con mayor número de eventos registrados por CONAFOR.",
      xTitle: "Eventos CONAFOR",
    },
    hectares: {
      field: "conafor_ha",
      title: "Top territorios por hectáreas CONAFOR",
      caption: "Territorios con mayor superficie registrada en el período.",
      xTitle: "Hectáreas",
    },
  }[activeGraph];

  if (!metric) return null;

  const topRows = [...rows]
    .sort((a, b) => Number(b[metric.field] || 0) - Number(a[metric.field] || 0))
    .slice(0, 12);

  return {
    title: metric.title,
    caption: metric.caption,
    xTitle: metric.xTitle,
    data: {
      labels: topRows.map(territoryName),
      datasets: [{
        label: metric.xTitle,
        data: topRows.map((row) => Number(row[metric.field] || 0)),
        backgroundColor: topRows.map((row) => row.color_sugerido_app || "#64748B"),
        borderRadius: 5,
      }],
    },
  };
}

function SummaryItem({ label, value }) {
  return (
    <div className="cmSummaryItem">
      <span>{label}</span>
      <strong>{value === 0 || value ? value : "N/D"}</strong>
    </div>
  );
}
