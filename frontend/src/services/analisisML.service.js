import { apiFetch } from "./api";

export function obtenerAnalisisML() {
  return apiFetch("/api/analisis-ml");
}

export function obtenerAnalisisMLPorId(id) {
  return apiFetch(`/api/analisis-ml/${id}`);
}

export function buscarAnalisisML(filtros = {}) {
  const query = new URLSearchParams(filtros).toString();

  return apiFetch(
    `/api/analisis-ml/filtros/busqueda?${query}`
  );
}