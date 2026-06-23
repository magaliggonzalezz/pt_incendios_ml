import { useEffect, useMemo, useState } from "react";
import ModalShell from "../Modals/ModalShell";
import "./ExportModal.css";
import { Eye, Download, FileText, Braces } from "lucide-react";

import { obtenerAnalisisML } from "../../services/analisisML.service";
import { exportarCSV, exportarJSON } from "../../services/exportacion.service";

export default function ExportModal({
  open,
  onClose,
  totalRecords = 0,
  onPreview,
  onDownload,
}) {
  const [selected, setSelected] = useState(null);
  const [analisisML, setAnalisisML] = useState([]);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function cargarDatos() {
      try {
        const data = await obtenerAnalisisML();
        setAnalisisML(data || []);
      } catch (err) {
        setError("Error al cargar resultados ML");
      }
    }

    if (open) {
      cargarDatos();
    }
  }, [open]);

  const totalExportar = analisisML.length || totalRecords;

  const footer = useMemo(
    () => (
      <div className="emFooter">
        Total de registros a exportar: <b>{totalExportar}</b>
      </div>
    ),
    [totalExportar]
  );

  async function handlePreview(format) {
    const datos = analisisML;

    console.log("Vista previa:", {
      formato: format,
      total: datos.length,
      datos,
    });

    onPreview?.({ format, datos });
  }

  async function handleDownload(format) {
    try {
      setMensaje("");
      setError("");

      const payload = {
        nombre: "resultados_analisis_ml",
        datos: analisisML,
      };

      const respuesta =
        format === "csv"
          ? await exportarCSV(payload)
          : await exportarJSON(payload);

      setMensaje(respuesta.mensaje || "Exportación generada correctamente");

      onDownload?.({ format, respuesta });
    } catch (err) {
      setError(err.message || "Error al exportar datos");
    }
  }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Exportar datos"
      width={448}
      footer={footer}
      allowOverlayClose={true}
    >
      <p className="emSubtitle">
        Seleccione el formato de exportación para descargar los resultados del análisis ML.
      </p>

      {mensaje && <p style={{ color: "green" }}>{mensaje}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div className="emList">
        <ExportOption
          active={selected === "csv"}
          title="Exportar CSV"
          desc="Tabla de resultados en formato CSV para Excel o análisis"
          leftIcon={<FileText size={20} />}
          onSelect={() => setSelected("csv")}
          actions={
            <OptionActions
              enabled={selected === "csv"}
              onPreview={() => handlePreview("csv")}
              onDownload={() => handleDownload("csv")}
            />
          }
        />

        <ExportOption
          active={selected === "json"}
          title="Exportar JSON"
          desc="Resultados estructurados para desarrollo web o APIs"
          leftIcon={<Braces size={20} />}
          onSelect={() => setSelected("json")}
          actions={
            <OptionActions
              enabled={selected === "json"}
              onPreview={() => handlePreview("json")}
              onDownload={() => handleDownload("json")}
            />
          }
        />
      </div>
    </ModalShell>
  );
}

function ExportOption({ active, title, desc, leftIcon, onSelect, actions }) {
  return (
    <div
      className={`emCard ${active ? "isActive" : ""}`}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.();
        }
      }}
    >
      <div className="emCardLeft">
        <div className={`emLeftIcon ${active ? "isActive" : ""}`}>
          {leftIcon}
        </div>

        <div className="emText">
          <div className="emTitle">{title}</div>
          <div className="emDesc" title={desc}>
            {desc}
          </div>
        </div>
      </div>

      <div className="emCardRight">{actions}</div>
    </div>
  );
}

function OptionActions({ enabled, onPreview, onDownload }) {
  return (
    <div className="emActions">
      <IconBtn
        enabled={enabled}
        label="Vista previa"
        onClick={(e) => {
          e.stopPropagation();
          onPreview?.();
        }}
      >
        <Eye size={18} />
      </IconBtn>

      <IconBtn
        enabled={enabled}
        label="Descargar"
        onClick={(e) => {
          e.stopPropagation();
          onDownload?.();
        }}
      >
        <Download size={18} />
      </IconBtn>
    </div>
  );
}

function IconBtn({ enabled, label, onClick, children }) {
  return (
    <button
      type="button"
      className={`emIconBtn ${enabled ? "isEnabled" : "isDisabled"}`}
      aria-label={label}
      title={label}
      onClick={enabled ? onClick : undefined}
    >
      {children}
    </button>
  );
}