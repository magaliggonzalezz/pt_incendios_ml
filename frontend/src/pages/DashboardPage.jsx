import { useEffect, useRef, useState } from "react";
import MapView from "../components/Map/MapView";
import LeftPanel from "../components/LeftPanel/LeftPanel";
import RightPanel from "../components/RightPanel/RightPanel";
import Header from "../components/Header/Header";
import Footer from "../components/Footer/Footer";
import { INITIAL_ACTIVE_LAYERS, INITIAL_SMN_FILTERS } from "../data/dashboardMock";
import { buildRealDashboardResults } from "../data/dashboardRealData";
import { obtenerClusters, obtenerEstados, obtenerMunicipios } from "../services/catalogos.service";
import {
  obtenerResultadosEstadoAnio,
  obtenerResultadosEstadoMes,
  obtenerResultadosMunicipioAnio,
  obtenerResultadosMunicipioMes,
} from "../services/resultados.service";
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
  if (consulta.nivelAgregacion === "municipio" && !consulta.cveEnt) return false;
  if (consulta.tipoPeriodo === "anio") return Boolean(consulta.anio);
  if (consulta.tipoPeriodo === "anio_mes") return Boolean(consulta.anio && consulta.mes);
  if (consulta.tipoPeriodo === "comparar_anios") {
    return Boolean(consulta.anioInicio && consulta.anioFin && consulta.anioInicio !== consulta.anioFin);
  }
  // Los controles de fecha ya existen en el frontend, pero la consulta diaria se
  // habilitará cuando las rutas día estén completas (municipio-día sigue diferido).
  return false;
}

const getConsultaInicial = () => ({
  ...CONSULTA_INICIAL,
  capasActivas: { ...CONSULTA_INICIAL.capasActivas },
  filtrosSmn: { ...CONSULTA_INICIAL.filtrosSmn },
});

const snapshotConsulta = (consulta) => ({
  ...consulta,
  capasActivas: { ...(consulta.capasActivas || {}) },
  filtrosSmn: { ...(consulta.filtrosSmn || {}) },
});

