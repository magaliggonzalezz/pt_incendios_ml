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
              <p className="legendIntro"><strong>Atributo de confianza.</strong> El color representa la categoría de confianza de cada detección FIRMS original.</p>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsLow"/><div><strong>Confianza baja</strong><span>Detección FIRMS original</span></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsNominal"/><div><strong>Confianza nominal</strong><span>Detección FIRMS original</span></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsHigh"/><div><strong>Confianza alta</strong><span>Detección FIRMS original</span></div></div>
              </div>
              <p className="legendNote"><strong>Archive:</strong> se muestran únicamente datos del archivo histórico consolidado de FIRMS. La aplicación no utiliza productos NRT ni RT.</p>
              <div className="legendListBlock">
                <strong>Tipo de detección</strong>
                <ul>
                  <li><b>0</b> · Incendio de vegetación presunto</li>
                  <li><b>1</b> · Volcán activo</li>
                  <li><b>2</b> · Otra fuente terrestre estática</li>
                  <li><b>3</b> · Detección offshore</li>
                </ul>
              </div>
            </section>
          ) : null}

          {showConafor ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">CONAFOR</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot conafor"/><div><strong>Incendio registrado</strong><span>Registro original; el tamaño visual depende de la superficie cuando existe.</span></div></div>
              </div>
            </section>
          ) : null}

          {showSmn ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">SMN-CONAGUA</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol station"/><div><strong>Estación meteorológica</strong><span>Registro original del inventario de estaciones.</span></div></div>
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
              <p className="legendNote">Los colores de estas capas son una simbología web definida por la aplicación; no se presentan como la simbología cartográfica oficial de INEGI. Las geometrías pueden simplificarse para visualización web sin sustituir sus features por registros sintéticos.</p>
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
