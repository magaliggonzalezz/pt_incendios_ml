import { useState } from "react";
import MapView from "../components/Map/MapView";
import LeftPanel from "../components/LeftPanel/LeftPanel";
import RightPanel from "../components/RightPanel/RightPanel";
import Header from "../components/Header/Header";
import Footer from "../components/Footer/Footer";
import {
  INITIAL_ACTIVE_LAYERS,
  INITIAL_SMN_FILTERS,
  buildMockDashboardResults,
} from "../data/dashboardMock";
import "./DashboardPage.css";

const CONSULTA_INICIAL = {
  nivelAgregacion: "",
  tipoPeriodo: "",
  anio: "",
  mes: "",
  anioInicio: "",
  anioFin: "",
  fechaInicio: "",
  fechaFin: "",
  cveEnt: "",
  cveMun: "",
  cvegeo: "",
  estado: "",
  municipio: "",
  cluster: "",
  capasActivas: INITIAL_ACTIVE_LAYERS,
  filtrosSmn: INITIAL_SMN_FILTERS,
};


function isConsultaCompleta(consulta) {
  if (!consulta?.nivelAgregacion || !consulta?.tipoPeriodo) return false;
  if (consulta.nivelAgregacion === "municipio" && !consulta.estado) return false;
  if ((consulta.tipoPeriodo === "anio" || consulta.tipoPeriodo === "anio_mes") && !consulta.anio) return false;
  if (consulta.tipoPeriodo === "anio_mes" && !consulta.mes) return false;
  if (consulta.tipoPeriodo === "rango_anios" && (!consulta.anioInicio || !consulta.anioFin)) return false;
  if (consulta.tipoPeriodo === "rango" && (!consulta.fechaInicio || !consulta.fechaFin)) return false;
  return true;
}
const getConsultaInicial = () => ({
  ...CONSULTA_INICIAL,
  capasActivas: { ...CONSULTA_INICIAL.capasActivas },
  filtrosSmn: { ...CONSULTA_INICIAL.filtrosSmn },
});

export default function DashboardPage() {
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [consultaActiva, setConsultaActiva] = useState(getConsultaInicial);
  const [consultaEjecutada, setConsultaEjecutada] = useState(false);
  const [resumenConsulta, setResumenConsulta] = useState(null);
  const [selectedMlCluster, setSelectedMlCluster] = useState(null);

  const handleConsultaChange = (campo, valor) => {
    setConsultaActiva((prev) => {
      if (campo === "capasActivas") {
        const { capa, activo } = valor;

        return {
          ...prev,
          capasActivas: {
            ...prev.capasActivas,
            [capa]: activo,
          },
        };
      }

      if (campo === "filtrosSmn") {
        return {
          ...prev,
          filtrosSmn: {
            ...prev.filtrosSmn,
            ...valor,
          },
        };
      }

      if (campo === "nivelAgregacion") {
        return {
          ...prev,
          nivelAgregacion: valor,
          estado: "",
          municipio: "",
          cveEnt: "",
          cveMun: "",
          cvegeo: "",
        };
      }

      return {
        ...prev,
        [campo]: valor,
      };
    });
  };

  const handleResetConsulta = () => {
    setConsultaActiva(getConsultaInicial());
    setConsultaEjecutada(false);
    setResumenConsulta(null);
    setSelectedMlCluster(null);
  };

  const handleConsultar = (consultaOverride = null) => {
    const consulta = consultaOverride ?? consultaActiva;
    if (!isConsultaCompleta(consulta)) return;
    setResumenConsulta(buildMockDashboardResults(consulta));
    setConsultaEjecutada(true);
    setSelectedMlCluster(null);
  };

  const handlePreviewExport = ({ format, consultaActiva: consulta, resumenConsulta: resumen }) => {
    console.log("preview export", { format, consulta, resumen, selectedMlCluster });
  };

  const handleDownloadExport = ({ format, consultaActiva: consulta, resumenConsulta: resumen }) => {
    const rows = resumen?.exportRows ?? [];
    const clusterFilteredRows = selectedMlCluster
      ? rows.filter((row) => Number(row.cluster_id) === Number(selectedMlCluster))
      : rows;
    const columns = resumen?.exportColumns ?? [];
    const payloadRows = columns.length
      ? clusterFilteredRows.map((row) => Object.fromEntries(columns.map((column) => [column, row[column] ?? ""])))
      : clusterFilteredRows;
    const text =
      format === "json"
        ? JSON.stringify(payloadRows, null, 2)
        : [
            columns.join(","),
            ...payloadRows.map((row) =>
              columns
                .map((column) => {
                  const value = row[column] ?? "";
                  const str = String(value);
                  return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
                })
                .join(",")
            ),
          ].join("\n");
    const blob = new Blob([text], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `resultado_ml_${consulta?.nivelAgregacion || "entidad"}_${selectedMlCluster ? `cluster_${selectedMlCluster}` : "todos"}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`dash ${rightOpen ? "right-open" : "right-closed"} ${leftOpen ? "left-open" : "left-closed"}`}>
      <MapView
        consultaActiva={consultaActiva}
        onConsultaChange={handleConsultaChange}
        onConsultar={handleConsultar}
        selectedMlCluster={selectedMlCluster}
        leftPanelOpen={leftOpen}
        rightPanelOpen={rightOpen}
      />

      <Header />
      <Footer />

      <LeftPanel
        open={leftOpen}
        onToggle={() => setLeftOpen((v) => !v)}
        consultaActiva={consultaActiva}
        consultaEjecutada={consultaEjecutada}
        onConsultaChange={handleConsultaChange}
        onConsultar={handleConsultar}
        onResetConsulta={handleResetConsulta}
      />
      <RightPanel
        open={rightOpen}
        onToggle={() => setRightOpen((v) => !v)}
        consultaEjecutada={consultaEjecutada}
        consultaActiva={consultaActiva}
        resumenConsulta={resumenConsulta}
        totalRecords={resumenConsulta?.totalRecords ?? 0}
        availableFormats={["csv", "json"]}
        isExporting={false}
        error={null}
        onPreviewExport={handlePreviewExport}
        onDownloadExport={handleDownloadExport}
        selectedMlCluster={selectedMlCluster}
        onSelectedMlClusterChange={setSelectedMlCluster}
      />
    </div>
  );
}