export default function DashboardPage() {
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [consultaActiva, setConsultaActiva] = useState(getConsultaInicial);
  const [consultaEjecutada, setConsultaEjecutada] = useState(false);
  const [ultimaConsultaEjecutada, setUltimaConsultaEjecutada] = useState(null);
  const [resumenConsulta, setResumenConsulta] = useState(null);
  const [selectedMlCluster, setSelectedMlCluster] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [estados, setEstados] = useState([]);
  const [municipios, setMunicipios] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const queryRunRef = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([obtenerClusters(), obtenerEstados()])
      .then(([clusterRows, estadoRows]) => {
        if (!active) return;
        setClusters(clusterRows);
        setEstados(estadoRows);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    if (!consultaActiva.cveEnt) {
      setMunicipios([]);
      return () => { active = false; };
    }
    obtenerMunicipios(consultaActiva.cveEnt)
      .then((rows) => {
        if (active) setMunicipios(rows);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => { active = false; };
  }, [consultaActiva.cveEnt]);

  const invalidateExecutedQuery = () => {
    setConsultaEjecutada(false);
    setUltimaConsultaEjecutada(null);
    setResumenConsulta(null);
    setSelectedMlCluster(null);
  };

  const cancelPendingQuery = () => {
    queryRunRef.current += 1;
    setIsLoading(false);
  };

  const invalidateForQueryChange = () => {
    cancelPendingQuery();
    invalidateExecutedQuery();
    setError(null);
  };

  const handleConsultaChange = (campo, valor) => {
    if (campo === "consultaPatch") {
      invalidateForQueryChange();
      setConsultaActiva((prev) => ({ ...prev, ...(valor || {}) }));
      return;
    }

    const changesOnlyVisualization = campo === "capasActivas" || campo === "filtrosSmn";
    if (!changesOnlyVisualization) invalidateForQueryChange();

    setConsultaActiva((prev) => {
      if (campo === "capasActivas") {
        const { capa, activo } = valor;
        return { ...prev, capasActivas: { ...prev.capasActivas, [capa]: activo } };
      }
      if (campo === "filtrosSmn") {
        return { ...prev, filtrosSmn: { ...prev.filtrosSmn, ...valor } };
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
      return { ...prev, [campo]: valor };
    });
  };

  const handleResetConsulta = () => {
    cancelPendingQuery();
    setConsultaActiva(getConsultaInicial());
    invalidateExecutedQuery();
    setError(null);
  };

  const fetchAnnualRows = async (consulta, anio) => {
    if (consulta.nivelAgregacion === "entidad") {
      let rows = await obtenerResultadosEstadoAnio(anio);
      if (consulta.cveEnt) rows = rows.filter((row) => row.cve_ent === consulta.cveEnt);
      return rows;
    }
    return obtenerResultadosMunicipioAnio({ anio, cveEnt: consulta.cveEnt, cvegeo: consulta.cvegeo });
  };

  const handleConsultar = async (consultaOverride = null) => {
    const consulta = consultaOverride ?? consultaActiva;
    if (!isConsultaCompleta(consulta)) return;

    const runId = queryRunRef.current + 1;
    queryRunRef.current = runId;
    setIsLoading(true);
    setError(null);

    try {
      let rows;

      if (consulta.tipoPeriodo === "comparar_anios") {
        const [rowsA, rowsB] = await Promise.all([
          fetchAnnualRows(consulta, consulta.anioInicio),
          fetchAnnualRows(consulta, consulta.anioFin),
        ]);
        rows = [
          ...rowsA.map((row) => ({ ...row, anio_comparacion: Number(consulta.anioInicio) })),
          ...rowsB.map((row) => ({ ...row, anio_comparacion: Number(consulta.anioFin) })),
        ];
      } else if (consulta.nivelAgregacion === "entidad") {
        rows = consulta.tipoPeriodo === "anio_mes"
          ? await obtenerResultadosEstadoMes(consulta.anio, Number(consulta.mes))
          : await obtenerResultadosEstadoAnio(consulta.anio);
        if (consulta.cveEnt) rows = rows.filter((row) => row.cve_ent === consulta.cveEnt);
      } else {
        const params = { anio: consulta.anio, cveEnt: consulta.cveEnt, cvegeo: consulta.cvegeo };
        rows = consulta.tipoPeriodo === "anio_mes"
          ? await obtenerResultadosMunicipioMes({ ...params, mes: Number(consulta.mes) })
          : await obtenerResultadosMunicipioAnio(params);
      }

      if (runId !== queryRunRef.current) return;

      const resumen = buildRealDashboardResults({ consulta, rows, clusters, estados, municipios });
      if (runId !== queryRunRef.current) return;

      setResumenConsulta(resumen);
      setUltimaConsultaEjecutada(snapshotConsulta(consulta));
      setConsultaEjecutada(true);
      setSelectedMlCluster(null);
    } catch (err) {
      if (runId !== queryRunRef.current) return;
      invalidateExecutedQuery();
      setError(err.message);
    } finally {
      if (runId === queryRunRef.current) setIsLoading(false);
    }
  };

  const handlePreviewExport = ({ format, consultaActiva: consulta, resumenConsulta: resumen }) => {
    console.log("preview export", { format, consulta, resumen, selectedMlCluster });
  };

  const handleDownloadExport = ({ format, consultaActiva: consulta, resumenConsulta: resumen }) => {
    const rows = resumen?.exportRows ?? [];
    const clusterFilteredRows = selectedMlCluster
      ? rows.filter((row) => Number(row.cluster) === Number(selectedMlCluster))
      : rows;
    const columns = resumen?.exportColumns ?? [];
    const payloadRows = columns.length
      ? clusterFilteredRows.map((row) => Object.fromEntries(columns.map((column) => [column, row[column] ?? ""])))
      : clusterFilteredRows;
    const text = format === "json"
      ? JSON.stringify(payloadRows, null, 2)
      : [
          columns.join(","),
          ...payloadRows.map((row) => columns.map((column) => {
            const value = row[column] ?? "";
            const str = String(value);
            return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
          }).join(",")),
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
        consultaEjecutada={ultimaConsultaEjecutada}
        resumenConsulta={resumenConsulta}
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
        onToggle={() => setLeftOpen((value) => !value)}
        consultaActiva={consultaActiva}
        consultaEjecutada={consultaEjecutada}
        onConsultaChange={handleConsultaChange}
        onConsultar={handleConsultar}
        onResetConsulta={handleResetConsulta}
        estados={estados}
        municipios={municipios}
        isLoading={isLoading}
      />
      <RightPanel
        open={rightOpen}
        onToggle={() => setRightOpen((value) => !value)}
        consultaEjecutada={consultaEjecutada}
        consultaActiva={consultaActiva}
        consultaResultado={ultimaConsultaEjecutada}
        resumenConsulta={resumenConsulta}
        totalRecords={resumenConsulta?.totalRecords ?? 0}
        availableFormats={["csv", "json"]}
        isExporting={false}
        isLoading={isLoading}
        error={error}
        onPreviewExport={handlePreviewExport}
        onDownloadExport={handleDownloadExport}
        selectedMlCluster={selectedMlCluster}
        onSelectedMlClusterChange={setSelectedMlCluster}
      />
    </div>
  );
}
