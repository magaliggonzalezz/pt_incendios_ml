import { useEffect, useMemo, useState } from "react";
import ModalShell from "../Modals/ModalShell";
import "./ExportModal.css";
import { Eye, Download, FileText, Braces } from "lucide-react";

export default function ExportModal({
  open,
  onClose,
  consultaActiva = null,
  resumenConsulta = null,
  onDownloadExport,
  selectedMlCluster = null,
}) {
  const [selected, setSelected] = useState(null);
  const [previewFormat, setPreviewFormat] = useState(null);

  useEffect(() => {
    if (!open) {
      setSelected(null);
      setPreviewFormat(null);
    }
  }, [open]);

  const rows = useMemo(() => {
    const source = resumenConsulta?.exportRows ?? [];
    if (!selectedMlCluster) return source;
    return source.filter((row) => Number(row.cluster) === Number(selectedMlCluster));
  }, [resumenConsulta, selectedMlCluster]);

  const columns = resumenConsulta?.exportColumns ?? [];
  const previewRows = rows.slice(0, 10);

  const footer = (
    <div className="emFooter">
      Total de registros a exportar: <b>{rows.length}</b>
      {selectedMlCluster ? <span> · Cluster {selectedMlCluster}</span> : null}
    </div>
  );

  const buildPayload = (format) => ({ format, consultaActiva, resumenConsulta });

  return (
    <ModalShell open={open} onClose={onClose} title="Exportar datos" width={560} footer={footer} allowOverlayClose className="emDialog">
      <p className="emSubtitle">Selecciona el formato de los datos correspondientes a la consulta ejecutada.</p>

      <div className="emList">
        <ExportOption
          active={selected === "csv"}
          title="Exportar CSV"
          desc="Tabla de resultados para Excel o análisis tabular"
          leftIcon={<FileText size={20} />}
          onSelect={() => { setSelected("csv"); setPreviewFormat(null); }}
          actions={
            <OptionActions
              enabled={selected === "csv"}
              onPreview={() => setPreviewFormat("csv")}
              onDownload={() => onDownloadExport?.(buildPayload("csv"))}
            />
          }
        />

        <ExportOption
          active={selected === "json"}
          title="Exportar JSON"
          desc="Datos estructurados de la consulta"
          leftIcon={<Braces size={20} />}
          onSelect={() => { setSelected("json"); setPreviewFormat(null); }}
          actions={
            <OptionActions
              enabled={selected === "json"}
              onPreview={() => setPreviewFormat("json")}
              onDownload={() => onDownloadExport?.(buildPayload("json"))}
            />
          }
        />
      </div>

      {previewFormat ? (
        <div className="emPreview">
          <div className="emPreviewTitle">
            Vista previa · {previewFormat.toUpperCase()}
            <span>Primeros {Math.min(10, rows.length)} de {rows.length} registros</span>
          </div>
          {previewFormat === "json" ? (
            <pre className="emJsonPreview">{JSON.stringify(previewRows, null, 2)}</pre>
          ) : (
            <div className="emPreviewTableWrap">
              <table className="emPreviewTable">
                <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                <tbody>
                  {previewRows.map((row, index) => (
                    <tr key={index}>{columns.map((column) => <td key={column}>{row?.[column] ?? ""}</td>)}</tr>
                  ))}
                  {!previewRows.length ? <tr><td colSpan={Math.max(columns.length, 1)}>No hay registros para previsualizar.</td></tr> : null}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
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
        <div className={`emLeftIcon ${active ? "isActive" : ""}`}>{leftIcon}</div>
        <div className="emText">
          <div className="emTitle">{title}</div>
          <div className="emDesc" title={desc}>{desc}</div>
        </div>
      </div>
      <div className="emCardRight">{actions}</div>
    </div>
  );
}

function OptionActions({ enabled, onPreview, onDownload }) {
  return (
    <div className="emActions">
      <IconBtn enabled={enabled} label="Vista previa" onClick={(e) => { e.stopPropagation(); onPreview?.(); }}><Eye size={18} /></IconBtn>
      <IconBtn enabled={enabled} label="Descargar" onClick={(e) => { e.stopPropagation(); onDownload?.(); }}><Download size={18} /></IconBtn>
    </div>
  );
}

function IconBtn({ enabled, label, onClick, children }) {
  return (
    <button type="button" className={`emIconBtn ${enabled ? "isEnabled" : "isDisabled"}`} aria-label={label} title={label} onClick={enabled ? onClick : undefined}>
      {children}
    </button>
  );
}
