import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import "./MapLegend.css";

export default function MapLegend({ resumenConsulta = null, rightPanelOpen = false, selectedMlCluster = null }) {
  const [collapsed, setCollapsed] = useState(false);

  const items = useMemo(() => {
    const catalogRows = resumenConsulta?.catalogRows ?? [];
    const rows = resumenConsulta?.rows ?? [];
    if (!catalogRows.length || !rows.length) return [];

    const presentes = new Set(rows.map((row) => Number(row.cluster)));

    return catalogRows
      .filter((cluster) => presentes.has(Number(cluster.cluster_id)))
      .sort((a, b) => Number(a.prioridad_visual_app ?? 999) - Number(b.prioridad_visual_app ?? 999))
      .map((cluster) => ({
        id: Number(cluster.cluster_id),
        label: `Cluster ${cluster.cluster_id}`,
        detail: cluster.estado_app || cluster.etiqueta_final || "Sin descripción",
        color: cluster.color_sugerido_app || "#64748B",
      }));
  }, [resumenConsulta]);

  if (!items.length) return null;

  return (
    <aside
      className={`mapLegend ${rightPanelOpen ? "rightPanelOpen" : ""} ${collapsed ? "isCollapsed" : ""}`}
      aria-label="Leyenda de resultados ML"
    >
      <div className="mapLegendHeader">
        <span>Leyenda ML</span>
        <button
          type="button"
          className="mapLegendToggle"
          aria-label={collapsed ? "Mostrar leyenda ML" : "Ocultar leyenda ML"}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {!collapsed && (
        <div className="mapLegendBody">
          <section className="mapLegendSection">
            <div className="mapLegendSectionTitle">Patrones presentes en la consulta</div>
            <p>Los polígonos se colorean con el catálogo real de clusters del modelo.</p>
            <div className="mapLegendItems">
              {items.map((item) => {
                const dimmed = selectedMlCluster !== null && selectedMlCluster !== "" && Number(selectedMlCluster) !== item.id;
                return (
                  <div
                    className="mapLegendItem"
                    key={item.id}
                    style={dimmed ? { opacity: 0.35 } : undefined}
                  >
                    <span
                      className="mapLegendSymbol fill"
                      style={{ "--symbol-color": item.color }}
                      aria-hidden="true"
                    />
                    <div>
                      <strong>{item.label}</strong>
                      <span>{item.detail}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
          <div className="mapLegendFooter">Geometría administrativa: INEGI. Color: resultado ML de la consulta ejecutada.</div>
        </div>
      )}
    </aside>
  );
}
