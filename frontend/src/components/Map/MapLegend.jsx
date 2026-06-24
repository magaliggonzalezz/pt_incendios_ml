import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getActiveLegendSections } from "../../data/dashboardMock";
import "./MapLegend.css";

export default function MapLegend({ consultaActiva = null, rightPanelOpen = false }) {
  const [collapsed, setCollapsed] = useState(false);
  const sections = useMemo(() => getActiveLegendSections(consultaActiva), [consultaActiva]);

  if (!sections.length) return null;

  return (
    <aside
      className={`mapLegend ${rightPanelOpen ? "rightPanelOpen" : ""} ${collapsed ? "isCollapsed" : ""}`}
      aria-label="Leyenda de capas activas"
    >
      <div className="mapLegendHeader">
        <span>Leyenda de capas</span>
        <button
          type="button"
          className="mapLegendToggle"
          aria-label={collapsed ? "Mostrar leyenda de capas" : "Ocultar leyenda de capas"}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {!collapsed && (
        <div className="mapLegendBody">
          {sections.map((section) => (
            <section className="mapLegendSection" key={section.id}>
              <div className="mapLegendSectionTitle">{section.title}</div>
              <p>{section.description}</p>
              <div className="mapLegendItems">
                {section.items.map((item) => (
                  <div className="mapLegendItem" key={`${section.id}-${item.label}`}>
                    <Symbol item={item} />
                    <div>
                      <strong>{item.label}</strong>
                      {item.detail && <span>{item.detail}</span>}
                    </div>
                  </div>
                ))}
              </div>
              {section.note && <em>{section.note}</em>}
            </section>
          ))}
          <div className="mapLegendFooter">Activa o desactiva capas desde el panel izquierdo.</div>
        </div>
      )}
    </aside>
  );
}

function Symbol({ item }) {
  const style = { "--symbol-color": item.color };
  return <span className={`mapLegendSymbol ${item.symbol}`} style={style} aria-hidden="true" />;
}
