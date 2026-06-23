import { useState } from "react";
import "./RightPanel.css";
import { MapPin, Flame, Trees, BarChart3, Download } from "lucide-react";
import ExportModal from "../Modals/ExportModal";
import ChartsModal from "../Modals/ChartsModal";
import { obtenerAnalisisML } from "../../services/analisisML.service";
import { exportarCSV, exportarJSON } from "../../services/exportacion.service";

export default function RightPanel({ open, onToggle, totalRecords = 0 }) {
  const [openExport, setOpenExport] = useState(false);
  const [openCharts, setOpenCharts] = useState(false);

  async function obtenerDatosExportacion() {
    const data = await obtenerAnalisisML();
    return data || [];
  }

  async function handlePreview(format) {
    try {
      const datos = await obtenerDatosExportacion();

      console.log("Vista previa:", {
        formato: format,
        total: datos.length,
        datos
      });

      alert(`Vista previa ${format.toUpperCase()} generada en consola.`);
    } catch (error) {
      console.error(error);
      alert("Error al obtener datos para vista previa");
    }
  }

  async function handleDownload(format) {
    try {
      const datos = await obtenerDatosExportacion();

      const payload = {
        nombre: "resultados_analisis_ml",
        datos
      };

      const respuesta =
        format === "csv"
          ? await exportarCSV(payload)
          : await exportarJSON(payload);

    if (respuesta.archivo) {
  const url = `http://localhost:3004/api/exportacion/descargar/${respuesta.archivo}`;
  const link = document.createElement("a");

  link.href = url;
  link.download = respuesta.archivo;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

alert(respuesta.mensaje || "Exportación realizada correctamente");
    } catch (error) {
      console.error(error);
      alert("Error al exportar datos");
    }
  }

  return (
    <>
      <aside className={`rightPanel ${open ? "open" : "closed"}`}>
        <button className="toggleBtn" onClick={onToggle} aria-label="Toggle right panel">
          {open ? "⟩" : "⟨"}
        </button>

        <div className="kpiCard">
          <div className="kpiHeader">
            <span className="kpiHeaderIcon" aria-hidden="true">
              <MapPin size={18} />
            </span>
            México
          </div>

          <div className="kpiBody">
            <div className="kpiBox">
              <div className="kpiTopRow">
                <span className="kpiIcon" aria-hidden="true">
                  <Flame size={16} />
                </span>
                <div className="kpiLabel">Incendios detectados</div>
              </div>
              <div className="kpiValue">331</div>
            </div>

            <div className="kpiBox">
              <div className="kpiTopRow">
                <span className="kpiIcon" aria-hidden="true">
                  <Trees size={16} />
                </span>
                <div className="kpiLabel">Hectáreas afectadas</div>
              </div>
              <div className="kpiValue">87,279</div>
            </div>
          </div>

          <div className="kpiActions">
            <button className="primaryBtn" onClick={() => setOpenCharts(true)}>
              <BarChart3 size={18} />
              Ver gráficas
            </button>

            <button className="secondaryBtn" onClick={() => setOpenExport(true)}>
              <Download size={18} />
              Exportar datos
            </button>
          </div>
        </div>
      </aside>

      <ExportModal
        open={openExport}
        onClose={() => setOpenExport(false)}
        totalRecords={totalRecords}
        onPreview={({ format }) => handlePreview(format)}
        onDownload={({ format }) => handleDownload(format)}
      />

      <ChartsModal open={openCharts} onClose={() => setOpenCharts(false)} />
    </>
  );
}