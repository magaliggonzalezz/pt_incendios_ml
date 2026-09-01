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

  useEffect(() => {
    const observer = new MutationObserver(() => {
      if (document.querySelector(".leaflet-popup")) setCollapsed(true);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  if (!hasSymbology) return null;

  const toggleLegend = () => {
    setCollapsed((value) => {
      const next = !value;
      if (!next) document.querySelector(".leaflet-popup-close-button")?.click();
      return next;
    });
  };

  return (
    <aside className={`mapLegend ${rightPanelOpen ? "rightPanelOpen" : ""} ${collapsed ? "isCollapsed" : ""}`} aria-label="Simbología del mapa">
      <div className="mapLegendHeader">
        <span>Simbología</span>
        <button type="button" className="mapLegendToggle" aria-label={collapsed ? "Mostrar simbología" : "Ocultar simbología"} aria-expanded={!collapsed} onClick={toggleLegend}>
          {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {!collapsed ? (
        <div className="mapLegendBody">
          {showFirms ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">FIRMS</div>
              <p className="legendLead">FIRMS representa <strong>anomalías térmicas detectadas por satélite</strong>; una detección no equivale por sí sola a un incendio confirmado.</p>
              <div className="legendSubTitle">Representación del punto</div>
              <ul className="legendDefinitionList">
                <li><strong>Color:</strong> categoría del atributo de confianza.</li>
                <li><strong>Tamaño:</strong> FRP; una mayor potencia radiativa produce un punto visualmente mayor.</li>
                <li><strong>Borde:</strong> claro para detección diurna y oscuro para nocturna.</li>
              </ul>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsLow"/><div><strong>Confianza baja</strong></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsNominal"/><div><strong>Confianza nominal</strong></div></div>
                <div className="mapLegendItem"><span className="mapLegendSymbol dot firmsHigh"/><div><strong>Confianza alta</strong></div></div>
              </div>
              <div className="legendNoteBlock">
                <strong>Producto utilizado: Archive</strong>
                <span>Se presentan únicamente observaciones del archivo histórico consolidado empleado por el proyecto; no se utilizan productos NRT ni RT.</span>
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
                  <li><b>Satélite</b> e <b>instrumento</b>: plataforma e instrumento que originaron la observación.</li>
                  <li><b>FRP</b>: potencia radiativa asociada a la anomalía térmica.</li>
                  <li><b>Brillo</b>: temperatura de brillo registrada por el producto.</li>
                  <li><b>Scan / Track</b>: dimensiones espaciales asociadas a la detección.</li>
                </ul>
              </div>
            </section>
          ) : null}

          {showConafor ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">CONAFOR</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol dot conafor"/><div><strong>Incendio registrado</strong><span>Registro oficial individual; el tamaño visual depende de la superficie registrada cuando existe.</span></div></div>
              </div>
            </section>
          ) : null}

          {showSmn ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">SMN-CONAGUA</div>
              <div className="mapLegendItems">
                <div className="mapLegendItem"><span className="mapLegendSymbol station"/><div><strong>Estación meteorológica</strong><span>Estación individual del inventario; puede filtrarse por territorio, cobertura temporal y situación operativa.</span></div></div>
              </div>
            </section>
          ) : null}

          {showInegi ? (
            <section className="mapLegendSection">
              <div className="mapLegendSectionTitle">INEGI</div>
              <div className="mapLegendItems">
                {capasActivas.fisiografiaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line physiography"/><div><strong>Provincias fisiográficas</strong><span>Regiones físicas del territorio definidas por rasgos del relieve y su origen.</span></div></div> : null}
                {capasActivas.edafologiaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line soil"/><div><strong>Edafología</strong><span>Unidades y grupos de suelo presentes en la cartografía fuente.</span></div></div> : null}
                {capasActivas.usoSueloVegetacionInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line landUse"/><div><strong>Uso de suelo y vegetación</strong><span>Cobertura y uso de suelo según la clasificación del producto.</span></div></div> : null}
                {capasActivas.corrientesAguaInegi ? <div className="mapLegendItem"><span className="mapLegendSymbol line water"/><div><strong>Corrientes de agua</strong><span>Elementos lineales de la red hidrográfica; cuando la fuente incluye nombre se presenta en el detalle.</span></div></div> : null}
                {capasActivas.limitesEstatales ? <div className="mapLegendItem"><span className="mapLegendSymbol line boundary"/><div><strong>Límite estatal</strong><span>El estilo se adapta al mapa base para mantener contraste.</span></div></div> : null}
                {capasActivas.limitesMunicipales ? <div className="mapLegendItem"><span className="mapLegendSymbol line boundaryMunicipal"/><div><strong>Límite municipal</strong><span>El estilo se adapta al mapa base para mantener contraste.</span></div></div> : null}
              </div>
              <p className="legendNote">La versión web actual conserva las features y sus atributos, pero no dispone en el repositorio de una definición de estilo oficial (QML/SLD/LYR) para reproducir exactamente la simbología cartográfica de origen. La paleta actual es de la aplicación y deberá sustituirse por la convención oficial cuando se incorpore esa definición.</p>
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
