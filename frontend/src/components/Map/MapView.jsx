import React, { useState } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import MapControls from "./MapControls";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

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

export default function MapView() {
    const [baseLayerId, setBaseLayerId] = useState("esri");
    const activeLayer = BASE_LAYERS[baseLayerId];

    return (
        <div className="mapWrap">
            <MapContainer
                center={DEFAULT_VIEW.center}
                zoom={DEFAULT_VIEW.zoom}
                minZoom={3}
                className="leafletMap"
                zoomControl={false}
            >
                <TileLayer
                    url={activeLayer.url} 
                    attribution={activeLayer.attribution} 
                />
                <MapControls 
                    defaultView={DEFAULT_VIEW}
                    baseLayerId={baseLayerId}
                    onChangeLayer={setBaseLayerId}
                    layers={BASE_LAYERS}
                />
            </MapContainer>          
        </div>
    );
}