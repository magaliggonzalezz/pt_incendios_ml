import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import "./MapLegend.css";

export default function MapLegend({
  resumenConsulta = null,
  rightPanelOpen = false,
  selectedMlCluster = null,
  capasActivas = {},
}) {
  const [collapsed, setCollapsed] = useState(true);

  const mlItems = useMemo(() => {
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

  const showFirms = Boolean(capasActivas.puntosCalorFirms);
  const showConafor = Boolean(capasActivas.incendiosConafor);
  const showSmn = Boolean(capasActivas.estacionesSmn);
  const showInegi = Boolean(
    capasActivas.limitesEstatales ||
    capasActivas.limitesMunicipales ||
    capasActivas.fisiografiaInegi ||
    capasActivas.edafologiaInegi ||
    capasActivas.usoSueloVegetacionInegi ||
    capasActivas.corrientesAguaInegi
  );
  const hasSymbology = showFirms || showConafor || showSmn || showInegi || mlItems.length > 0;

  useEffect(() => {
    if (hasSymbology) setCollapsed(false);
  }, [hasSymbology]);

  if (!hasSymbology) return null;

  return (
    <aside className={`mapLegend ${rightPanelOpen ? "rightPanelOpen" : ""} ${collapsed ? "isCollapsed" : ""}`} aria-label="Simbología del mapa">
      <div className="mapLegendHeader">
        <span>Simbología</span>
        <button type="button" className="mapLegendToggle" aria-label={collapsed ? "Mostrar simbología" : "Ocultar simbología"} aria-expanded={!collapsed} onClick={() => setCollapsed((value) => !value)}>
          {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {!collapsed ? (
        <div className="mapLegendBody">
          {showFirms ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">FIRMS</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsLow"/><div><strong>Confianza baja</strong><span>Detección FIRMS original</span></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsNominal"/><div><strong>Confianza nominal</strong><span>Detección FIRMS original</span></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsHigh"/><div><strong>Confianza alta</strong><span>Detección FIRMS original</span></div></div>
              </div>
              <p className="legendNote"><strong>Archive:</strong> se muestran únicamente datos del archivo histórico consolidado de FIRMS. No se utilizan productos NRT ni RT.</p>
              <p className="legendNote"><strong>Tipo:</strong> 0 incendio de vegetación presunto · 1 volcán activo · 2 otra fuente terrestre estática · 3 detección offshore.</p>
            </section>
          ) : null}

          {(showConafor || showSmn) ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">CONAFOR y SMN-CONAGUA</div>
              <div className="mapLegendItems">
                {showConafor ? <div className="mapLegendItem"><span className="mapLegendSymbol dot conafor"/><div><strong>Incendio CONAFOR</strong><span>Registro original; tamaño según superficie cuando existe.</span></div></div> : null}
                {showSmn ? <div className="mapLegendItem"><span className="mapLegendSymbol station"/><div><strong>Estación meteorológica</strong><span>Inventario SMN-CONAGUA filtrado por territorio, período y situación operativa.</span></div></div> : null}
              </div>
            </section>
          ) : null}

          {showInegi ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">INEGI</div>
              <div className="mapLegendItems">
                {capasActivas.fisiografiaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line physiography"/><div><strong>Provincias fisiográficas</strong></div></div> : null}
                {capasActivas.edafologiaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line soil"/><div><strong>Edafología</strong></div></div> : null}
                {capasActivas.usoSueloVegetacionInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line landUse"/><div><strong>Uso de suelo y vegetación</strong></div></div> : null}
                {capasActivas.corrientesAguaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line water"/><div><strong>Corrientes de agua</strong></div></div> : null}
                {capasActivas.limitesEstatales ? <div className="mapLegendItem"><span className="mapLegendSymbol line boundary"/><div><strong>Límite estatal</strong><span>El color se adapta al mapa base.</span></div></div> : null}
                {capasActivas.limitesMunicipales ? <div className="mapLegendItem"><span className="mapLegendSymbol line boundaryMunicipal"/><div><strong>Límite municipal</strong><span>El color se adapta al mapa base.</span></div></div> : null}
              </div>
              <p className="legendNote">Las geometrías temáticas pueden simplificarse para visualización web; no se crean registros sintéticos ni se sustituyen los atributos originales.</p>
            </section>
          ) : null}

          {mlItems.length ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">Resultados ML presentes</div>
              <div className="mapLegendItems">
                {mlItems.map((item) => {
                  const dimmed = selectedMlCluster !== null && selectedMlCluster !== "" && Number(selectedMlCluster) !== item.id;
                  return (
                    <div className="mapLegendItem" key={item.id} style={dimmed ? { opacity: 0.35 } : undefined}>
                      <span className="mapLegendSymbol fill" style={{ "--symbol-color": item.color }} aria-hidden="true" />
                      <div><strong>{item.label}</strong><span>{item.detail}</span></div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}

          <div className="mapLegendFooter">La simbología explica la representación del mapa; “Fuentes de datos” queda reservado para atribución y enlaces de origen.</div>
        </div>
      ) : null}
    </aside>
  );
}
