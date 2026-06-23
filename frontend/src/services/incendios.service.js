/*import { apiFetch } from "./api";

export async function obtenerIncendios() {
  const response = await fetch("http://localhost:3000/api/incendios");
  if (!response.ok) {
    throw new Error("Error al obtener incendios");
  }
  return response.json();
}

export function obtenerIncendiosMapa(filtros = {}) {
  const query = new URLSearchParams(filtros).toString();
  return apiFetch(`/api/incendios/mapa?${query}`);
}*/

import { apiFetch } from "./api";

export function obtenerIncendiosMapa(filtros = {}) {
  const params = new URLSearchParams();

  Object.entries(filtros).forEach(([key, value]) => {
    if (value && value !== "" && typeof value !== "object") {
      params.append(key, value);
    }
  });

  const query = params.toString();

  return apiFetch(`/api/incendios/mapa${query ? `?${query}` : ""}`);
}