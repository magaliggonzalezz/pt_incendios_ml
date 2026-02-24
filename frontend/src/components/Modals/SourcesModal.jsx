// src/components/Modals/SourcesModal/SourcesModal.jsx
import "./SourcesModal.css";
import { X, ExternalLink } from "lucide-react";

const SOURCES = [
    {
        name: "NASA FIRMS",
        subtitle: "Fire Information for Resource Management System",
        url: "https://firms.modaps.eosdis.nasa.gov/",
    },
    {
        name: "SMN-CONAGUA",
        subtitle: "Servicio Meteorológico Nacional - Comisión Nacional del Agua",
        url: "https://smn.conagua.gob.mx/",
    },
    {
        name: "INEGI",
        subtitle: "Instituto Nacional de Estadística y Geografía",
        url: "https://www.inegi.org.mx/",
    },
    {
        name: "CONABIO",
        subtitle: "Comisión Nacional para el Conocimiento y Uso de la Biodiversidad",
        url: "http://www.conabio.gob.mx/",
    },
    {
        name: "CONAFOR",
        subtitle: "Comisión Nacional Forestal",
        url: "https://www.gob.mx/conafor",
    },
];

export default function SourcesModal({ open, onClose }) {
    if (!open) return null;

    const onBackdropMouseDown = (e) => {
        // Cierra solo si das click en el backdrop
        if (e.target === e.currentTarget) onClose?.();
    };

    return (
        <div className="smBackdrop" onMouseDown={onBackdropMouseDown}>
            <div className="smModal" role="dialog" aria-modal="true" aria-label="Fuentes de Datos">
                <div className="smHeader">
                    <div className="smHeaderText">
                        <div className="smTitleRow">
                            <h2 className="smTitle">Fuentes de Datos</h2>
                        </div>
                        <p className="smSubtitle">
                            Esta aplicación web integra información de múltiples fuentes oficiales listadas a continuación:
                        </p>
                    </div>
                    <button className="smCloseBtn" type="button" onClick={onClose} aria-label="Cerrar">
                        <X className="smCloseIcon" aria-hidden="true" />
                    </button>
                </div>

                <div className="smList">
                {SOURCES.map((s) => (
                    <a
                    key={s.name}
                    className="smCard"
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    >
                    <div className="smCardText">
                        <div className="smCardTitle">{s.name}</div>
                        <div className="smCardSub">{s.subtitle}</div>
                    </div>

                    <ExternalLink className="smExtIcon" aria-hidden="true" />
                    </a>
                ))}
                </div>
            </div>
        </div>
    );
}