import { apiFetch } from "./api";

export async function obtenerIncendios() {
  const response = await fetch("http://localhost:3000/api/incendios");
  if (!response.ok) {
    throw new Error("Error al obtener incendios");
  }
  return response.json();
}

/*export function obtenerIncendioPorId(id) {
  return apiFetch(`/api/incendios/${id}`);
}

export function crearIncendio(data) {
  return apiFetch("/api/incendios", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export function buscarIncendiosConFiltros(params) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/api/incendios/filtros/busqueda?${query}`);
}

export function obtenerIncendiosParaMapa() {
  return apiFetch("/api/incendios/visualizacion/mapa");
}*/