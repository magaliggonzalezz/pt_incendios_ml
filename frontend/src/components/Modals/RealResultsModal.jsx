import { useMemo, useState } from "react";
import { BarChart3, FileText, LayoutDashboard } from "lucide-react";
import { BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const TABS = [
  { key: "summary", label: "Resumen", icon: LayoutDashboard },
  { key: "charts", label: "Gráficas", icon: BarChart3 },
  { key: "data", label: "Datos", icon: FileText },
];

const formatNumber = (value, digits = 0) =>
  Number(value || 0).toLocaleString("es-MX", { maximumFractionDigits: digits });

export default function RealResultsModal({ open, onClose, resumenConsulta = null }) {
  const [tab, setTab] = useState("summary");
  const rows = resumenConsulta?.rows ?? [];
  const summaryRows = resumenConsulta?.summaryRows ?? [];

  const chartData = useMemo(() => ({
    labels: summaryRows.map((row) => row.estado_app || `Cluster ${row.cluster_id}`),
    datasets: [
      {
        label: "Observaciones",
        data: summaryRows.map((row) => Number(row.n_observaciones || 0)),
        backgroundColor: summaryRows.map((row) => row.color_sugerido_app || "#64748B"),
        borderRadius: 5,
      },
    ],
  }), [summaryRows]);

  const chartOptions = useMemo(() => ({
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: true } },
    scales: { x: { beginAtZero: true } },
  }), []);

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
          <div className="cmPanelTitle">Distribución por cluster</div>
          {summaryRows.length ? (
            <div className="cmChartCard">
              <div className="cmChartCanvas">
                <Bar data={chartData} options={chartOptions} />
              </div>
            </div>
          ) : (
            <div className="cmChartEmpty">No hay datos suficientes para mostrar esta gráfica.</div>
          )}
        </div>
      )}

      {tab === "data" && (
        <div className="cmDataPanel">
          <div className="cmPanelTitle">Datos de la consulta</div>
          <div className="cmTableWrap isPreview">
            <table className="cmTable">
              <thead>
                <tr>
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
                    <td>{row.cvegeo || row.cve_ent}</td>
                    <td>{row.cluster}</td>
                    <td>{formatNumber(row.observaciones)}</td>
                    <td>{formatNumber(row.firms_detecciones)}</td>
                    <td>{formatNumber(row.conafor_eventos)}</td>
                    <td>{formatNumber(row.conafor_ha, 2)}</td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr><td colSpan={6}>No hay filas disponibles para esta consulta.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </ModalShell>
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
