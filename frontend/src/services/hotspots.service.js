import { apiFetch } from "./api";

export function obtenerHotspots() {
  return apiFetch("/api/hotspots");
}

export function crearHotspot(data) {
  return apiFetch("/api/hotspots", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export function buscarHotspotsConFiltros(params) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/api/hotspots/filtros/busqueda?${query}`);
}

export function obtenerHotspotsParaMapa() {
  return apiFetch("/api/hotspots/visualizacion/mapa");
}