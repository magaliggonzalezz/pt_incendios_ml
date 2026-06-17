import "./SourcesModal.css";
import ModalShell from "./ModalShell";
import { ExternalLink } from "lucide-react";

const SOURCES = [
  {
    name: "NASA FIRMS",
    subtitle: "Fire Information for Resource Management System",
    url: "https://firms.modaps.eosdis.nasa.gov/",
  },
  {
    name: "CONAFOR",
    subtitle: "Comisión Nacional Forestal",
    url: "https://www.gob.mx/conafor",
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
];

export default function SourcesModal({ open, onClose }) {
  return (
    <ModalShell open={open} onClose={onClose} title="Fuentes de datos" width={550} allowOverlayClose={true} footer={null}>
      <p className="smSubtitle">
        Esta aplicación web integra información de fuentes oficiales para capas observadas, estaciones, capas territoriales y resultados analíticos.
      </p>
      <div className="smList">
        {SOURCES.map((s) => (
          <a
            key={s.name}
            className="smCard"
            href={s.url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Abrir fuente de datos ${s.name} en una pestaña nueva`}
          >
            <div className="smCardText">
              <div className="smCardTitle">{s.name}</div>
              <div className="smCardSub">{s.subtitle}</div>
            </div>

            <ExternalLink className="smExtIcon" aria-hidden="true" />
          </a>
        ))}
      </div>
    </ModalShell>
  );
}
