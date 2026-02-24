import "./RightPanel.css";

export default function RightPanel({ open, onToggle }) {
    return (
        <aside className={`rightPanel ${open ? "open" : "closed"}`}>
            <button className="toggleBtn" onClick={onToggle} aria-label="Toggle right panel">
                {open ? "⟩" : "⟨"}
            </button>

            <div className="kpiCard">
                <div className="kpiHeader">
                    <span className="kpiHeaderIcon" aria-hidden="true">📍</span>
                    México
                </div>

                <div className="kpiBody">
                    <div className="kpiBox">
                        <div className="kpiLabel">Incendios detectados</div>
                            <div className="kpiValue">331</div>
                    </div>

                    <div className="kpiBox">
                        <div className="kpiLabel">Hectáreas afectadas</div>
                            <div className="kpiValue">87,279</div>
                    </div>
                </div>

                <div className="kpiActions">
                    <button className="primaryBtn">Exportar datos</button>
                    <button className="secondaryBtn">Ver gráficas</button>
                </div>
            </div>
        </aside>
    );
}