import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer,GeoJSON, useMap } from "react-leaflet";
import MapControls from "./MapControls";
import "leaflet/dist/leaflet.css";
import "./MapView.css";
import { obtenerIncendiosMapa } from "../../services/incendios.service";

const DEFAULT_VIEW = { center: [23.6345, -102.5528], zoom: 5 };

const BASE_LAYERS = {
    esri: {
        name: "Satelital",
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution: "Tiles &copy; Esri",
    },
    osm: {
        name: "OpenStreetMap",
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution: '&copy; OpenStreetMap contributors',
    },
    topo: {
        name: "Topográfico",
        url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attribution: '&copy; OpenTopoMap (CC-BY-SA)',
    },
};

export default function MapView({ filtros = {} }) {
    const [baseLayerId, setBaseLayerId] = useState("esri");
    const [incendiosGeojson, setIncendiosGeojson] = useState(null);
    const [loading, setLoading] = useState(false);
    const activeLayer = BASE_LAYERS[baseLayerId];

     async function buscarIncendios(filtros = {}) {
    try {
      setLoading(true);
      const data = await obtenerIncendiosMapa(filtros);
      setIncendiosGeojson(data);
    } catch (error) {
      console.error("Error al cargar incendios en mapa:", error);
    } finally {
      setLoading(false);
    }
    }

    useEffect(() => {
    buscarIncendios(filtros);
    }, [filtros]);

    function MapFlyTo({ vista }) {
    const map = useMap();

    useEffect(() => {
    if (vista?.center && vista?.zoom) {
      map.setView(vista.center, vista.zoom);
    }
     }, [vista, map]);

    return null;
    }



    return (
        <div className="mapWrap">
            <MapContainer
                center={DEFAULT_VIEW.center}
                zoom={DEFAULT_VIEW.zoom}
                minZoom={3}
                className="leafletMap"
                zoomControl={false}
            >
                 <MapFlyTo vista={filtros?.vista} />
                <TileLayer
                    url={activeLayer.url} 
                    attribution={activeLayer.attribution} 
                />

            {incendiosGeojson && (
            <GeoJSON
            key={JSON.stringify(incendiosGeojson).length}
            data={incendiosGeojson}
            onEachFeature={(feature, layer) => {
              const p = feature.properties;

              layer.bindPopup(`
                <strong>${p.estado || "Sin estado"}</strong><br/>
                Municipio: ${p.municipio || "No disponible"}<br/>
                Año: ${p.anio || "N/A"}<br/>
                Causa: ${p.causa || "No especificada"}<br/>
                Superficie: ${p.superficie || "N/A"}
              `);
            }}
            />
            )}
                <MapControls 
                    defaultView={DEFAULT_VIEW}
                    baseLayerId={baseLayerId}
                    onChangeLayer={setBaseLayerId}
                    layers={BASE_LAYERS}
                    onBuscarIncendios={buscarIncendios}
                    loading={loading}
                />
            </MapContainer>    

        </div>
    );
}