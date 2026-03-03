import { useMemo, useState } from "react";
import ModalShell from "../Modals/ModalShell";
import "./ExportModal.css";
import { Eye, Download, FileText, Braces } from "lucide-react";

export default function ExportModal({
    open,
    onClose,
    totalRecords = 0,
    onPreview,
    onDownload,
}) {
    const [selected, setSelected] = useState(null);

    const footer = useMemo(
        () => (
            <div className="emFooter">
                Total de registros a exportar: <b>{totalRecords}</b>
            </div>
        ),
        [totalRecords]
    );

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
                Seleccione el formato de exportación para descargar los datos de incendios.
            </p>

            <div className="emList">
                <ExportOption
                active={selected === "csv"}
                title="Exportar CSV"
                desc="Tabla de datos en formato CSV para Excel o análisis"
                leftIcon={<FileText size={20} />}
                onSelect={() => setSelected("csv")}
                actions={
                    <OptionActions
                    enabled={selected === "csv"}
                    onPreview={() => onPreview?.({ format: "csv" })}
                    onDownload={() => onDownload?.({ format: "csv" })}
                    />
                }
                />

                <ExportOption
                active={selected === "json"}
                title="Exportar JSON"
                desc="Datos estructurados para desarrollo web o APIs"
                leftIcon={<Braces size={20} />}
                onSelect={() => setSelected("json")}
                actions={
                    <OptionActions
                    enabled={selected === "json"}
                    onPreview={() => onPreview?.({ format: "json" })}
                    onDownload={() => onDownload?.({ format: "json" })}
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