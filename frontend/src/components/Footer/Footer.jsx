import { useState } from "react";
import "./Footer.css";
import SourcesModal from "../Modals/SourcesModal";
import { Database } from "lucide-react";

export default function Footer() {
    const [openSources, setOpenSources] = useState(false);

    return (
        <>
        <footer className="footerBar">
            <button
            className="footerBtn"
            type="button"
            onClick={() => setOpenSources(true)}
            aria-label="Ver fuentes de datos"
            > 
                <span className="footerBtnText">Ver fuentes de datos</span>
                <Database className="footerBtnIcon" aria-hidden="true" />
            </button>
        </footer>
        <SourcesModal open={openSources} onClose={() => setOpenSources(false)} />
        </>
    );
}