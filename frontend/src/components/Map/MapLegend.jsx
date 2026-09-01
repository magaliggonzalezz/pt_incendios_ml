import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import "./MapLegend.css";

function CategoryLegend({ title, data }) {
  const items = data?.items || [];
  const total = Number(data?.total || 0);
  if (!items.length) return null;
  return (
    <div className="thematicCategoryBlock">
      <strong>{title}</strong>
      <div className="thematicCategoryList">
        {items.map((item) => (
          <div className="thematicCategoryItem" key={`${title}-${item.label}`}>
            <span className="thematicSwatch" style={{ "--category-color": item.color }} aria-hidden="true" />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      {total > items.length ? <small>+ {total - items.length} categorías adicionales visibles</small> : null}
    </div>
  );
}

export default function MapLegend({
  resumenConsulta = null,
  rightPanelOpen = false,
  selectedMlCluster = null,
  capasActivas = {},
  thematicLegend = {},
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

  useEffect(() => {
    const collapseForPopup = () => setCollapsed(true);
    window.addEventListener("map:feature-popup-open", collapseForPopup);
    return () => window.removeEventListener("map:feature-popup-open", collapseForPopup);
  }, []);

  if (!hasSymbology) return null;

  const toggleLegend = () => {
    setCollapsed((value) => {
      const next = !value;
      if (!next) window.dispatchEvent(new CustomEvent("map:legend-open"));
      return next;
    });
  };

  return (
    <aside className={`mapLegend ${rightPanelOpen ? "rightPanelOpen" : ""} ${collapsed ? "isCollapsed" : ""}`} aria-label="Simbología del mapa">
      {collapsed ? (
        <button
          type="button"
          className="mapLegendCollapsedButton"
          aria-label="Mostrar simbología"
          aria-expanded="false"
          onClick={toggleLegend}
        >
          <span>Simbología</span>
          <ChevronRight size={17} strokeWidth={2.2} aria-hidden="true" />
        </button>
      ) : (
        <div className="mapLegendHeader">
          <span>Simbología</span>
          <button type="button" className="mapLegendToggle" aria-label="Ocultar simbología" aria-expanded="true" onClick={toggleLegend}>
            <ChevronDown size={15} />
          </button>
        </div>
      )}

      {!collapsed ? (
        <div className="mapLegendBody">
          {showFirms ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">FIRMS</div>
              <p className="legendLead">Representa <strong>anomalías térmicas detectadas por satélite</strong>; una detección no equivale por sí sola a un incendio confirmado.</p>
              <div className="legendSubTitle">Representación del punto</div>
              <ul className="legendDefinitionList">
                <li><strong>Color:</strong> categoría del atributo de confianza.</li>
                <li><strong>Tamaño:</strong> FRP; mayor potencia radiativa, mayor tamaño visual.</li>
                <li><strong>Borde:</strong> claro para detección diurna y oscuro para nocturna.</li>
              </ul>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsLow"/><div><strong>Confianza baja</strong></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsNominal"/><div><strong>Confianza nominal</strong></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsHigh"/><div><strong>Confianza alta</strong></div></div>
              </div>
              <div className="legendNoteBlock">
                <strong>Producto utilizado: Archive</strong>
                <span>Archivo histórico consolidado empleado por el proyecto; no se utilizan productos NRT ni RT.</span>
              </div>
              <div className="legendListBlock">
                <strong>Tipo de detección</strong>
                <ul>
                  <li><b>0</b> · Incendio de vegetación presunto</li>
                  <li><b>1</b> · Volcán activo</li>
                  <li><b>2</b> · Otra fuente terrestre estática</li>
                  <li><b>3</b> · Detección offshore</li>
                </ul>
              </div>
              <div className="legendListBlock compact">
                <strong>Atributos mostrados</strong>
                <ul>
                  <li><b>Satélite:</b> plataforma que realizó la observación.</li>
                  <li><b>Instrumento:</b> sensor que generó la detección.</li>
                  <li><b>FRP:</b> potencia radiativa de la anomalía térmica.</li>
                  <li><b>Brillo:</b> temperatura de brillo registrada.</li>
                  <li><b>Scan / Track:</b> dimensiones espaciales asociadas a la detección.</li>
                </ul>
              </div>
            </section>
          ) : null}

          {showConafor ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">CONAFOR</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot conafor"/><div><strong>Incendio registrado</strong><span>Registro individual; el tamaño visual depende de la superficie registrada cuando existe.</span></div></div>
              </div>
            </section>
          ) : null}

          {showSmn ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">SMN-CONAGUA</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol station"/><div><strong>Estación meteorológica</strong><span>Estación individual del inventario, filtrable por territorio, cobertura temporal y situación operativa.</span></div></div>
              </div>
            </section>
          ) : null}

          {showInegi ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">INEGI</div>
              <p className="legendLead">En las capas temáticas el color diferencia los valores o categorías representados. El contraste se ajusta para conservar legibilidad sobre el mapa base.</p>

              {capasActivas.fisiografiaInegi ? (
                <>
                  <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line physiography"/><div><strong>Provincias fisiográficas</strong><span>Cada provincia visible conserva un color consistente.</span></div></div></div>
                  <CategoryLegend title="Provincias visibles" data={thematicLegend.fisiografia} />
                </>
              ) : null}

              {capasActivas.edafologiaInegi ? (
                <>
                  <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line soil"/><div><strong>Edafología</strong><span>El color diferencia el grupo principal de suelo.</span></div></div></div>
                  <CategoryLegend title="Grupos de suelo visibles" data={thematicLegend.edafologia} />
                </>
              ) : null}

              {capasActivas.usoSueloVegetacionInegi ? (
                <>
                  <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line landUse"/><div><strong>Uso de suelo y vegetación</strong><span>El color diferencia la categoría temática representada.</span></div></div></div>
                  <CategoryLegend title="Categorías visibles" data={thematicLegend.usoSueloVegetacion} />
                </>
              ) : null}

              {capasActivas.corrientesAguaInegi ? <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line water"/><div><strong>Corrientes de agua</strong><span>Azul para la red hidrográfica; el grosor aumenta con el orden de corriente cuando está disponible.</span></div></div></div> : null}
              {capasActivas.limitesEstatales ? <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line boundary"/><div><strong>Límite estatal</strong><span>El estilo se adapta al mapa base para mantener contraste.</span></div></div></div> : null}
              {capasActivas.limitesMunicipales ? <div className="mapLegendItems compactItems"><div className="mapLegendItem"><span className="mapLegendSymbol line boundaryMunicipal"/><div><strong>Límite municipal</strong><span>El estilo se adapta al mapa base para mantener contraste.</span></div></div></div> : null}
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
        </div>
      ) : null}
    </aside>
  );
}
