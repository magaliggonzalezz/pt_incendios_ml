import { useState } from "react";
import "./RightPanel.css";
import { MapPin, Flame, Trees, BarChart3, Download } from "lucide-react";
import ExportModal from "../Modals/ExportModal";
import ChartsModal from "../Modals/ChartsModal";

export default function RightPanel({ open, onToggle, totalRecords = 0 }) {
    const [openExport, setOpenExport] = useState(false);
    const [openCharts, setOpenCharts] = useState(false);

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
            onPreview={({ format }) => {
                // después lo conectamos al PreviewModal real
                console.log("preview", format);
            }}
            onDownload={({ format }) => {
                // después conectamos CSV/JSON real
                console.log("download", format);
            }}
        />

        <ChartsModal open={openCharts} onClose={() => setOpenCharts(false)} />

        </>
    );
}