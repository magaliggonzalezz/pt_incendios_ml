import { apiFetch } from "./api";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function obtenerResultadosEstadoDia(fecha) {
  return apiFetch(`/api/resultados/estado/dia?${buildQuery({ fecha })}`);
}

export function obtenerResultadosEstadoAnio(anio) {
  return apiFetch(`/api/resultados/estado/anio?${buildQuery({ anio })}`);
}

export function obtenerResultadosEstadoMes(anio, mes) {
  return apiFetch(`/api/resultados/estado/mes?${buildQuery({ anio, mes })}`);
}

export function obtenerResultadosMunicipioDia({ fecha, cvegeo }) {
  return apiFetch(
    `/api/resultados/municipio/dia?${buildQuery({ fecha, cvegeo })}`
  );
}

export function obtenerResultadosMunicipioAnio({ anio, cveEnt, cvegeo }) {
  return apiFetch(
    `/api/resultados/municipio/anio?${buildQuery({ anio, cve_ent: cveEnt, cvegeo })}`
  );
}

export function obtenerResultadosMunicipioMes({ anio, mes, cveEnt, cvegeo }) {
  return apiFetch(
    `/api/resultados/municipio/mes?${buildQuery({ anio, mes, cve_ent: cveEnt, cvegeo })}`
  );
}
